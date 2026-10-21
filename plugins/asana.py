"""JARVIS plugin - Asana integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "asana",
    "description": "Asana: list tasks, create tasks, complete tasks.",
    "brief": "Asana: tasks CRUD.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list|create|complete"},
            "project_id": {"type": "STRING", "description": "Project id (list/create)."},
            "name": {"type": "STRING", "description": "Task name (create)."},
            "notes": {"type": "STRING", "description": "Task notes (create)."},
            "task_id": {"type": "STRING", "description": "Task id (complete)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("asana_token", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token = _token()
    if not token:
        return outcome.failed("asana", "Asana token not configured")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        if action == "list":
            pid = params.get("project_id", "")
            url = f"https://app.asana.com/api/1.0/tasks?project={pid}&limit=20"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            tasks = data.get("data", [])
            lines = [f"- {t['gid']}: {t['name']}" for t in tasks]
            return outcome.done("asana", note="\n".join(lines) or "no tasks", count=len(tasks))
        if action == "create":
            body = {"data": {"name": params.get("name", ""), "notes": params.get("notes", ""), "projects": [params.get("project_id", "")]}}
            req = urllib.request.Request("https://app.asana.com/api/1.0/tasks", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("asana", note=f"created task: {data['data']['gid']}")
        if action == "complete":
            tid = params.get("task_id", "")
            body = {"data": {"completed": True}}
            req = urllib.request.Request(f"https://app.asana.com/api/1.0/tasks/{tid}", data=json.dumps(body).encode(), headers=headers, method="PUT")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("asana", note=f"completed: {tid}")
        return outcome.failed("asana", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("asana", str(e))
