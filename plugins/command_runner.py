"""Command runner for JARVIS.

The escape hatch for everything the dedicated tools do not cover: git, pip,
ffmpeg, a project script, a system query, a CLI the user installed yesterday.

It is deliberately NOT a silent remote shell. Every command is parked behind
the HUD confirmation gate in core/confirm.py, which the model cannot forge: the
command executes only after a person presses CONFIRM. Destructive patterns are
refused unless the user explicitly enables them in this plugin's settings.

That combination is what makes "obey every command" compatible with an
assistant that is allowed to touch a real machine: the user keeps the final
keystroke.
"""
from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
from pathlib import Path

from core import confirm, outcome
from memory.config_manager import get_plugin_config

PLUGIN = {
    "name": "command_runner",
    "description": (
        "Runs a PowerShell or cmd command on this computer. Use it for any "
        "command no other tool covers: installed CLI tools, git, pip, ffmpeg, "
        "project scripts, system queries. The command is NOT run until the "
        "user presses CONFIRM on the screen, so never claim it has run before "
        "that. Do not use this for opening apps, files, volume, windows or "
        "power - those have dedicated tools."
    ),
    "brief": (
        "Runs a PowerShell/cmd command after an on-screen CONFIRM. Use for CLI "
        "tools and system queries, not for apps/files/power."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "command": {
                "type": "STRING",
                "description": (
                    "The exact command to run. PowerShell syntax when "
                    "shell='powershell', cmd syntax when shell='cmd'. Keep it "
                    "one command (use ';' inside PowerShell if needed)."
                ),
            },
            "shell": {
                "type": "STRING",
                "description": "powershell (default) or cmd.",
                "enum": ["powershell", "cmd"],
            },
            "timeout": {
                "type": "INTEGER",
                "description": "Seconds before the command is stopped, 1-300.",
            },
            "working_dir": {
                "type": "STRING",
                "description": "Optional folder to run the command in.",
            },
        },
        "required": ["command"],
    },
    "tier": "extra",
}


# Patterns that can destroy data or the boot configuration. They are refused
# even though there is a confirmation step, because a confirmation banner can
# be read too quickly. The user can opt in per-plugin if they genuinely need
# one of these.
_BLOCKED = [
    (re.compile(r"(?:^|[;&|]\s*)format(?:\.com)?\b", re.I), "disk formatting"),
    (re.compile(r"\bdiskpart\b", re.I), "disk partitioning"),
    (re.compile(r"\bbcdedit\b", re.I), "boot configuration"),
    (re.compile(r"\bwbadmin\b", re.I), "Windows backup"),
    (re.compile(r"\bvssadmin\b", re.I), "shadow copies"),
    (re.compile(r"\bcipher\s+/w\b", re.I), "disk wiping"),
    (re.compile(r"\breg(?:\.exe)?\s+delete\b", re.I), "registry deletion"),
    (re.compile(r"\bnet\s+user\b[^\n]*?/delete\b", re.I), "account deletion"),
    (re.compile(r"\bschtasks\b[^\n]*?/delete\b", re.I), "scheduled task deletion"),
    (re.compile(r"\btakeown\b", re.I), "ownership takeover"),
    (re.compile(r"\bicacls\b[^\n]*?/(?:grant|deny|reset)\b", re.I), "permission changes"),
    (re.compile(r"\b(?:shutdown|restart-computer|stop-computer)\b", re.I), "power state change"),
    (re.compile(r"\b(?:rd|rmdir)\s+/s\s+/q\s+[a-z]:\\?\s*(?:$|[;&|])", re.I), "drive-root deletion"),
    (re.compile(r"\bdel\s+/f\s+/s\s+/q\s+[a-z]:\\?\s*(?:$|[;&|])", re.I), "drive-root deletion"),
    (re.compile(r"\bremove-item\b[^\n]*?-recurse[^\n]*?\b[a-z]:\\?\s*(?:$|[;&|])", re.I), "drive-root deletion"),
    (re.compile(r"\brm\s+-rf\s+/\s*(?:$|[;&|])", re.I), "root deletion"),
    (re.compile(r"\bmkfs\b|\bdd\s+if=", re.I), "filesystem overwrite"),
    (re.compile(r"-encodedcommand\b|\s-enc\s", re.I), "encoded/obfuscated command"),
]


