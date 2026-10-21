"""Docker control: status, start, pull, run, stop, remove, clone+compose."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "docker_control",
    "description": "Control Docker: check status, start Docker Desktop, pull/run/stop/remove containers, clone a repo and run compose.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "status|start|pull|run|stop|remove|clone"},
            "image": {"type": "STRING", "description": "Image name for pull/run"},
            "name": {"type": "STRING", "description": "Container name"},
            "ports": {"type": "STRING", "description": "Port mapping, e.g. 8080:80"},
            "env": {"type": "STRING", "description": "Env vars, comma-separated KEY=VAL"},
            "repo": {"type": "STRING", "description": "Git repo URL for clone"},
            "dest": {"type": "STRING", "description": "Destination directory for clone"},
            "compose_file": {"type": "STRING", "description": "Compose file (default docker-compose.yml)"},
        },
        "required": ["action"],
    },
}


def _run(cmd, cwd=None, timeout=300):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return proc.returncode, (out + ("\n" + err if err else ""))[:4000]
    except FileNotFoundError:
        return 1, "docker/git not found on PATH"
    except Exception as e:
        return 1, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    if action == "status":
        code, out = _run(["docker", "info"])
        return (outcome.done if code == 0 else outcome.failed)("docker_control", note="docker info", output=out)
    if action == "start":
        # Try opening Docker Desktop on Windows
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"])
            else:
                subprocess.Popen(["open", "-a", "Docker"])
        except Exception as e:
            return outcome.failed("docker_control", f"could not start Docker: {e}")
        return outcome.done("docker_control", note="docker desktop launched")
    if action == "pull":
        image = params.get("image")
        if not image:
            return outcome.failed("docker_control", "image required")
        code, out = _run(["docker", "pull", image], timeout=600)
        return (outcome.done if code == 0 else outcome.failed)("docker_control", note=f"pull {image}", output=out)
    if action == "run":
        image = params.get("image")
        if not image:
            return outcome.failed("docker_control", "image required")
        cmd = ["docker", "run", "-d"]
        if params.get("name"):
            cmd += ["--name", params["name"]]
        if params.get("ports"):
            cmd += ["-p", params["ports"]]
        if params.get("env"):
            for e in str(params["env"]).split(","):
                e = e.strip()
                if e:
                    cmd += ["-e", e]
        cmd.append(image)
        code, out = _run(cmd)
        return (outcome.done if code == 0 else outcome.failed)("docker_control", note=f"run {image}", output=out)
    if action == "stop":
        name = params.get("name") or params.get("image")
        if not name:
            return outcome.failed("docker_control", "name required")
        code, out = _run(["docker", "stop", name])
        return (outcome.done if code == 0 else outcome.failed)("docker_control", note=f"stop {name}", output=out)
    if action == "remove":
        name = params.get("name") or params.get("image")
        if not name:
            return outcome.failed("docker_control", "name required")
        code, out = _run(["docker", "rm", "-f", name])
        return (outcome.done if code == 0 else outcome.failed)("docker_control", note=f"rm {name}", output=out)
    if action == "clone":
        repo = params.get("repo")
        dest = params.get("dest") or "."
        if not repo:
            return outcome.failed("docker_control", "repo required")
        code, out = _run(["git", "clone", repo, dest], timeout=600)
        if code != 0:
            return outcome.failed("docker_control", "docker command failed", note="git clone failed", output=out)
        cf = params.get("compose_file") or "docker-compose.yml"
        compose_path = Path(dest) / cf
        if compose_path.exists():
            code2, out2 = _run(["docker", "compose", "-f", str(compose_path), "up", "-d"], cwd=dest, timeout=600)
            return (outcome.done if code2 == 0 else outcome.failed)("docker_control", note=f"cloned+compose {repo}", output=out + "\n" + out2)
        return outcome.done("docker_control", note=f"cloned {repo}", output=out)
    return outcome.failed("docker_control", f"unknown action: {action}")
PYEOF

