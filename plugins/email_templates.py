"""JARVIS plugin - email templates."""
from __future__ import annotations

import json
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "email_templates",
    "description": "Manage email templates: create, list, render with variables.",
    "brief": "Email templates: create/list/render.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "create|list|render|delete"},
            "name": {"type": "STRING", "description": "Template name."},
            "subject": {"type": "STRING", "description": "Subject template (create)."},
            "body": {"type": "STRING", "description": "Body template (create). Use {var} placeholders."},
            "variables": {"type": "STRING", "description": "JSON variables (render)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_STORE = Path(__file__).resolve().parents[1] / "memory" / "email_templates.json"


def _load():
    try:
        if _STORE.exists():
            return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"templates": {}}


def _save(d):
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    d = _load()
    tpls = d.setdefault("templates", {})
    if action == "create":
        name = params.get("name", "")
        if not name:
            return outcome.failed("email_templates", "name required")
        tpls[name] = {"subject": params.get("subject", ""), "body": params.get("body", "")}
        _save(d)
        return outcome.done("email_templates", note=f"template '{name}' created")
    if action == "list":
        lines = [f"- {n}: {t.get('subject', '')}" for n, t in tpls.items()]
        return outcome.done("email_templates", note="\n".join(lines) or "no templates", count=len(tpls))
    if action == "render":
        name = params.get("name", "")
        if name not in tpls:
            return outcome.failed("email_templates", f"template not found: {name}")
        try:
            variables = json.loads(params.get("variables", "{}"))
        except Exception:
            variables = {}
        tpl = tpls[name]
        subject = tpl["subject"].format(**variables)
        body = tpl["body"].format(**variables)
        return outcome.done("email_templates", note=f"Subject: {subject}\n\n{body}", subject=subject, body=body)
    if action == "delete":
        name = params.get("name", "")
        if name in tpls:
            del tpls[name]
            _save(d)
            return outcome.done("email_templates", note=f"deleted '{name}'")
        return outcome.failed("email_templates", f"not found: {name}")
    return outcome.failed("email_templates", f"unknown action: {action}")