def _settings() -> dict:
    cfg = get_plugin_config("command_runner")

    def flag(key: str, default: bool) -> bool:
        value = cfg.get(key, default)
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)

    def integer(key: str, default: int, low: int, high: int) -> int:
        try:
            value = int(str(cfg.get(key, default)).strip())
        except Exception:
            value = default
        return max(low, min(high, value))

    return {
        "allow_shell": flag("allow_shell", True),
        "allow_destructive": flag("allow_destructive", False),
        "default_timeout": integer("default_timeout", 30, 1, 300),
        "max_output": integer("max_output", 4000, 200, 20000),
    }


def _creation_flags() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _oem_encoding() -> str:
    if os.name == "nt":
        try:
            import ctypes
            return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
        except Exception:
            return "cp850"
    return "utf-8"


def _powershell_argv(command: str) -> list[str]:
    # -EncodedCommand takes UTF-16LE base64, which preserves accents and quotes
    # that a console code page would mangle before PowerShell ever saw them.
    payload = base64.b64encode(str(command).encode("utf-16le")).decode("ascii")
    executable = (
        shutil.which("powershell.exe")
        or shutil.which("powershell")
        or shutil.which("pwsh.exe")
        or shutil.which("pwsh")
    )
    if not executable:
        raise FileNotFoundError("PowerShell was not found on PATH")
    return [
        executable,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", payload,
    ]


def _cmd_argv(command: str) -> list[str]:
    executable = (
        os.environ.get("COMSPEC")
        or shutil.which("cmd.exe")
        or "cmd.exe"
    )
    return [executable, "/d", "/s", "/c", str(command)]


def _blocked(command: str) -> str:
    for pattern, label in _BLOCKED:
        if pattern.search(command):
            return label
    return ""


def _clean_stderr(text: str) -> str:
    """Drop PowerShell's CLIXML progress envelope from redirected stderr.

    `powershell.exe -EncodedCommand` writes module-loading progress to stderr as
    a CLIXML document even when the command succeeds. It is noise to the user
    and to the model. Real command output belongs on stdout; the exit code is
    what decides success.
    """
    text = str(text or "")
    marker = "#< CLIXML"
    if marker in text:
        text = text.split(marker, 1)[0]
    return text.strip()


def _execute(
    command: str,
    shell: str,
    timeout: int,
    cwd: str | None,
    max_output: int,
    player,
) -> str:
    try:
        argv = _powershell_argv(command) if shell == "powershell" else _cmd_argv(command)
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding=_oem_encoding(),
            errors="replace",
            timeout=timeout,
            cwd=cwd,
            creationflags=_creation_flags(),
        )
        stdout = (proc.stdout or "").strip()
        stderr = _clean_stderr(proc.stderr)
        combined = stdout + (("\n" + stderr) if stderr else "")
        if len(combined) > max_output:
            combined = combined[:max_output] + "\n...[truncated]"

        if player and hasattr(player, "show_content"):
            try:
                player.show_content(
                    f"COMMAND ({shell})", combined or "(no output)"
                )
            except Exception:
                pass

        # The tool result reaches the model, but by the time a confirmed
        # command finishes the model may have finished its turn. request_say
        # is the only channel that can still speak the outcome.
        if player and hasattr(player, "request_say"):
            try:
                player.request_say(
                    f"Command finished with exit code {proc.returncode}. "
                    f"Output: {combined[:400] or '(no output)'}"
                )
            except Exception:
                pass

        if proc.returncode == 0:
            return outcome.done(
                "command_runner", shell=shell, exit_code=0,
                output=combined or "(no output)",
            )
        return outcome.failed(
            "command_runner",
            f"exit code {proc.returncode}",
            shell=shell, exit_code=proc.returncode,
            output=combined or "(no output)",
        )

    except subprocess.TimeoutExpired:
        return outcome.failed(
            "command_runner",
            f"timed out after {timeout} seconds",
            shell=shell,
        )
    except Exception as e:
        return outcome.failed(
            "command_runner", str(e), shell=shell
        )


