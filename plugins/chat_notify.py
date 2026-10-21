"""JARVIS plugin - send messages to Slack/Discord."""
from __future__ import annotations

import json
import os
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "chat_notify",
    "description": "Send messages to Slack or Discord via webhooks. Actions: send.",
    "brief": "Slack/Discord: send messages via webhook.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "platform": {"type": "STRING", "description": "slack|discord"},
            "text": {"type": "STRING", "description": "Message text."},
            "webhook_url": {"type": "STRING", "description": "Webhook URL (optional, uses config)."},
        },
        "required": ["platform", "text"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    platform = (params.get("platform") or "").lower()
    text = params.get("text", "")
    webhook = params.get("webhook_url", "")
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        if platform == "slack":
            webhook = webhook or cfg.get("slack_webhook", "")
        elif platform == "discord":
            webhook = webhook or cfg.get("discord_webhook", "")
    except Exception:
        pass
    if not webhook:
        return outcome.failed("chat_notify", f"{platform} webhook not configured")
    try:
        import urllib.request
        data = {"text": text} if platform == "slack" else {"content": text}
        req = urllib.request.Request(webhook, data=__import__("json").dumps(data).encode(), headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=15)
        msg = f"Message sent to {platform}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("chat_notify", note=msg)
    except Exception as e:
        return outcome.failed("chat_notify", str(e))
