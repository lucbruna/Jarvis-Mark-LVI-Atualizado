"""JARVIS plugin - Jira integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "jira",
    "description": "Jira: list issues, create issues, transition, comment.",
    "brief": "Jira: issues CRUD.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list|create|transition|comment"},
            "project": {"type": "STRING", "description": "Project key."},
            "summary": {"type": "STRING", "description": "Issue summary (create)."},
            "description": {"type": "STRING", "description": "Issue description (create)."},
            "issue_key": {"type": "STRING", "description": "Issue key (transition/comment)."},
            "transition": {"type": "STRING", "description": "Transition name (transition)."},
            "comment": {"type": "STRING", "description": "Comment text (comment)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _cfg():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("jira_url", ""), cfg.get("jira_email", ""), cfg.get("jira_token", "")
    except Exception:
        return "", "", ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    url, email, token = _cfg()
    if not url or not token:
        return outcome.failed("jira", "Jira not configured (jira_url/email/token)")
    import base64
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    base = url.rstrip("/")
    try:
        if action == "list":
            project = params.get("project", "")
            jql = f"project={project}" if project else "order by created DESC"
            req = urllib.request.Request(f"{base}/rest/api/3/search?jql={__import__('urllib.parse').parse.quote(jql)}&maxResults=10", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            lines = [f"- {i['key']}: {i['fields'].get('summary', '')}" for i in data.get("issues", [])]
            return outcome.done("jira", note="\n".join(lines) or "no issues", count=len(data.get("issues", [])))
        if action == "create":
            body = {"fields": {"project": {"key": params.get("project", "")}, "summary": params.get("summary", ""), "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": params.get("description", "")}]}]}, "issuetype": {"name": "Task"}}}
            req = urllib.request.Request(f"{base}/rest/api/3/issue", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("jira", note=f"created {data.get('key')}", key=data.get("key"))
        if action == "comment":
            key = params.get("issue_key", "")
            body = {"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": params.get("comment", "")}]}]}}
            req = urllib.request.Request(f"{base}/rest/api/3/issue/{key}/comment", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("jira", note=f"commented on {key}")
        return outcome.failed("jira", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("jira", str(e))
