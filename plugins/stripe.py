"""JARVIS plugin - Stripe integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "stripe",
    "description": "Stripe: list customers, create payment intent, list charges.",
    "brief": "Stripe: customers/charges/payment intents.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "customers|charges|create_payment_intent|balance"},
            "amount": {"type": "INTEGER", "description": "Amount in cents (create_payment_intent)."},
            "currency": {"type": "STRING", "description": "Currency (default usd)."},
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
        return outcome.failed("stripe", "Stripe secret key not configured")
    headers = {"Authorization": f"Bearer {key}"}
    try:
        if action == "customers":
            req = urllib.request.Request("https://api.stripe.com/v1/customers?limit=10", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            customers = data.get("data", [])
            lines = [f"- {c.get('email', '?')} ({c.get('id')})" for c in customers]
            return outcome.done("stripe", note="\n".join(lines) or "no customers", count=len(customers))
        if action == "charges":
            req = urllib.request.Request("https://api.stripe.com/v1/charges?limit=10", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            charges = data.get("data", [])
            lines = [f"- {c.get('amount')/100} {c.get('currency').upper()} ({c.get('status')})" for c in charges]
            return outcome.done("stripe", note="\n".join(lines) or "no charges", count=len(charges))
        if action == "balance":
            req = urllib.request.Request("https://api.stripe.com/v1/balance", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            avail = data.get("available", [{}])[0]
            msg = f"Available: {avail.get('amount', 0)/100} {avail.get('currency', '').upper()}"
            return outcome.done("stripe", note=msg)
        if action == "create_payment_intent":
            amount = int(params.get("amount", 1000))
            currency = params.get("currency", "usd")
            data = __import__("urllib.parse").urlencode({"amount": amount, "currency": currency}).encode()
            req = urllib.request.Request("https://api.stripe.com/v1/payment_intents", data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.loads(r.read())
            return outcome.done("stripe", note=f"payment intent: {res.get('id')} (client_secret: {res.get('client_secret')})")
        return outcome.failed("stripe", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("stripe", str(e))
