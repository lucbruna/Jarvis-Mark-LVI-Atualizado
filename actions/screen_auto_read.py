"""JARVIS action - read the screen on its own, without being asked.

The user should never have to say "read my screen" for the assistant to know
what is on it. This action captures the display, describes what is there
(text, layout, errors, running apps) and returns a compact summary that the
model can use to act immediately. It never asks a follow-up question: it
reports facts and a suggested next step, so a turn can continue without the
user repeating themselves.

It is deliberately fast: capture is a few milliseconds, compression is
already in screen_processor, and the description uses the fast tier so the
answer arrives while the user is still looking at the screen.
"""
from __future__ import annotations

import io
import hashlib
import time
from pathlib import Path

from core import gemini, outcome, cache
from core.lazyimport import installed

_PIL = installed("PIL")
try:
    import PIL.Image
except Exception:
    PIL = None

# Reuse the project's own capture + compression so resolution/quality stay
# consistent with the rest of the app (no second code path to drift).
try:
    from actions.screen_processor import _capture_screen
except Exception:
    _capture_screen = None

TOOL_TIER = "fast"


def _describe(img_bytes: bytes, mime: str, instruction: str = "") -> str:
    try:
        img = PIL.Image.open(io.BytesIO(img_bytes)) if _PIL and PIL is not None else None
    except Exception:
        img = None

    prompt = (
        "You are looking at a screenshot of the user's computer. "
        "Report, concisely and in the user's language's style: "
        "(1) what application/window is in the foreground and what it shows, "
        "(2) any visible error, warning, dialog or notification, "
        "(3) the key text/content that matters for acting on it, "
        "(4) one concrete suggested next step if there is an obvious one. "
        "No preamble, no 'I can see'. Facts only."
    )
    if instruction:
        prompt += f"\nExtra focus: {instruction}"

    contents = [prompt]
    if img is not None:
        contents.append(img)
    else:
        contents.append({"mime_type": mime, "data": img_bytes})

    try:
        resp = gemini.call(contents, tier=gemini.FAST, timeout_ms=20000)
        if resp is None:
            return "Screen captured but the description model did not answer."
        text = getattr(resp, "text", None)
        if text is None and hasattr(resp, "candidates"):
            try:
                text = resp.candidates[0].content.parts[0].text
            except Exception:
                text = None
        return (text or "").strip() or "Screen captured; nothing notable to report."
    except Exception as e:
        return f"Screen read failed: {e}"


def screen_auto_read(parameters=None, response=None, player=None,
                    session_memory=None) -> str:
    params = parameters or {}
    instruction = (params.get("focus") or params.get("instruction") or "").strip()
    save = bool(params.get("save", False))

    if _capture_screen is None:
        return outcome.failed("screen_auto_read", "screen capture is not available (mss not installed)")

    try:
        t0 = time.monotonic()
        img_bytes, mime = _capture_screen()
        took = time.monotonic() - t0
    except Exception as e:
        return outcome.failed("screen_auto_read", f"capture failed: {e}")

    # Cache by image hash: an unchanged screen returns instantly.
    img_hash = hashlib.sha256(img_bytes).hexdigest()
    cache_key = {"hash": img_hash, "focus": instruction}
    cached_summary = cache.get("screen", cache_key)
    if cached_summary is not None and not save:
        if player:
            try:
                player.write_log(f"JARVIS: [screen] cache hit ({took:.2f}s capture skipped)")
            except Exception:
                pass
        return outcome.done("screen_auto_read", note=cached_summary[:300],
                            cached=True, elapsed="0.00s")

    if player:
        try:
            player.write_log(f"JARVIS: [screen] captured {len(img_bytes)} bytes in {took:.2f}s")
        except Exception:
            pass

    if save:
        try:
            out_dir = Path.home() / "Pictures" / "JarvisScreenshots"
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / f"screen_{int(time.time())}.jpg"
            out.write_bytes(img_bytes)
        except Exception:
            out = None
    else:
        out = None

    summary = _describe(img_bytes, mime, instruction)

    try:
        cache.set("screen", cache_key, summary, ttl=60.0)
    except Exception:
        pass

    result = f"Screen read ({took:.2f}s): {summary}"
    if out is not None:
        result += f"\nScreenshot saved: {out}"

    if player:
        try:
            player.write_log(f"JARVIS: {result[:400]}")
        except Exception:
            pass

    return outcome.done("screen_auto_read", note=summary[:300], saved=str(out) if out else None,
                        elapsed=f"{took:.2f}s")


TOOL = {
    "name": "screen_auto_read",
    "description": (
        "Captures the user's screen and describes what is on it WITHOUT asking "
        "the user anything. Use this proactively whenever the user refers to "
        "'this', 'here', 'the screen', 'what I'm looking at', an error they "
        "mention, or a task that depends on current on-screen state. Also use "
        "it before acting on a UI when you are not sure what is displayed. "
        "Returns a concise factual summary plus an optional suggested next step. "
        "Never ask the user to read or describe the screen; call this instead."
    ),
    "brief": "Captures and describes the current screen so you can act without asking.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "focus": {
                "type": "STRING",
                "description": "Optional focus, e.g. 'error dialog', 'form fields', 'browser tab'.",
            },
            "save": {
                "type": "BOOLEAN",
                "description": "Save the screenshot to ~/Pictures/JarvisScreenshots (default false).",
            },
        },
        "required": [],
    },
    "handler": screen_auto_read,
    "tier": "core",
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
}
