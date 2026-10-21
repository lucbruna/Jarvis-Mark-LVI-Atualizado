"""JARVIS plugin - API tester (Postman-like)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "api_tester",
    "description": "Test HTTP APIs: GET/POST/PUT/DELETE with headers and body.",
    "brief": "API tester (HTTP requests).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "method": {"type": "STRING", "description": "GET (default)|POST|PUT|DELETE|PATCH"},
            "url": {"type": "STRING", "description": "URL."},
            "headers": {"type": "STRING", "description": "JSON headers."},
            "body": {"type": "STRING", "description": "Request body (JSON or text)."},
        },
        "required": ["url"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    method = (params.get("method") or "GET").upper()
    url = params.get("url", "")
    try:
        headers = json.loads(params.get("headers", "{}"))
    except Exception:
        headers = {}
    body = params.get("body", "")
    try:
        data = body.encode() if body else None
        if data and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as r:
            status = r.status
            resp_headers = dict(r.headers)
            resp_body = r.read().decode("utf-8", "replace")[:4000]
        msg = f"HTTP {status}\n{resp_body}"
        if player:
            try: player.write_log(f"JARVIS: {msg[:300]}")
            except Exception: pass
        return outcome.done("api_tester", note=msg[:500], status=status, body=resp_body, headers=resp_headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:2000]
        return outcome.failed("api_tester", f"HTTP {e.code}: {body}")
    except Exception as e:
        return outcome.failed("api_tester", str(e))
