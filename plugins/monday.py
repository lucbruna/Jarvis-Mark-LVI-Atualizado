"""JARVIS plugin - Monday.com integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "monday",
    "description": "Monday.com: create items, update, list boards.",
    "brief": "Monday.com: boards/items.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "boards|items|create_item|update_item"},
            "board_id": {"type": "STRING", "description": "Board id."},
            "item_name": {"type": "STRING", "description": "Item name (create)."},
            "group_id": {"type": "STRING", "description": "Group id (create)."},
            "column_values": {"type": "STRING", "description": "JSON column values (create/update)."},
            "item_id": {"type": "STRING", "description": "Item id (update)."},
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
        if action == "boards":
            data, err = _graphql("query { boards { id name } }")
            if err:
                return outcome.failed("monday", err)
            boards = data["data"]["boards"]
            lines = [f"- {b['name']} ({b['id']})" for b in boards]
            return outcome.done("monday", note="\n".join(lines) or "no boards", count=len(boards))
        if action == "items":
            bid = params.get("board_id", "")
            data, err = _graphql("query ($boardId: ID!) { boards(ids: [$boardId]) { items_page { items { id name } } } }", {"boardId": bid})
            if err:
                return outcome.failed("monday", err)
            items = data["data"]["boards"][0]["items_page"]["items"]
            lines = [f"- {i['name']} ({i['id']})" for i in items]
            return outcome.done("monday", note="\n".join(lines) or "no items", count=len(items))
        if action == "create_item":
            bid = params.get("board_id", "")
            name = params.get("item_name", "")
            gid = params.get("group_id", "")
            data, err = _graphql("mutation ($boardId: ID!, $groupId: String!, $itemName: String!) { create_item (board_id: $boardId, group_id: $groupId, item_name: $itemName) { id } }", {"boardId": bid, "groupId": gid, "itemName": name})
            if err:
                return outcome.failed("monday", err)
            return outcome.done("monday", note=f"created item: {data['data']['create_item']['id']}")
        return outcome.failed("monday", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("monday", str(e))
