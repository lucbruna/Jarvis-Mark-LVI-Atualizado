"""JARVIS plugin - WhatsApp automation via pywhatkit."""
from __future__ import annotations

from core import outcome


PLUGIN = {
    "name": "whatsapp_auto",
    "description": "Send WhatsApp messages (instant or scheduled) via pywhatkit. Requires WhatsApp Web login.",
    "brief": "WhatsApp: send messages.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "send (default) | send_image"},
            "phone": {"type": "STRING", "description": "Phone number with country code (e.g. +90...)."},
            "message": {"type": "STRING", "description": "Message text."},
            "image_path": {"type": "STRING", "description": "Image path (send_image)."},
            "wait_time": {"type": "INTEGER", "description": "Seconds to wait before sending (default 15)."},
        },
        "required": ["action", "phone"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "send").lower()
    phone = params.get("phone", "")
    try:
        import pywhatkit
    except ImportError:
        return outcome.failed("whatsapp_auto", "pywhatkit not installed. Run: pip install pywhatkit")
    try:
        if action == "send":
            msg = params.get("message", "")
            wait = int(params.get("wait_time", 15))
            pywhatkit.sendwhatmsg_instantly(phone, msg, wait_time=wait, tab_close=True)
            return outcome.done("whatsapp_auto", note=f"message sent to {phone}")
        if action == "send_image":
            img = params.get("image_path", "")
            caption = params.get("message", "")
            pywhatkit.sendwhats_image(phone, img, caption, wait_time=int(params.get("wait_time", 15)))
            return outcome.done("whatsapp_auto", note=f"image sent to {phone}")
        return outcome.failed("whatsapp_auto", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("whatsapp_auto", str(e))
