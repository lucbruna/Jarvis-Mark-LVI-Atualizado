"""
Install a program using a package manager (winget/choco/scoop).
"""
import subprocess

PLUGIN = {
    "name": "package_install",
    "description": (
        "Install a program via winget, Chocolatey or Scoop. Use for common "
        "software (git, vscode, python, node, 7zip, etc.)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "package": {"type": "STRING", "description": "Package id/name, e.g. 'Git.Git' or 'git'"},
            "manager": {"type": "STRING", "description": "auto, winget, choco or scoop (default auto)"},
            "silent": {"type": "BOOLEAN", "description": "Silent install (default true)"},
        },
        "required": ["package"],
    },
}


def _run(cmd, player):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
        out = (r.stdout or r.stderr or "").strip()[:3000]
        if player:
            try:
                player.write_log(f"JARVIS: {cmd}")
            except Exception:
                pass
        return out or f"exited {r.returncode}."
    except Exception as e:
        return f"Sir, package_install failed: {e}"


def run(parameters, player=None, session_memory=None) -> str:
    package = (parameters.get("package") or "").strip()
    if not package:
        return "No package provided."
    manager = (parameters.get("manager") or "auto").strip().lower()
    silent = parameters.get("silent", True)
    silent_flag = ""
    if silent:
        silent_flag = " --silent" if manager == "choco" else " --silent" if manager == "scoop" else " --silent"
    # winget uses --silent too
    if manager == "auto":
        # try winget first
        for mgr in ("winget", "choco", "scoop"):
            if mgr == "winget":
                cmd = f"winget install --id {package} -e --accept-source-agreements --accept-package-agreements"
                if silent:
                    cmd += " --silent"
            elif mgr == "choco":
                cmd = f"choco install {package} -y" + (" --silent" if silent else "")
            else:
                cmd = f"scoop install {package}"
            res = _run(cmd, player)
            # Heuristic: success if no "not found"/error? Return first non-error-ish
            low = res.lower()
            if "not found" not in low and "error" not in low and "is not recognized" not in low:
                return f"{mgr}: {res}"
        return "No package manager succeeded."
    if manager == "winget":
        cmd = f"winget install --id {package} -e --accept-source-agreements --accept-package-agreements"
        if silent:
            cmd += " --silent"
    elif manager == "choco":
        cmd = f"choco install {package} -y" + (" --silent" if silent else "")
    elif manager == "scoop":
        cmd = f"scoop install {package}"
    else:
        return f"Unknown manager: {manager}"
    return _run(cmd, player)
