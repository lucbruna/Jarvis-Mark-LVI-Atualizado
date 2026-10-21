"""JARVIS plugin - Notion/Obsidian notes integration."""
from __future__ import annotations

import json
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "notes_notion",
    "description": "Read/write notes in Notion or Obsidian vault. Actions: search, create, append, list.",
    "brief": "Notes: Notion/Obsidian search/create/append.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "provider": {"type": "STRING", "description": "notion|obsidian"},
            "action": {"type": "STRING", "description": "search|create|append|list"},
            "query": {"type": "STRING", "description": "Search query."},
            "title": {"type": "STRING", "description": "Page/note title (create)."},
            "content": {"type": "STRING", "description": "Content (create/append)."},
            "vault_path": {"type": "STRING", "description": "Obsidian vault path."},
        },
        "required": ["provider", "action"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    provider = (params.get("provider") or "").lower()
    action = (params.get("action") or "").lower()

    if provider == "obsidian":
        vault = Path(params.get("vault_path") or "").expanduser()
        if not vault.exists():
            return outcome.failed("notes_notion", f"vault not found: {vault}")
        if action == "list":
            files = list(vault.rglob("*.md"))[:30]
            return outcome.done("notes_notion", note="\n".join(str(f.relative_to(vault)) for f in files), count=len(files))
        if action == "search":
            q = params.get("query", "").lower()
            matches = []
            for f in vault.rglob("*.md"):
                try:
                    if q in f.read_text(encoding="utf-8", errors="ignore").lower():
                        matches.append(str(f.relative_to(vault)))
                except Exception:
                    pass
            return outcome.done("notes_notion", note="\n".join(matches[:20]) or "no matches", count=len(matches))
        if action == "create":
            title = params.get("title", "Untitled")
            path = vault / f"{title}.md"
            path.write_text(params.get("content", ""), encoding="utf-8")
            return outcome.done("notes_notion", note=f"created {path}")
        if action == "append":
            title = params.get("title", "")
            path = vault / f"{title}.md"
            if path.exists():
                path.write_text(path.read_text(encoding="utf-8") + "\n" + params.get("content", ""), encoding="utf-8")
                return outcome.done("notes_notion", note=f"appended to {path}")
            return outcome.failed("notes_notion", f"note not found: {title}")
        return outcome.failed("notes_notion", f"unknown action: {action}")

    if provider == "notion":
        try:
            import requests
            cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
            token = cfg.get("notion_token", "")
            if not token:
                return outcome.failed("notes_notion", "Notion token not configured")
            headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
            if action == "search":
                r = requests.post("https://api.notion.com/v1/search", headers=headers, json={"query": params.get("query", "")}, timeout=15)
                r.raise_for_status()
                results = r.json().get("results", [])
                lines = [f"- {r.get('properties', {}).get('title', {}).get('title', [{}])[0].get('text', {}).get('content', '?')}" for r in results[:10]]
                return outcome.done("notes_notion", note="\n".join(lines) or "no results", count=len(results))
            return outcome.failed("notes_notion", f"action '{action}' not implemented for Notion yet")
        except ImportError:
            return outcome.failed("notes_notion", "requests not installed")
        except Exception as e:
            return outcome.failed("notes_notion", str(e))

    return outcome.failed("notes_notion", f"unknown provider: {provider}")