def _test(values=None):
    """Settings-panel test button: checks that PowerShell can be launched."""
    try:
        proc = subprocess.run(
            _powershell_argv("Write-Output 'JARVIS command runner OK'"),
            capture_output=True,
            text=True,
            encoding=_oem_encoding(),
            errors="replace",
            timeout=10,
            creationflags=_creation_flags(),
        )
        text = (proc.stdout or proc.stderr or "").strip()
        if proc.returncode == 0:
            return True, f"OK: {text[:200]}"
        return False, f"exit {proc.returncode}: {text[:300]}"
    except Exception as e:
        return False, str(e)


PLUGIN_SETTINGS = {
    "namespace": "command_runner",
    "title": "COMMAND RUNNER",
    "fields": [
        {
            "key": "allow_shell",
            "label": "Allow command execution",
            "type": "toggle",
            "default": True,
        },
        {
            "key": "allow_destructive",
            "label": "Allow destructive commands (format, diskpart, registry, power)",
            "type": "toggle",
            "default": False,
        },
        {
            "key": "default_timeout",
            "label": "Default timeout (seconds)",
            "type": "text",
            "default": "30",
        },
        {
            "key": "max_output",
            "label": "Max output characters",
            "type": "text",
            "default": "4000",
        },
    ],
    "action": {
        "label": "TEST COMMAND RUNNER",
        "run": _test,
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    try:
        command = str(parameters.get("command") or "").strip()
        if not command:
            return outcome.failed(
                "command_runner", "command is required"
            )
        if len(command) > 8000:
            return outcome.failed(
                "command_runner",
                "command is too long (maximum 8000 characters)",
            )

        shell = str(parameters.get("shell") or "powershell").strip().lower()
        if shell not in ("powershell", "cmd"):
            shell = "powershell"

        cfg = _settings()
        if not cfg["allow_shell"]:
            return outcome.failed(
                "command_runner",
                "command execution is disabled in the Command Runner plugin settings",
            )

        reason = _blocked(command)
        if reason and not cfg["allow_destructive"]:
            return outcome.failed(
                "command_runner",
                f"refused: this looks like a destructive action ({reason}). "
                f"Enable 'Allow destructive commands' in the plugin settings "
                f"only if you really need it.",
                blocked=reason,
            )

        try:
            timeout = int(parameters.get("timeout") or cfg["default_timeout"])
        except Exception:
            timeout = cfg["default_timeout"]
        timeout = max(1, min(300, timeout))

        cwd = str(parameters.get("working_dir") or "").strip() or None
        if cwd:
            cwd = os.path.expanduser(cwd)
            if not Path(cwd).is_dir():
                return outcome.failed(
                    "command_runner",
                    f"working_dir is not a directory: {cwd}",
                )

        if confirm.pending_title():
            return outcome.ask(
                "command_runner",
                "Another confirmation is already on screen. Confirm or cancel "
                "it before starting a command.",
            )

        detail = f"{shell.upper()}: {command[:600]}"
        if len(command) > 600:
            detail += "\n...[truncated]"
        detail += f"\n\nTimeout: {timeout}s"
        if cwd:
            detail += f"\nWorking directory: {cwd}"

        return confirm.request(
            "command_runner",
            f"Run {shell} command?",
            detail,
            lambda: _execute(
                command, shell, timeout, cwd, cfg["max_output"], player
            ),
        )

    except Exception as e:
        return outcome.failed("command_runner", str(e))
