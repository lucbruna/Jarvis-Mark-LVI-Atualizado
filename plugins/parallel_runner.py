"""JARVIS plugin - run several independent tasks in parallel and deliver results.

Speed matters: when the user asks for multiple things ("check git status, run
tests, and lint"), doing them one after another wastes wall-clock time. This
plugin fans out a list of shell commands across a thread pool and returns all
results together. Each command still goes through the confirmation gate only
if run via command_runner; here commands are executed directly, so it is
intended for read-only / safe diagnostics. Destructive patterns are refused.
"""
from __future__ import annotations

import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from core import outcome

PLUGIN = {
    "name": "parallel_runner",
    "description": (
        "Runs a list of independent shell commands in parallel and returns all "
        "results together. Use for 'run these checks', 'do X, Y and Z', "
        "batch diagnostics. Commands are PowerShell by default. Refuses "
        "destructive patterns. For a single command or anything destructive, "
        "use command_runner instead (confirmation gate)."
    ),
    "brief": "Runs multiple shell commands in parallel for speed.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            # `items` is required by Gemini's declaration validation.
            "commands": {"type": "ARRAY", "items": {"type": "STRING"},
                         "description": "List of command strings to run."},
            "shell": {"type": "STRING", "description": "powershell (default) or cmd."},
            "timeout": {"type": "INTEGER", "description": "Per-command timeout seconds (default 60)."},
            "max_parallel": {"type": "INTEGER", "description": "Max concurrent (default 4)."},
        },
        "required": ["commands"],
    },
    "tier": "extra",
}

_BLOCKED = re.compile(r"\b(format|diskpart|bcdedit|shutdown|restart-computer|rm\s+-rf\s+/|mkfs|dd\s+if=)\b", re.I)


def _run_one(cmd, shell, timeout, cwd):
    if _BLOCKED.search(cmd):
        return {"cmd": cmd, "ok": False, "output": "refused: destructive pattern"}
    try:
        if shell == "powershell":
            import base64, shutil
            payload = base64.b64encode(str(cmd).encode("utf-16le")).decode("ascii")
            exe = shutil.which("powershell") or shutil.which("pwsh") or "powershell"
            argv = [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", payload]
        else:
            argv = ["cmd", "/d", "/s", "/c", str(cmd)]
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=timeout, cwd=cwd,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        marker = "#< CLIXML"
        if marker in err:
            err = err.split(marker, 1)[0].strip()
        combined = out + (("\n" + err) if err else "")
        return {"cmd": cmd, "ok": proc.returncode == 0, "code": proc.returncode,
                "output": combined[:4000] or "(no output)"}
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "ok": False, "output": f"timed out after {timeout}s"}
    except Exception as e:
        return {"cmd": cmd, "ok": False, "output": str(e)}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    cmds = params.get("commands") or []
    if isinstance(cmds, str):
        cmds = [cmds]
    cmds = [str(c).strip() for c in cmds if str(c).strip()]
    if not cmds:
        return outcome.failed("parallel_runner", "commands list is empty")
    shell = (params.get("shell") or "powershell").lower()
    timeout = max(1, min(300, int(params.get("timeout") or 60)))
    maxp = max(1, min(8, int(params.get("max_parallel") or 4)))
    cwd = params.get("working_dir")
    if cwd:
        cwd = str(Path(cwd).expanduser())
        if not Path(cwd).is_dir():
            return outcome.failed("parallel_runner", f"working_dir not a directory: {cwd}")

    t0 = time.monotonic()
    results = [None] * len(cmds)
    with ThreadPoolExecutor(max_workers=maxp) as ex:
        fut = {ex.submit(_run_one, c, shell, timeout, cwd): i for i, c in enumerate(cmds)}
        for f in as_completed(fut):
            results[fut[f]] = f.result()
    elapsed = time.monotonic() - t0

    lines = [f"Parallel run: {len(cmds)} commands in {elapsed:.2f}s"]
    for r in results:
        status = "OK" if r["ok"] else "FAIL"
        lines.append(f"\n[{status}] {r['cmd']}\n{r['output']}")
    msg = "\n".join(lines)
    if player:
        try:
            player.write_log(f"JARVIS: {msg[:600]}")
            if hasattr(player, "show_content"):
                player.show_content("PARALLEL RUN", msg[:8000])
        except Exception:
            pass
    ok = all(r["ok"] for r in results)
    return (outcome.done if ok else outcome.failed)("parallel_runner", note=f"{sum(r['ok'] for r in results)}/{len(cmds)} ok in {elapsed:.2f}s", output=msg[:4000])
