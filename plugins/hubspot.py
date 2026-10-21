"""JARVIS plugin - HubSpot integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "hubspot",
    "description": "HubSpot: list/create contacts, deals, companies.",
    "brief": "HubSpot: contacts/deals/companies.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list_contacts|create_contact|list_deals|create_deal"},
            "email": {"type": "STRING", "description": "Contact email (create_contact)."},
            "firstname": {"type": "STRING", "description": "First name (create_contact)."},
            "lastname": {"type": "STRING", "description": "Last name (create_contact)."},
            "dealname": {"type": "STRING", "description": "Deal name (create_deal)."},
            "amount": {"type": "NUMBER", "description": "Deal amount (create_deal)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("hubspot_token", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token = _token()
    if not token:
        return outcome.failed("hubspot", "HubSpot token not configured")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        if action == "list_contacts":
            req = urllib.request.Request("https://api.hubapi.com/crm/v3/objects/contacts?limit=20", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            contacts = data.get("results", [])
            lines = [f"- {c.get('properties', {}).get('email', '?')}" for c in contacts]
            return outcome.done("hubspot", note="\n".join(lines) or "no contacts", count=len(contacts))
        if action == "create_contact":
            body = {"properties": {"email": params.get("email", ""), "firstname": params.get("firstname", ""), "lastname": params.get("lastname", "")}}
            req = urllib.request.Request("https://api.hubapi.com/crm/v3/objects/contacts", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("hubspot", note=f"contact created: {data.get('id')}")
        if action == "list_deals":
            req = urllib.request.Request("https://api.hubapi.com/crm/v3/objects/deals?limit=20", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            deals = data.get("results", [])
            lines = [f"- {d.get('properties', {}).get('dealname', '?')}: {d.get('properties', {}).get('amount', '?')}" for d in deals]
            return outcome.done("hubspot", note="\n".join(lines) or "no deals", count=len(deals))
        if action == "create_deal":
            body = {"properties": {"dealname": params.get("dealname", ""), "amount": params.get("amount", "")}}
            req = urllib.request.Request("https://api.hubapi.com/crm/v3/objects/deals", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("hubspot", note=f"deal created: {data.get('id')}")
        return outcome.failed("hubspot", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("hubspot", str(e))
