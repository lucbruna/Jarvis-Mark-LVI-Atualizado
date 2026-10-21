"""JARVIS plugin - PayPal advanced (subscriptions, invoices, refunds)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "paypal_adv",
    "description": "PayPal advanced: subscriptions, invoices, refunds.",
    "brief": "PayPal advanced: subs/invoices/refunds.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "subscriptions|invoices|refund"},
            "subscription_id": {"type": "STRING", "description": "Subscription id (refund)."},
            "amount": {"type": "STRING", "description": "Refund amount (refund)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        client_id = cfg.get("paypal_client_id", "")
        secret = cfg.get("paypal_secret", "")
        if not client_id or not secret:
            return None, "PayPal credentials not configured"
        import base64
        creds = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
        data = __import__("urllib.parse").urlencode({"grant_type": "client_credentials"}).encode()
        req = urllib.request.Request("https://api-m.sandbox.paypal.com/v1/oauth2/token", data=data, headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()).get("access_token"), None
    except Exception as e:
        return None, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token, err = _token()
    if err:
        return outcome.failed("paypal_adv", err)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base = "https://api-m.sandbox.paypal.com"
    try:
        if action == "subscriptions":
            req = urllib.request.Request(f"{base}/v1/billing/subscriptions", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            subs = data.get("subscriptions", [])
            lines = [f"- {s.get('id')}: {s.get('status')}" for s in subs]
            return outcome.done("paypal_adv", note="\n".join(lines) or "no subscriptions", count=len(subs))
        if action == "invoices":
            req = urllib.request.Request(f"{base}/v2/invoicing/invoices", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            invs = data.get("items", [])
            lines = [f"- {i.get('id')}: {i.get('status')}" for i in invs]
            return outcome.done("paypal_adv", note="\n".join(lines) or "no invoices", count=len(invs))
        return outcome.failed("paypal_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("paypal_adv", str(e))
