"""JARVIS plugin - Trello integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "trello",
    "description": "Trello: list boards, lists, cards; create cards.",
    "brief": "Trello: boards/lists/cards.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "boards|lists|cards|create_card"},
            "board_id": {"type": "STRING", "description": "Board id."},
            "list_id": {"type": "STRING", "description": "List id."},
            "name": {"type": "STRING", "description": "Card name (create_card)."},
            "desc": {"type": "STRING", "description": "Card description (create_card)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _cfg():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("trello_api_key", ""), cfg.get("trello_token", "")
    except Exception:
        return "", ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    key, token = _cfg()
    if not key or not token:
        return outcome.failed("trello", "Trello API key/token not configured")
    base = "https://api.trello.com/1"
    auth = f"key={key}&token={token}"
    try:
        if action == "boards":
            with urllib.request.urlopen(f"{base}/members/me/boards?{auth}", timeout=15) as r:
                data = json.loads(r.read())
            lines = [f"- {b['name']} ({b['id']})" for b in data]
            return outcome.done("trello", note="\n".join(lines) or "no boards", count=len(data))
        if action == "lists":
            bid = params.get("board_id", "")
            with urllib.request.urlopen(f"{base}/boards/{bid}/lists?{auth}", timeout=15) as r:
                data = json.loads(r.read())
            lines = [f"- {l['name']} ({l['id']})" for l in data]
            return outcome.done("trello", note="\n".join(lines) or "no lists", count=len(data))
        if action == "cards":
            lid = params.get("list_id", "")
            with urllib.request.urlopen(f"{base}/lists/{lid}/cards?{auth}", timeout=15) as r:
                data = json.loads(r.read())
            lines = [f"- {c['name']}" for c in data]
            return outcome.done("trello", note="\n".join(lines) or "no cards", count=len(data))
        if action == "create_card":
            lid = params.get("list_id", "")
            name = params.get("name", "")
            desc = params.get("desc", "")
            url = f"{base}/cards?{auth}&idList={lid}&name={__import__('urllib.parse').parse.quote(name)}&desc={__import__('urllib.parse').parse.quote(desc)}"
            with urllib.request.urlopen(url, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("trello", note=f"card created: {data.get('id')}")
        return outcome.failed("trello", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("trello", str(e))
