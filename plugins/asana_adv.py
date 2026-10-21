"""JARVIS plugin - Asana advanced (sections, tags, attachments)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "asana_adv",
    "description": "Asana advanced: sections, tags, attachments, subtasks.",
    "brief": "Asana advanced: sections/tags/attachments/subtasks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "sections|tags|add_subtask|attach"},
            "project_id": {"type": "STRING", "description": "Project id."},
            "task_id": {"type": "STRING", "description": "Task id."},
            "name": {"type": "STRING", "description": "Section/tag/subtask name."},
            "file_path": {"type": "STRING", "description": "File to attach (attach)."},
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
        return outcome.failed("asana_adv", "Asana token not configured")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        if action == "sections":
            pid = params.get("project_id", "")
            req = urllib.request.Request(f"https://app.asana.com/api/1.0/projects/{pid}/sections", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            sections = data.get("data", [])
            lines = [f"- {s['gid']}: {s['name']}" for s in sections]
            return outcome.done("asana_adv", note="\n".join(lines) or "no sections", count=len(sections))
        if action == "tags":
            req = urllib.request.Request("https://app.asana.com/api/1.0/tags", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            tags = data.get("data", [])
            lines = [f"- {t['gid']}: {t['name']}" for t in tags]
            return outcome.done("asana_adv", note="\n".join(lines) or "no tags", count=len(tags))
        if action == "add_subtask":
            tid = params.get("task_id", "")
            body = {"data": {"name": params.get("name", ""), "parent": tid}}
            req = urllib.request.Request("https://app.asana.com/api/1.0/tasks", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("asana_adv", note=f"subtask created: {data['data']['gid']}")
        return outcome.failed("asana_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("asana_adv", str(e))
