"""JARVIS plugin - personalized daily news digest."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "news_digest",
    "description": "Build a personalized news digest from configured topics. Uses web_search. Summarizes top headlines.",
    "brief": "Personalized daily news digest.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            # `items` is required by Gemini's declaration validation.
            "topics": {"type": "ARRAY", "items": {"type": "STRING"},
                       "description": "List of topics (e.g. ['AI', 'sports'])."},
            "count": {"type": "INTEGER", "description": "Headlines per topic (default 5)."},
        },
        "required": [],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    topics = params.get("topics") or ["technology", "world"]
    count = int(params.get("count", 5))
    try:
        from actions.web_search import _news, _search
    except Exception:
        return outcome.failed("news_digest", "web_search not available")
    sections = []
    for t in topics:
        try:
            res = _news(t) if False else _search(t)
        except Exception:
            res = ""
        sections.append(f"## {t}\n{res[:800]}")
    msg = "\n\n".join(sections)
    # Save to file
    out = Path.home() / "Documents" / f"news_digest_{int(time.time())}.txt"
    out.write_text(msg, encoding="utf-8")
    if player:
        try: player.write_log(f"JARVIS: News digest saved: {out}")
        except Exception: pass
    return outcome.done("news_digest", note=f"Digest saved: {out}", path=str(out))
