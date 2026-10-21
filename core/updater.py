"""core/updater.py - background update checker.

Polls GitHub releases periodically and notifies the UI when a newer version
is available. No-op when offline. Safe to run in a daemon thread.
"""
from __future__ import annotations

import json
import threading
import time
from urllib.request import urlopen

_REPO = "lucbruna/Jarvis-Mark-LVI-Atualizado"
_INTERVAL = 24 * 3600  # daily


def _latest_tag(repo: str = _REPO) -> str | None:
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        with urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data.get("tag_name")
    except Exception:
        return None


def _download_asset(url: str, dest: Path) -> bool:
    try:
        from urllib.request import urlretrieve
        urlretrieve(url, str(dest))
        return dest.exists() and dest.stat().st_size > 0
    except Exception:
        return False


def check_once(ui=None, current: str = "") -> str | None:
    tag = _latest_tag()
    if tag and tag != current:
        msg = f"SYS: New version available: {tag}"
        if ui:
            try:
                ui.write_log(msg)
            except Exception:
                pass
        return tag
    return None


def download_update(repo: str = _REPO, dest_dir: str | None = None) -> str:
    """Download the latest release asset (Windows exe) and return its path."""
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        with urlopen(url, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        assets = data.get("assets") or []
        exe_asset = next((a for a in assets if a.get("name", "").endswith(".exe")), None)
        if not exe_asset:
            return "no exe asset found in latest release"
        dest = Path(dest_dir or (Path.home() / "Downloads"))
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / exe_asset["name"]
        if _download_asset(exe_asset["browser_download_url"], out):
            return f"downloaded: {out}"
        return "download failed"
    except Exception as e:
        return f"update download failed: {e}"


def apply_update(exe_path: str) -> str:
    """Apply a downloaded update by replacing the current exe via a batch script."""
    try:
        import sys
        current = Path(sys.executable)
        new_exe = Path(exe_path)
        if not new_exe.exists():
            return "update file not found"
        bat = Path.home() / "AppData" / "Local" / "Temp" / "apply_update.bat"
        bat.write_text(f"""@echo off
timeout /t 2 /nobreak >nul
copy /y "{new_exe}" "{current}"
start "" "{current}"
del "%~f0"
""", encoding="utf-8")
        subprocess.run(["cmd", "/c", "start", "", str(bat)], check=False)
        return "update will be applied on next restart"
    except Exception as e:
        return f"apply failed: {e}"


def start_background(ui=None, current: str = "", interval: float = _INTERVAL) -> threading.Thread:
    def loop():
        while True:
            try:
                check_once(ui=ui, current=current)
            except Exception:
                pass
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True, name="updater")
    t.start()
    return t
