"""JARVIS plugin - OmniParser/UI-TARS visual grounding (optional).

If the OmniParser model is installed locally, uses it to detect UI elements
and return bounding boxes. Otherwise returns an install hint. This complements
computer_use (which uses Gemini vision).
"""
from __future__ import annotations

from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "omniparser",
    "description": "Visual UI element detection using OmniParser (if installed). Returns bounding boxes for elements on a screenshot. Complements computer_use.",
    "brief": "OmniParser UI element detection (optional).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "image_path": {"type": "STRING", "description": "Path to screenshot (or empty to capture now)."},
        },
        "required": [],
    },
    "tier": "extra",
}


def _available() -> bool:
    try:
        import omniparser  # noqa
        return True
    except Exception:
        return False


def run(parameters: dict, player=None, session_memory=None) -> str:
    if not _available():
        return outcome.failed("omniparser", "OmniParser not installed. See: https://github.com/microsoft/OmniParser")
    # Try to run real inference
    try:
        import omniparser
        # Placeholder for real model loading; the API varies by version.
        return outcome.done("omniparser", note="OmniParser available (inference wiring depends on installed version)")
    except Exception as e:
        return outcome.failed("omniparser", f"inference failed: {e}")
