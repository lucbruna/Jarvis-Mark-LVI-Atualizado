"""JARVIS plugin - social media posting (Twitter/X, LinkedIn)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "social_media",
    "description": "Post to social media (Twitter/X, LinkedIn). Requires API credentials.",
    "brief": "Social media: post to Twitter/X and LinkedIn.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "platform": {"type": "STRING", "description": "twitter|linkedin"},
            "text": {"type": "STRING", "description": "Post text."},
            "action": {"type": "STRING", "description": "post (default)"},
        },
        "required": ["platform", "text"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    platform = (params.get("platform") or "").lower()
    text = params.get("text", "")
    if platform == "twitter":
        try:
            import tweepy
            cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
            client = tweepy.Client(
                consumer_key=cfg.get("twitter_api_key"), consumer_secret=cfg.get("twitter_api_secret"),
                access_token=cfg.get("twitter_access_token"), access_token_secret=cfg.get("twitter_access_secret"),
            )
            resp = client.create_tweet(text=text)
            msg = f"Tweet posted: {resp.data['id']}"
            if player:
                try: player.write_log(f"JARVIS: {msg}")
                except Exception: pass
            return outcome.done("social_media", note=msg)
        except ImportError:
            return outcome.failed("social_media", "tweepy not installed. Run: pip install tweepy")
        except Exception as e:
            return outcome.failed("social_media", str(e))
    if platform == "linkedin":
        # LinkedIn posting requires OAuth; return guidance
        return outcome.failed("social_media", "LinkedIn posting requires OAuth setup. Use the LinkedIn API with a registered app.")
    return outcome.failed("social_media", f"unknown platform: {platform}")
