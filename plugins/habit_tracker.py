"""JARVIS plugin - habit tracker with streaks."""
from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "habit_tracker",
    "description": "Track daily habits with streaks. Actions: add, check, list, stats.",
    "brief": "Habit tracker with streaks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add|check|list|stats"},
            "habit": {"type": "STRING", "description": "Habit name."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_STORE = Path(__file__).resolve().parents[1] / "memory" / "habits.json"


def _load():
    try:
        if _STORE.exists():
            return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"habits": {}}


def _save(d):
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def _streak(dates):
    if not dates:
        return 0
    s = set(dates)
    today = date.today()
    streak = 0
    cur = today
    while cur.isoformat() in s:
        streak += 1
        cur -= timedelta(days=1)
    return streak


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    d = _load()
    habits = d.setdefault("habits", {})
    if action == "add":
        name = params.get("habit", "")
        if not name:
            return outcome.failed("habit_tracker", "habit name required")
        habits.setdefault(name, {"checks": []})
        _save(d)
        return outcome.done("habit_tracker", note=f"added habit: {name}")
    if action == "check":
        name = params.get("habit", "")
        if name not in habits:
            return outcome.failed("habit_tracker", f"habit not found: {name}")
        today = date.today().isoformat()
        if today not in habits[name]["checks"]:
            habits[name]["checks"].append(today)
        _save(d)
        return outcome.done("habit_tracker", note=f"checked {name} (streak {_streak(habits[name]['checks'])})")
    if action == "list":
        lines = [f"- {h}: streak {_streak(info.get('checks', []))}" for h, info in habits.items()]
        return outcome.done("habit_tracker", note="\n".join(lines) or "no habits", count=len(habits))
    if action == "stats":
        lines = [f"- {h}: {_streak(info.get('checks', []))} day streak, {len(info.get('checks', []))} total" for h, info in habits.items()]
        return outcome.done("habit_tracker", note="\n".join(lines) or "no habits")
    return outcome.failed("habit_tracker", f"unknown action: {action}")
