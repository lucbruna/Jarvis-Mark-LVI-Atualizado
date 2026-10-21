"""JARVIS plugin - stock/crypto price tracker."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "stock_crypto",
    "description": "Fetch stock or crypto prices. Supports Yahoo Finance (stocks) and CoinGecko (crypto).",
    "brief": "Stock/crypto prices (Yahoo/CoinGecko).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "symbol": {"type": "STRING", "description": "Ticker (AAPL) or crypto id (bitcoin)."},
            "type": {"type": "STRING", "description": "stock (default) or crypto."},
            "currency": {"type": "STRING", "description": "vs currency for crypto (default usd)."},
        },
        "required": ["symbol"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    symbol = params.get("symbol", "").upper()
    typ = (params.get("type") or "stock").lower()
    try:
        if typ == "crypto":
            cid = params.get("symbol", "").lower()
            vs = params.get("currency", "usd")
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies={vs}"
            with urllib.request.urlopen(url, timeout=15) as r:
                data = json.loads(r.read())
            price = data.get(cid, {}).get(vs, "?")
            msg = f"{cid}: {price} {vs.upper()}"
            return outcome.done("stock_crypto", note=msg, price=price)
        # stock via Yahoo
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice", "?")
        currency = meta.get("currency", "USD")
        msg = f"{symbol}: {price} {currency}"
        return outcome.done("stock_crypto", note=msg, price=price)
    except Exception as e:
        return outcome.failed("stock_crypto", str(e))
