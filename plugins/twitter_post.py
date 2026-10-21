"""
Twitter/X post plugin using API v2 (OAuth 2.0 user context not included; uses
app-only? Posting requires user auth. This plugin expects a ready bearer/user
token configured).
"""
import json
import urllib.request

PLUGIN = {
    "name": "twitter_post",
    "description": "Post a tweet to X (Twitter) using a configured bearer/user token.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Tweet text"},
            "token": {"type": "STRING", "description": "Optional bearer/user token"},
        },
        "required": ["text"],
    },
}


def _cfg(key, parameters, namespace):
    v = (parameters.get(key) or "").strip()
    if v:
        return v
    try:
        from memory.config_manager import get_plugin_config
        return (get_plugin_config(namespace).get(key) or "").strip()
    except Exception:
        return ""


def run(parameters, player=None, session_memory=None) -> str:
    text = (parameters.get("text") or "").strip()
    if not text:
        return "No tweet text provided."
    token = _cfg("token", parameters, "twitter_post")
    if not token:
        return "Twitter token not configured (twitter_post.token)."
    try:
        data = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(
            "https://api.twitter.com/2/tweets",
            data=data,
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            out = json.loads(resp.read().decode())
        tid = out.get("data", {}).get("id")
        if player:
            try:
                player.write_log(f"JARVIS: Tweet posted ({tid}).")
            except Exception:
                pass
        return f"Tweet posted (id {tid})."
    except Exception as e:
        return f"Sir, twitter_post failed: {e}"
