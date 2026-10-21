"""JARVIS plugin - personal finance tracker."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "finances",
    "description": "Track income/expenses and budget. Actions: add, summary, list, delete.",
    "brief": "Personal finance: add/summary/list expenses.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add|summary|list|delete"},
            "amount": {"type": "NUMBER", "description": "Amount (add)."},
            "category": {"type": "STRING", "description": "Category (add)."},
            "description": {"type": "STRING", "description": "Description (add)."},
            "type": {"type": "STRING", "description": "income|expense (add)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_STORE = Path(__file__).resolve().parents[1] / "memory" / "finances.json"


def _load():
    try:
        if _STORE.exists():
            return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"entries": []}


def _save(d):
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    d = _load()
    if action == "add":
        entry = {"amount": float(params.get("amount", 0)), "category": params.get("category", "general"),
                 "description": params.get("description", ""), "type": params.get("type", "expense"),
                 "date": time.strftime("%Y-%m-%d")}
        d["entries"].append(entry)
        _save(d)
        return outcome.done("finances", note=f"added {entry['type']} {entry['amount']} ({entry['category']})")
    if action == "list":
        lines = [f"- {e['date']}: {e['type']} {e['amount']} {e['category']} {e['description']}" for e in d["entries"][-20:]]
        return outcome.done("finances", note="\n".join(lines) or "no entries", count=len(d["entries"]))
    if action == "summary":
        income = sum(e["amount"] for e in d["entries"] if e.get("type") == "income")
        expense = sum(e["amount"] for e in d["entries"] if e.get("type") == "expense")
        by_cat = {}
        for e in d["entries"]:
            if e.get("type") == "expense":
                by_cat[e.get("category", "general")] = by_cat.get(e.get("category", "general"), 0) + e["amount"]
        msg = f"Income: {income}\nExpense: {expense}\nBalance: {income - expense}\nBy category: {by_cat}"
        return outcome.done("finances", note=msg)
    if action == "delete":
        # delete last
        if d["entries"]:
            removed = d["entries"].pop()
            _save(d)
            return outcome.done("finances", note=f"removed {removed}")
        return outcome.failed("finances", "no entries to delete")
    return outcome.failed("finances", f"unknown action: {action}")
