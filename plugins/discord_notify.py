"""
Discord notification plugin via webhook.
"""
import json
import urllib.request

PLUGIN = {
    "name": "discord_notify",
    "description": (
        "Send a message to a Discord channel through a webhook URL. "
        "Use for notifications and alerts."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Message text to send"},
            "webhook_url": {"type": "STRING", "description": "Optional override webhook URL"},
        },
        "required": ["text"],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    text = (parameters.get("text") or "").strip()
    if not text:
        return "No message text provided."
    url = (parameters.get("webhook_url") or "").strip()
    if not url:
        try:
            from memory.config_manager import get_plugin_config
            url = (get_plugin_config("discord_notify").get("webhook_url") or "").strip()
        except Exception:
            url = ""
    if not url:
        return ("Discord webhook not configured. Set it in plugin settings "
                "(discord_notify.webhook_url).")
    try:
        data = json.dumps({"content": text}).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                    headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.getcode()
        if player:
            try:
                player.write_log(f"JARVIS: Discord message sent ({code}).")
            except Exception:
                pass
        return f"Discord message sent ({code})."
    except Exception as e:
        return f"Sir, discord_notify failed: {e}"
