"""JARVIS plugin - generate reports from data (HTML/Markdown)."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "report_generator",
    "description": "Generate reports (HTML or Markdown) from data. Combines data into a formatted document.",
    "brief": "Generate reports (HTML/Markdown).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "Report title."},
            "content": {"type": "STRING", "description": "Report body (Markdown supported)."},
            "format": {"type": "STRING", "description": "md (default) or html."},
            "output": {"type": "STRING", "description": "Output folder (default documents)."},
        },
        "required": ["title", "content"],
    },
    "tier": "extra",
}


def _reveal(path):
    import subprocess, sys
    try:
        if sys.platform.startswith("win"):
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path.parent)], check=False)
    except Exception:
        pass


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    title = params.get("title", "Report")
    content = params.get("content", "")
    fmt = (params.get("format") or "md").lower()
    out_dir = Path(params.get("output") or str(Path.home() / "Documents")).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    if fmt == "html":
        html = f"<html><head><title>{title}</title></head><body><h1>{title}</h1>\n{content.replace(chr(10), '<br>')}\n</body></html>"
        out = out_dir / f"{title.replace(' ', '_')}_{stamp}.html"
        out.write_text(html, encoding="utf-8")
    else:
        md = f"# {title}\n\n{content}"
        out = out_dir / f"{title.replace(' ', '_')}_{stamp}.md"
        out.write_text(md, encoding="utf-8")
    threading.Thread(target=_reveal, args=(out,), daemon=True).start()
    msg = f"Report saved: {out}"
    if player:
        try: player.write_log(f"JARVIS: {msg}")
        except Exception: pass
    return outcome.done("report_generator", note=msg, path=str(out))
