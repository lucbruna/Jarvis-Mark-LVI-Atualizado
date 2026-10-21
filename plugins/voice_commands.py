"""JARVIS plugin - custom voice commands mapping."""
from __future__ import annotations

import json
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "voice_commands",
    "description": "Map custom voice phrases to actions. Actions: add, list, remove, match.",
    "brief": "Custom voice command mappings.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add|list|remove|match"},
            "phrase": {"type": "STRING", "description": "Voice phrase (add/match/remove)."},
            "command": {"type": "STRING", "description": "Action to trigger (add)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_STORE = Path(__file__).resolve().parents[1] / "memory" / "voice_commands.json"


def _load():
    try:
        if _STORE.exists():
            return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"commands": {}}


def _save(d):
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    d = _load()
    cmds = d.setdefault("commands", {})
    if action == "add":
        phrase = params.get("phrase", "")
        command = params.get("command", "")
        if not phrase or not command:
            return outcome.failed("voice_commands", "phrase and command required")
        cmds[phrase.lower()] = command
        _save(d)
        return outcome.done("voice_commands", note=f"mapped '{phrase}' -> {command}")
    if action == "list":
        lines = [f"- '{k}': {v}" for k, v in cmds.items()]
        return outcome.done("voice_commands", note="\n".join(lines) or "no custom commands", count=len(cmds))
    if action == "remove":
        phrase = params.get("phrase", "").lower()
        if phrase in cmds:
            del cmds[phrase]
            _save(d)
            return outcome.done("voice_commands", note=f"removed '{phrase}'")
        return outcome.failed("voice_commands", f"not found: {phrase}")
    if action == "match":
        phrase = params.get("phrase", "").lower()
        # simple substring match
        for k, v in cmds.items():
            if k in phrase or phrase in k:
                return outcome.done("voice_commands", note=f"matched: {v}", command=v)
        return outcome.done("voice_commands", note="no match", command=None)
    return outcome.failed("voice_commands", f"unknown action: {action}")
