"""JARVIS plugin - PayPal integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "paypal",
    "description": "PayPal: create orders, capture payments, list transactions.",
    "brief": "PayPal: orders/payments.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "create_order|capture|list_transactions"},
            "amount": {"type": "STRING", "description": "Amount (create_order)."},
            "currency": {"type": "STRING", "description": "Currency (default USD)."},
            "order_id": {"type": "STRING", "description": "Order id (capture)."},
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
        return outcome.failed("paypal", err)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base = "https://api-m.sandbox.paypal.com"
    try:
        if action == "create_order":
            amount = params.get("amount", "10.00")
            currency = params.get("currency", "USD")
            body = {"intent": "CAPTURE", "purchase_units": [{"amount": {"currency_code": currency, "value": amount}}]}
            req = urllib.request.Request(f"{base}/v2/checkout/orders", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("paypal", note=f"order created: {data.get('id')}", order_id=data.get("id"))
        if action == "capture":
            oid = params.get("order_id", "")
            req = urllib.request.Request(f"{base}/v2/checkout/orders/{oid}/capture", data=b"{}", headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("paypal", note=f"captured: {data.get('status')}")
        return outcome.failed("paypal", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("paypal", str(e))
