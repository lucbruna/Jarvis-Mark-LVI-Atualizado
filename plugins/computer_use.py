"""JARVIS plugin - visual computer use: see screen, click/type by description.

Uses screen capture + Gemini vision to locate an element and pyautogui to
act on it. This is a lightweight take on UI-TARS/OmniParser that reuses the
assistant's own vision. Requires pyautogui.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from core import gemini, outcome

PLUGIN = {
    "name": "computer_use",
    "description": (
        "Sees the screen, finds a UI element by description, and clicks/types "
        "on it. Use for 'click the Save button', 'type hello in the search box'. "
        "Requires pyautogui. Captures the screen, asks the vision model for "
        "coordinates, then acts."
    ),
    "brief": "Visual computer use: find an element on screen and click/type.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "click (default) | type | locate"},
            "target": {"type": "STRING", "description": "Description of the element, e.g. 'Save button'."},
            "text": {"type": "STRING", "description": "Text to type (action=type)."},
        },
        "required": ["target"],
    },
    "tier": "extra",
}


def _capture():
    try:
        from actions.screen_processor import _capture_screen
        return _capture_screen()
    except Exception:
        return None, None


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "click").lower()
    target = (params.get("target") or "").strip()
    if not target:
        return outcome.failed("computer_use", "target required")

    img_bytes, mime = _capture()
    if not img_bytes:
        return outcome.failed("computer_use", "screen capture unavailable")

    # Ask vision model for coordinates (normalized 0-1000).
    prompt = (
        f"Look at this screenshot. Find the UI element described as: '{target}'. "
        "Return ONLY JSON: {\"found\": true/false, \"x\": <0-1000>, \"y\": <0-1000>, "
        "\"label\": \"...\"}. Coordinates are relative to image (0,0 top-left)."
    )
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_bytes))
    except Exception:
        img = None
    contents = [prompt, img] if img is not None else [prompt, {"mime_type": mime, "data": img_bytes}]
    resp = gemini.call(contents, tier=gemini.FAST, timeout_ms=20000)
    if resp is None:
        return outcome.failed("computer_use", "vision model did not answer")
    import re
    text = getattr(resp, "text", None) or ""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return outcome.failed("computer_use", f"could not parse response: {text[:200]}")
    try:
        data = json.loads(m.group(0))
    except Exception:
        return outcome.failed("computer_use", f"bad JSON: {text[:200]}")
    if not data.get("found"):
        return outcome.failed("computer_use", f"element not found: {target}")
    x_norm = float(data.get("x", 0))
    y_norm = float(data.get("y", 0))

    # Need screen size to map normalized coords.
    try:
        import pyautogui
        sw, sh = pyautogui.size()
    except ImportError:
        return outcome.failed("computer_use", "pyautogui not installed")
    x = int(sw * x_norm / 1000.0)
    y = int(sh * y_norm / 1000.0)

    if action == "locate":
        return outcome.done("computer_use", note=f"found '{data.get('label', target)}' at ({x},{y})")

    if action == "type":
        text_to_type = params.get("text", "")
        pyautogui.click(x, y)
        time.sleep(0.3)
        pyautogui.write(text_to_type, interval=0.02)
        return outcome.done("computer_use", note=f"typed '{text_to_type}' at ({x},{y})")

    # click
    pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.click()
    return outcome.done("computer_use", note=f"clicked '{data.get('label', target)}' at ({x},{y})")
