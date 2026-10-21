"""JARVIS plugin - Mailchimp integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "mailchimp",
    "description": "Mailchimp: list audiences, add subscriber, send campaign.",
    "brief": "Mailchimp: audiences/subscribers/campaigns.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "lists|add_subscriber|campaigns"},
            "list_id": {"type": "STRING", "description": "Audience/list id."},
            "email": {"type": "STRING", "description": "Subscriber email (add_subscriber)."},
            "fname": {"type": "STRING", "description": "First name (add_subscriber)."},
            "lname": {"type": "STRING", "description": "Last name (add_subscriber)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _cfg():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        key = cfg.get("mailchimp_api_key", "")
        # datacenter is after the dash in the key
        dc = key.split("-")[-1] if "-" in key else "us1"
        return key, dc
    except Exception:
        return "", "us1"


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    key, dc = _cfg()
    if not key:
        return outcome.failed("mailchimp", "Mailchimp API key not configured")
    base = f"https://{dc}.api.mailchimp.com/3.0"
    headers = {"Authorization": f"apikey {key}", "Content-Type": "application/json"}
    try:
        if action == "lists":
            req = urllib.request.Request(f"{base}/lists", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            lists = data.get("lists", [])
            lines = [f"- {l['name']} ({l['id']}) - {l['stats']['member_count']} members" for l in lists]
            return outcome.done("mailchimp", note="\n".join(lines) or "no lists", count=len(lists))
        if action == "add_subscriber":
            lid = params.get("list_id", "")
            body = {"email_address": params.get("email", ""), "status": "subscribed", "merge_fields": {"FNAME": params.get("fname", ""), "LNAME": params.get("lname", "")}}
            req = urllib.request.Request(f"{base}/lists/{lid}/members", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("mailchimp", note=f"subscriber added: {data.get('id')}")
        if action == "campaigns":
            req = urllib.request.Request(f"{base}/campaigns", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            camps = data.get("campaigns", [])
            lines = [f"- {c['settings']['subject_line']} ({c['status']})" for c in camps[:10]]
            return outcome.done("mailchimp", note="\n".join(lines) or "no campaigns", count=len(camps))
        return outcome.failed("mailchimp", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("mailchimp", str(e))
