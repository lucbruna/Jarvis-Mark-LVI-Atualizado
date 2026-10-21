"""JARVIS plugin - smart home via Home Assistant REST API."""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

from core import outcome


PLUGIN = {
    "name": "smart_home",
    "description": "Control smart home devices via Home Assistant. Actions: turn_on, turn_off, toggle, list, state.",
    "brief": "Smart home (Home Assistant): on/off/toggle/state.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "turn_on|turn_off|toggle|list|state"},
            "entity_id": {"type": "STRING", "description": "Entity id (e.g. light.living_room)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _cfg():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("home_assistant_url", os.environ.get("HA_URL", "")), cfg.get("home_assistant_token", os.environ.get("HA_TOKEN", ""))
    except Exception:
        return os.environ.get("HA_URL", ""), os.environ.get("HA_TOKEN", "")


def _req(method, path, data=None):
    url, token = _cfg()
    if not url or not token:
        return None, "Home Assistant not configured (set home_assistant_url/token in config)"
    req = Request(f"{url.rstrip('/')}/api/{path.lstrip('/')}", method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    body = json.dumps(data).encode() if data else None
    try:
        with urlopen(req, data=body, timeout=10) as r:
            return json.loads(r.read().decode()), None
    except Exception as e:
        return None, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    eid = params.get("entity_id", "")
    if action == "list":
        data, err = _req("GET", "states")
        if err:
            return outcome.failed("smart_home", err)
        lines = [f"- {d['entity_id']}: {d['state']}" for d in data[:40]]
        return outcome.done("smart_home", note="\n".join(lines), count=len(data))
    if action == "state":
        data, err = _req("GET", f"states/{eid}")
        if err:
            return outcome.failed("smart_home", err)
        return outcome.done("smart_home", note=f"{eid}: {data.get('state')}", state=data.get("state"))
    svc = "turn_on" if action == "turn_on" else "turn_off" if action == "turn_off" else "toggle" if action == "toggle" else None
    if not svc:
        return outcome.failed("smart_home", f"unknown action: {action}")
    if not eid:
        return outcome.failed("smart_home", "entity_id required")
    data, err = _req("POST", f"services/homeassistant/{svc}", {"entity_id": eid})
    if err:
        return outcome.failed("smart_home", err)
    msg = f"{svc} {eid}"
    if player:
        try: player.write_log(f"JARVIS: {msg}")
        except Exception: pass
    return outcome.done("smart_home", note=msg)
