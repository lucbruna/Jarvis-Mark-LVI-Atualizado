"""JARVIS plugin - Stripe advanced (subscriptions, invoices, refunds)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "stripe_adv",
    "description": "Stripe advanced: subscriptions, invoices, refunds.",
    "brief": "Stripe advanced: subs/invoices/refunds.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "subscriptions|invoices|refund"},
            "charge_id": {"type": "STRING", "description": "Charge id (refund)."},
            "amount": {"type": "INTEGER", "description": "Refund amount in cents (refund)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _key():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("stripe_secret_key", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    key = _key()
    if not key:
        return outcome.failed("stripe_adv", "Stripe secret key not configured")
    headers = {"Authorization": f"Bearer {key}"}
    try:
        if action == "subscriptions":
            req = urllib.request.Request("https://api.stripe.com/v1/subscriptions?limit=10", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            subs = data.get("data", [])
            lines = [f"- {s.get('id')}: {s.get('status')} ({s.get('items', {}).get('data', [{}])[0].get('price', {}).get('unit_amount', 0)/100})" for s in subs]
            return outcome.done("stripe_adv", note="\n".join(lines) or "no subscriptions", count=len(subs))
        if action == "invoices":
            req = urllib.request.Request("https://api.stripe.com/v1/invoices?limit=10", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            invs = data.get("data", [])
            lines = [f"- {i.get('id')}: {i.get('amount_due', 0)/100} {i.get('currency', '').upper()} ({i.get('status')})" for i in invs]
            return outcome.done("stripe_adv", note="\n".join(lines) or "no invoices", count=len(invs))
        if action == "refund":
            cid = params.get("charge_id", "")
            amount = params.get("amount")
            data = __import__("urllib.parse").urlencode({"charge": cid, **({"amount": amount} if amount else {})}).encode()
            req = urllib.request.Request("https://api.stripe.com/v1/refunds", data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.loads(r.read())
            return outcome.done("stripe_adv", note=f"refund: {res.get('id')} ({res.get('status')})")
        return outcome.failed("stripe_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("stripe_adv", str(e))
