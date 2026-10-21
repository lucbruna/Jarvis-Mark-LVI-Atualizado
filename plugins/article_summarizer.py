"""JARVIS plugin - summarize web articles."""
from __future__ import annotations

import urllib.request
from pathlib import Path

from core import gemini, outcome


PLUGIN = {
    "name": "article_summarizer",
    "description": "Fetch a web article and summarize it. Provide URL.",
    "brief": "Summarize web articles.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "Article URL."},
            "length": {"type": "STRING", "description": "short|medium|long (default medium)."},
        },
        "required": ["url"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    url = params.get("url", "")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", "replace")
        # Strip tags
        import re
        text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = " ".join(text.split())[:15000]
    except Exception as e:
        return outcome.failed("article_summarizer", f"fetch failed: {e}")
    length = params.get("length", "medium")
    prompt = f"Summarize this article ({length}):\n\n{text}"
    try:
        resp = gemini.call(prompt, tier=gemini.SMART, timeout_ms=45000)
        summary = getattr(resp, "text", "No response") if resp else "No response"
    except Exception as e:
        summary = f"Failed: {e}"
    if player:
        try: player.write_log(f"JARVIS: {summary[:300]}")
        except Exception: pass
    return outcome.done("article_summarizer", note=summary[:500], summary=summary)
