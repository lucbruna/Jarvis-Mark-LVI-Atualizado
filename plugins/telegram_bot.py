"""JARVIS plugin - Telegram bot integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "telegram_bot",
    "description": "Send messages via Telegram Bot API. Actions: send, send_photo.",
    "brief": "Telegram: send messages/photos.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "send (default) | send_photo"},
            "chat_id": {"type": "STRING", "description": "Chat ID (or use config)."},
            "text": {"type": "STRING", "description": "Message text."},
            "photo_path": {"type": "STRING", "description": "Photo path (send_photo)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("telegram_bot_token", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "send").lower()
    token = _token()
    if not token:
        return outcome.failed("telegram_bot", "Telegram bot token not configured")
    chat_id = params.get("chat_id", "")
    if not chat_id:
        try:
            cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
            chat_id = cfg.get("telegram_chat_id", "")
        except Exception:
            pass
    if not chat_id:
        return outcome.failed("telegram_bot", "chat_id required")
    try:
        if action == "send":
            data = {"chat_id": chat_id, "text": params.get("text", "")}
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=__import__("json").dumps(data).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.loads(r.read())
            msg = f"Telegram sent: {res.get('result', {}).get('message_id')}"
            if player:
                try: player.write_log(f"JARVIS: {msg}")
                except Exception: pass
            return outcome.done("telegram_bot", note=msg)
        if action == "send_photo":
            import urllib.request as u
            # Use multipart manually is complex; use simple approach with file
            path = params.get("photo_path", "")
            if not path:
                return outcome.failed("telegram_bot", "photo_path required")
            # Use requests if available
            try:
                import requests
                with open(path, "rb") as f:
                    r = requests.post(f"https://api.telegram.org/bot{token}/sendPhoto", data={"chat_id": chat_id}, files={"photo": f}, timeout=30)
                    r.raise_for_status()
                return outcome.done("telegram_bot", note="photo sent")
            except ImportError:
                return outcome.failed("telegram_bot", "requests not installed for photo upload")
    except Exception as e:
        return outcome.failed("telegram_bot", str(e))
    return outcome.failed("telegram_bot", f"unknown action: {action}")
