"""JARVIS plugin - Monday advanced (updates, files, webhooks)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "monday_adv",
    "description": "Monday advanced: updates, files, webhooks.",
    "brief": "Monday advanced: updates/files/webhooks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add_update|add_file|list_updates"},
            "item_id": {"type": "STRING", "description": "Item id."},
            "text": {"type": "STRING", "description": "Update text (add_update)."},
            "file_path": {"type": "STRING", "description": "File path (add_file)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("monday_token", "")
    except Exception:
        return ""


def _graphql(query, variables=None):
    token = _token()
    if not token:
        return None, "Monday token not configured"
    req = urllib.request.Request("https://api.monday.com/v2", data=json.dumps({"query": query, "variables": variables or {}}).encode(), headers={"Authorization": token, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()), None
    except Exception as e:
        return None, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    try:
        if action == "add_update":
            iid = params.get("item_id", "")
            text = params.get("text", "")
            data, err = _graphql("mutation ($itemId: ID!, $body: String!) { create_update (item_id: $itemId, body: $body) { id } }", {"itemId": iid, "body": text})
            if err:
                return outcome.failed("monday_adv", err)
            return outcome.done("monday_adv", note=f"update created: {data['data']['create_update']['id']}")
        if action == "list_updates":
            iid = params.get("item_id", "")
            data, err = _graphql("query ($itemId: ID!) { items (ids: [$itemId]) { updates { id body created_at } } }", {"itemId": iid})
            if err:
                return outcome.failed("monday_adv", err)
            updates = data["data"]["items"][0]["updates"]
            lines = [f"- {u['created_at']}: {u['body'][:100]}" for u in updates]
            return outcome.done("monday_adv", note="\n".join(lines) or "no updates", count=len(updates))
        return outcome.failed("monday_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("monday_adv", str(e))
