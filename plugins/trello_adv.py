"""JARVIS plugin - Trello advanced (checklists, labels, due dates)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "trello_adv",
    "description": "Trello advanced: checklists, labels, due dates, comments.",
    "brief": "Trello advanced: checklists/labels/due/comments.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add_checklist|add_checkitem|add_label|set_due|add_comment|move_card"},
            "card_id": {"type": "STRING", "description": "Card id."},
            "name": {"type": "STRING", "description": "Checklist/item/label name."},
            "due": {"type": "STRING", "description": "Due date ISO (set_due)."},
            "comment": {"type": "STRING", "description": "Comment text (add_comment)."},
            "list_id": {"type": "STRING", "description": "Target list (move_card)."},
        },
        "required": ["action", "card_id"],
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
        return outcome.failed("trello_adv", "Trello not configured")
    auth = f"key={key}&token={token}"
    base = "https://api.trello.com/1"
    cid = params.get("card_id", "")
    try:
        if action == "add_checklist":
            import urllib.parse
            url = f"{base}/checklists?{auth}&idCard={cid}&name={urllib.parse.quote(params.get('name', 'Checklist'))}"
            with urllib.request.urlopen(url, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("trello_adv", note=f"checklist created: {data.get('id')}")
        if action == "add_checkitem":
            clid = params.get("checklist_id", "")
            import urllib.parse
            url = f"{base}/checklists/{clid}/checkItems?{auth}&name={urllib.parse.quote(params.get('name', 'item'))}"
            with urllib.request.urlopen(url, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("trello_adv", note=f"checkitem added: {data.get('id')}")
        if action == "set_due":
            body = {"due": params.get("due", "")}
            req = urllib.request.Request(f"{base}/cards/{cid}?{auth}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="PUT")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("trello_adv", note=f"due set: {data.get('due')}")
        if action == "add_comment":
            import urllib.parse
            url = f"{base}/cards/{cid}/actions/comments?{auth}&text={urllib.parse.quote(params.get('comment', ''))}"
            with urllib.request.urlopen(url, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("trello_adv", note="comment added")
        if action == "move_card":
            lid = params.get("list_id", "")
            body = {"idList": lid}
            req = urllib.request.Request(f"{base}/cards/{cid}?{auth}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="PUT")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("trello_adv", note=f"moved to {lid}")
        return outcome.failed("trello_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("trello_adv", str(e))
