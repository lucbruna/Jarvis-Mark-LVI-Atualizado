"""JARVIS plugin - Mailchimp advanced (templates, automations, reports)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "mailchimp_adv",
    "description": "Mailchimp advanced: templates, automations, reports.",
    "brief": "Mailchimp advanced: templates/automations/reports.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "templates|automations|reports"},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _cfg():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        key = cfg.get("mailchimp_api_key", "")
        dc = key.split("-")[-1] if "-" in key else "us1"
        return key, dc
    except Exception:
        return "", "us1"


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    key, dc = _cfg()
    if not key:
        return outcome.failed("mailchimp_adv", "Mailchimp API key not configured")
    base = f"https://{dc}.api.mailchimp.com/3.0"
    headers = {"Authorization": f"apikey {key}"}
    try:
        if action == "templates":
            req = urllib.request.Request(f"{base}/templates", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            templates = data.get("templates", [])
            lines = [f"- {t['name']} ({t['id']})" for t in templates[:20]]
            return outcome.done("mailchimp_adv", note="\n".join(lines) or "no templates", count=len(templates))
        if action == "automations":
            req = urllib.request.Request(f"{base}/automations", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            autos = data.get("automations", [])
            lines = [f"- {a['settings']['title']} ({a['status']})" for a in autos[:20]]
            return outcome.done("mailchimp_adv", note="\n".join(lines) or "no automations", count=len(autos))
        if action == "reports":
            req = urllib.request.Request(f"{base}/reports", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            reps = data.get("reports", [])
            lines = [f"- {r['campaign_title']}: {r['opens']['open_rate']} opens" for r in reps[:10]]
            return outcome.done("mailchimp_adv", note="\n".join(lines) or "no reports", count=len(reps))
        return outcome.failed("mailchimp_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("mailchimp_adv", str(e))
