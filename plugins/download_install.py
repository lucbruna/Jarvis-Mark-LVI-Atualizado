"""
Download and install a program from the internet.

Safety:
- In normal mode, a confirmation banner is shown and nothing runs until the
  user presses CONFIRM.
- In unrestricted mode (config: unrestricted_mode=true), it runs immediately.
"""
import hashlib
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

PLUGIN = {
    "name": "download_install",
    "description": (
        "Download an installer from a URL and run it. Use only when the user "
        "explicitly asks to install a program. Supports .exe/.msi and other "
        "executables. Optional sha256 verification."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "Direct download URL of the installer"},
            "filename": {"type": "STRING", "description": "Optional local filename"},
            "args": {"type": "STRING", "description": "Installer arguments, e.g. '/S' or '/quiet'"},
            "sha256": {"type": "STRING", "description": "Optional SHA-256 hex digest to verify"},
        },
        "required": ["url"],
    },
}


def _unlocked():
    try:
        from memory.config_manager import get_unrestricted_mode
        return bool(get_unrestricted_mode())
    except Exception:
        return False


def _do_install(url, filename, args, sha256, player):
    try:
        if player:
            try:
                player.write_log(f"JARVIS: Downloading {url}")
            except Exception:
                pass
        tmp = Path(tempfile.gettempdir()) / (filename or Path(url).name or "installer.bin")
        urllib.request.urlretrieve(url, tmp)
        if sha256:
            h = hashlib.sha256()
            with open(tmp, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            if h.hexdigest().lower() != sha256.lower():
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass
                return "SHA-256 mismatch; installer deleted."
        if player:
            try:
                player.write_log(f"JARVIS: Running installer {tmp}")
            except Exception:
                pass
        cmd = [str(tmp)] + (args.split() if args else [])
        subprocess.Popen(cmd)
        return f"Installer launched: {tmp.name}."
    except Exception as e:
        return f"Sir, download_install failed: {e}"


def run(parameters, player=None, session_memory=None) -> str:
    url = (parameters.get("url") or "").strip()
    filename = (parameters.get("filename") or "").strip()
    github_repo = (parameters.get("github_repo") or "").strip()  # owner/repo
    asset_pattern = (parameters.get("asset_pattern") or "").strip()
    if not url and github_repo:
        try:
            import json, urllib.request
            api = f"https://api.github.com/repos/{github_repo}/releases/latest"
            req = urllib.request.Request(api, headers={"User-Agent": "MarkLVI/1.0", "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                rel = json.loads(resp.read().decode())
            assets = rel.get("assets", [])
            if asset_pattern:
                import fnmatch
                assets = [a for a in assets if fnmatch.fnmatch(a.get("name", ""), asset_pattern)]
            if not assets:
                return "No matching release asset found."
            url = assets[0].get("browser_download_url", "")
            if not filename:
                filename = assets[0].get("name", "")
        except Exception as e:
            return f"Sir, download_install failed resolving GitHub release: {e}"
    if not url:
        return "No url provided."
    filename = (parameters.get("filename") or filename or "").strip()
    args = (parameters.get("args") or "").strip()
    sha256 = (parameters.get("sha256") or "").strip()

    # Unrestricted mode: run immediately.
    if _unlocked():
        return _do_install(url, filename, args, sha256, player)

    # Otherwise gate behind human confirmation.
    try:
        from core import confirm
        title = f"Download & install from {url}"
        detail = f"URL: {url}\nArgs: {args or '(none)'}"
        return confirm.request(
            key="download_install",
            title=title,
            detail=detail,
            run=lambda: _do_install(url, filename, args, sha256, player),
        )
    except Exception as e:
        return f"Sir, download_install failed: {e}"
