"""
Slack notification plugin.

Sends a message to a Slack channel via an incoming webhook URL. Configure the
webhook once with save_plugin_config("slack_notify", {"webhook_url": "..."})
or pass webhook_url per call.
"""
import json
import urllib.request

PLUGIN = {
    "name": "slack_notify",
    "description": (
        "Send a message to a Slack channel through an incoming webhook. "
        "Use for notifications, alerts and short updates. Not for chat history."
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
            url = (get_plugin_config("slack_notify").get("webhook_url") or "").strip()
        except Exception:
            url = ""
    if not url:
        return ("Slack webhook not configured. Set it in plugin settings "
                "(slack_notify.webhook_url).")
    try:
        data = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                    headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.getcode()
        if player:
            try:
                player.write_log(f"JARVIS: Slack message sent ({code}).")
            except Exception:
                pass
        return f"Slack message sent ({code})."
    except Exception as e:
        return f"Sir, slack_notify failed: {e}"
