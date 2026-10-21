"""JARVIS plugin - Jira advanced (transitions, attachments, search)."""
from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "jira_adv",
    "description": "Jira advanced: transitions, attachments, JQL search, assign.",
    "brief": "Jira advanced: transitions/attachments/search/assign.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "transitions|transition|attach|search|assign"},
            "issue_key": {"type": "STRING", "description": "Issue key."},
            "transition": {"type": "STRING", "description": "Transition name/id (transition)."},
            "file_path": {"type": "STRING", "description": "File to attach (attach)."},
            "jql": {"type": "STRING", "description": "JQL query (search)."},
            "assignee": {"type": "STRING", "description": "Assignee account id (assign)."},
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
        return outcome.failed("jira_adv", "Jira not configured")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    base = url.rstrip("/")
    try:
        if action == "transitions":
            key = params.get("issue_key", "")
            req = urllib.request.Request(f"{base}/rest/api/3/issue/{key}/transitions", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            trans = data.get("transitions", [])
            lines = [f"- {t['id']}: {t['name']}" for t in trans]
            return outcome.done("jira_adv", note="\n".join(lines) or "no transitions")
        if action == "transition":
            key = params.get("issue_key", "")
            tid = params.get("transition", "")
            body = {"transition": {"id": tid}}
            req = urllib.request.Request(f"{base}/rest/api/3/issue/{key}/transitions", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                pass
            return outcome.done("jira_adv", note=f"transitioned {key} to {tid}")
        if action == "search":
            jql = params.get("jql", "order by created DESC")
            import urllib.parse
            req = urllib.request.Request(f"{base}/rest/api/3/search?jql={urllib.parse.quote(jql)}&maxResults=10", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            issues = data.get("issues", [])
            lines = [f"- {i['key']}: {i['fields'].get('summary', '')}" for i in issues]
            return outcome.done("jira_adv", note="\n".join(lines) or "no issues", count=len(issues))
        if action == "assign":
            key = params.get("issue_key", "")
            aid = params.get("assignee", "")
            body = {"fields": {"assignee": {"id": aid}}}
            req = urllib.request.Request(f"{base}/rest/api/3/issue/{key}", data=json.dumps(body).encode(), headers=headers, method="PUT")
            with urllib.request.urlopen(req, timeout=15) as r:
                pass
            return outcome.done("jira_adv", note=f"assigned {key} to {aid}")
        if action == "attach":
            key = params.get("issue_key", "")
            fp = params.get("file_path", "")
            # multipart upload
            import mimetypes
            mime = mimetypes.guess_type(fp)[0] or "application/octet-stream"
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            data = open(fp, "rb").read()
            body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{Path(fp).name}\"\r\nContent-Type: {mime}\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
            headers2 = {"Authorization": f"Basic {auth}", "X-Atlassian-Token": "no-check", "Content-Type": f"multipart/form-data; boundary={boundary}"}
            req = urllib.request.Request(f"{base}/rest/api/3/issue/{key}/attachments", data=body, headers=headers2, method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read())
            return outcome.done("jira_adv", note=f"attached to {key}")
        return outcome.failed("jira_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("jira_adv", str(e))
