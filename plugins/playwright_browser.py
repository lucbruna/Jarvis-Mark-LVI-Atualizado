"""JARVIS plugin - browser automation with Playwright.

Modern, reliable web automation: navigate, click, fill, extract, screenshot.
Use when browser_control (URL/shortcuts) is not enough and the task needs
real interaction with a page. Requires `pip install playwright` + `playwright
install chromium`. Falls back gracefully with an install hint.
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

from core import outcome

PLUGIN = {
    "name": "playwright_browser",
    "description": (
        "Automates a real browser with Playwright: navigate to a URL, click "
        "elements, fill forms, extract text/HTML, take screenshots, run JS. "
        "Use for 'log in to X and download Y', 'scrape this page fully', "
        "'fill this form'. Requires Playwright installed. More reliable than "
        "browser_control for complex page interaction."
    ),
    "brief": "Real browser automation (Playwright): navigate, click, fill, extract, screenshot.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "navigate|click|fill|extract|screenshot|eval|close"},
            "url": {"type": "STRING", "description": "URL for navigate."},
            "selector": {"type": "STRING", "description": "CSS selector for click/fill/extract."},
            "value": {"type": "STRING", "description": "Text to fill or JS to eval."},
            "headless": {"type": "BOOLEAN", "description": "Run headless (default true)."},
            "wait_ms": {"type": "INTEGER", "description": "Wait after action (default 1000)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_STATE = {"pw": None, "browser": None, "page": None, "lock": threading.Lock()}


def _ensure():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "Playwright not installed. Run: pip install playwright && playwright install chromium"
    with _STATE["lock"]:
        if _STATE["page"] is not None:
            return _STATE["page"], None
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            page = browser.new_page()
            _STATE.update({"pw": pw, "browser": browser, "page": page})
            return page, None
        except Exception as e:
            return None, f"Playwright failed to start: {e}"


def _close():
    with _STATE["lock"]:
        try:
            if _STATE["browser"]:
                _STATE["browser"].close()
            if _STATE["pw"]:
                _STATE["pw"].stop()
        except Exception:
            pass
        _STATE.update({"pw": None, "browser": None, "page": None})


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower().strip()
    if action == "close":
        _close()
        return outcome.done("playwright_browser", note="browser closed")

    page, err = _ensure()
    if err:
        return outcome.failed("playwright_browser", err)

    try:
        if action == "navigate":
            url = params.get("url", "")
            if not url:
                return outcome.failed("playwright_browser", "url required")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(int(params.get("wait_ms", 1000)))
            title = page.title()
            return outcome.done("playwright_browser", note=f"navigated: {title}", url=url)

        if action == "click":
            sel = params.get("selector", "")
            if not sel:
                return outcome.failed("playwright_browser", "selector required")
            page.click(sel, timeout=10000)
            page.wait_for_timeout(int(params.get("wait_ms", 500)))
            return outcome.done("playwright_browser", note=f"clicked {sel}")

        if action == "fill":
            sel = params.get("selector", "")
            val = params.get("value", "")
            if not sel:
                return outcome.failed("playwright_browser", "selector required")
            page.fill(sel, val, timeout=10000)
            return outcome.done("playwright_browser", note=f"filled {sel}")

        if action == "extract":
            sel = params.get("selector", "body")
            try:
                text = page.inner_text(sel, timeout=10000)
            except Exception:
                text = page.content()
            text = (text or "")[:8000]
            return outcome.done("playwright_browser", note=text[:400], text=text)

        if action == "screenshot":
            out = Path.home() / "Pictures" / f"pw_{int(time.time())}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out), full_page=bool(params.get("full_page", False)))
            return outcome.done("playwright_browser", note=f"screenshot saved: {out}", path=str(out))

        if action == "eval":
            js = params.get("value", "")
            if not js:
                return outcome.failed("playwright_browser", "value (JS) required")
            res = page.evaluate(js)
            return outcome.done("playwright_browser", note=str(res)[:400], result=res)

        return outcome.failed("playwright_browser", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("playwright_browser", str(e))
