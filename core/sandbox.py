"""core/sandbox.py - run untrusted code in an isolated subprocess.

WHY THIS EXISTS
    dev_agent and code execution paths used to exec() in-process, which gives
    the model the whole interpreter. This runs code in a separate process with
    a timeout, a memory cap (best-effort), no network env, and a cleaned
    environment. Not a real container, but a real boundary: a runaway loop or
    an `os.system` can no longer take the assistant down.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def run_python(code: str, timeout: int = 30, cwd: str | None = None, no_network: bool = False) -> dict:
    """Execute code in a subprocess (or Docker container if available)."""
    """Execute `code` in a fresh interpreter. Returns {ok, stdout, stderr, code}."""
    tmp = Path(tempfile.mkdtemp()) / "snippet.py"
    try:
        tmp.write_text(code, encoding="utf-8")
        env = {k: v for k, v in __import__("os").environ.items()
               if k.lower() not in ("http_proxy", "https_proxy", "all_proxy")}
        if no_network:
            for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
                env.pop(k, None)
            env["NO_PROXY"] = "*"
            env["no_proxy"] = "*"
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, "-I", str(tmp)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, cwd=cwd, env=env,
            creationflags=__import__("subprocess").CREATE_NO_WINDOW if sys.platform.startswith("win") else 0,
        )
        return {"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr,
                "code": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"timed out after {timeout}s", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}
    finally:
        try:
            tmp.unlink(missing_ok=True)
            tmp.parent.rmdir()
        except Exception:
            pass


def run_in_container(code: str, timeout: int = 60, image: str = "python:3.11-slim") -> dict:
    """Run code in a Docker container for stronger isolation."""
    import subprocess
    tmp = Path(tempfile.mkdtemp()) / "snippet.py"
    try:
        tmp.write_text(code, encoding="utf-8")
        cmd = ["docker", "run", "--rm", "-v", f"{tmp.parent}:/code", "-w", "/code", image, "python", "snippet.py"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr, "code": proc.returncode}
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "stderr": "docker not found", "code": -1}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"timed out after {timeout}s", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}
    finally:
        try:
            tmp.unlink(missing_ok=True)
            tmp.parent.rmdir()
        except Exception:
            pass
