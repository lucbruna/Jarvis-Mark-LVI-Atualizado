"""JARVIS plugin - create a file and deliver it ready to use.

The gap between "created" and "delivered" is where assistants lose people:
a file written into a folder nobody opens is not a deliverable. This plugin
writes the content, then opens the containing folder and selects the file
(Windows/macOS) or prints its path, so the result is immediately in the
user's hands. It also records an undo entry for the creation.

Supported content types: plain text, markdown, json, csv, html, py, and
binary-ish base64 via 'encoding=base64'. For spreadsheets/images use the
dedicated builders (bi_excel_builder, media_creator).
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from core import outcome, undo

PLUGIN = {
    "name": "file_deliver",
    "description": (
        "Creates a file with the given content and delivers it ready to use: "
        "writes it, then opens the containing folder and reveals the file. "
        "Use whenever the user asks to 'create', 'make', 'write', 'generate' "
        "and 'deliver/send/give me the file'. Supports txt, md, json, csv, "
        "html, py and base64 binary. Returns the absolute path. "
        "Do NOT use file_controller for deliverable creation when the user "
        "expects to receive the file - use this so the folder opens."
    ),
    "brief": "Creates a file and opens its folder so the user receives it immediately.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "File name including extension, e.g. report.md"},
            "content": {"type": "STRING", "description": "Full file content (or base64 if encoding=base64)."},
            "folder": {"type": "STRING", "description": "Target folder: desktop (default), documents, downloads, home, or an absolute path."},
            "encoding": {"type": "STRING", "description": "text (default) or base64."},
            "open": {"type": "BOOLEAN", "description": "Open/reveal the file after writing (default true)."},
        },
        "required": ["name", "content"],
    },
    "tier": "core",
}


def _resolve_folder(folder: str) -> Path:
    f = (folder or "desktop").strip().lower()
    home = Path.home()
    mapping = {
        "desktop": home / "Desktop",
        "documents": home / "Documents",
        "downloads": home / "Downloads",
        "home": home,
        "pictures": home / "Pictures",
    }
    if f in mapping:
        p = mapping[f]
    else:
        p = Path(folder).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _reveal(path: Path) -> None:
    system = sys.platform
    try:
        if system.startswith("win"):
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        elif system == "darwin":
            subprocess.run(["open", "-R", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path.parent)], check=False)
    except Exception:
        pass


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    name = (params.get("name") or "").strip()
    content = params.get("content") or ""
    folder = params.get("folder") or "desktop"
    encoding = (params.get("encoding") or "text").strip().lower()
    do_open = params.get("open", True)
    if do_open is None:
        do_open = True

    if not name:
        return outcome.failed("file_deliver", "a file name is required")
    if "/" in name or "\\" in name:
        name = Path(name).name

    target_dir = _resolve_folder(folder)
    target = target_dir / name

    try:
        if encoding == "base64":
            data = base64.b64decode(content.encode("ascii"), validate=False)
            target.write_bytes(data)
        else:
            target.write_text(str(content), encoding="utf-8")
    except Exception as e:
        return outcome.failed("file_deliver", f"write failed: {e}")

    # undo: delete the created file
    def _undo():
        try:
            if target.exists():
                target.unlink()
            return f"Removed {target.name}."
        except Exception as e:
            return f"Undo failed: {e}"
    try:
        undo.push_undo(f"created {target.name}", _undo)
    except Exception:
        pass

    size = target.stat().st_size
    if do_open:
        threading.Thread(target=_reveal, args=(target,), daemon=True).start()

    msg = f"Delivered: {target} ({size} bytes)"
    if player:
        try:
            player.write_log(f"JARVIS: {msg}")
            if hasattr(player, "show_content"):
                player.show_content("DELIVERED FILE", str(target))
        except Exception:
            pass
    return outcome.done("file_deliver", path=str(target), bytes=size, opened=bool(do_open))
