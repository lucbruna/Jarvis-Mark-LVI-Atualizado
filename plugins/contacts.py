"""JARVIS plugin - contact management (local CRM)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "contacts",
    "description": "Manage contacts: add, search, list, update, delete. Stored locally.",
    "brief": "Contact management (local CRM).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add|search|list|update|delete"},
            "name": {"type": "STRING", "description": "Contact name."},
            "email": {"type": "STRING", "description": "Email."},
            "phone": {"type": "STRING", "description": "Phone."},
            "company": {"type": "STRING", "description": "Company."},
            "notes": {"type": "STRING", "description": "Notes."},
            "query": {"type": "STRING", "description": "Search query."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_STORE = Path(__file__).resolve().parents[1] / "memory" / "contacts.json"


def _load():
    try:
        if _STORE.exists():
            return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"contacts": []}


def _save(d):
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    d = _load()
    contacts = d.setdefault("contacts", [])
    if action == "add":
        entry = {"name": params.get("name", ""), "email": params.get("email", ""), "phone": params.get("phone", ""),
                 "company": params.get("company", ""), "notes": params.get("notes", ""), "created": time.time()}
        contacts.append(entry)
        _save(d)
        return outcome.done("contacts", note=f"added contact: {entry['name']}")
    if action == "search":
        q = (params.get("query") or "").lower()
        matches = [c for c in contacts if q in c.get("name", "").lower() or q in c.get("email", "").lower() or q in c.get("company", "").lower()]
        lines = [f"- {c['name']} ({c.get('email', '')}) {c.get('company', '')}" for c in matches]
        return outcome.done("contacts", note="\n".join(lines) or "no matches", count=len(matches))
    if action == "list":
        lines = [f"- {c['name']} ({c.get('email', '')}) {c.get('company', '')}" for c in contacts]
        return outcome.done("contacts", note="\n".join(lines) or "no contacts", count=len(contacts))
    if action == "update":
        name = params.get("name", "")
        for c in contacts:
            if c.get("name", "").lower() == name.lower():
                for k in ("email", "phone", "company", "notes"):
                    if params.get(k):
                        c[k] = params[k]
                _save(d)
                return outcome.done("contacts", note=f"updated: {name}")
        return outcome.failed("contacts", f"contact not found: {name}")
    if action == "delete":
        name = params.get("name", "")
        d["contacts"] = [c for c in contacts if c.get("name", "").lower() != name.lower()]
        _save(d)
        return outcome.done("contacts", note=f"deleted: {name}")
    return outcome.failed("contacts", f"unknown action: {action}")
