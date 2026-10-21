"""JARVIS plugin - multi-agent task orchestration."""
from __future__ import annotations

from core import gemini, outcome, multi_agent


PLUGIN = {
    "name": "multi_agent",
    "description": "Decompose a complex task into sub-tasks and run them in parallel via multiple agents.",
    "brief": "Multi-agent task orchestration.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {"type": "STRING", "description": "High-level task to decompose and execute."},
            "max_agents": {"type": "INTEGER", "description": "Max parallel agents (default 4)."},
        },
        "required": ["task"],
    },
    "tier": "extra",
}


def _worker(subtask: str) -> str:
    try:
        resp = gemini.call(f"Execute this sub-task and report the result concisely:\n\n{subtask}", tier=gemini.SMART, timeout_ms=30000)
        return getattr(resp, "text", "no response") if resp else "no response"
    except Exception as e:
        return f"failed: {e}"


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    task = params.get("task", "")
    max_agents = int(params.get("max_agents", 4))
    subtasks = multi_agent.decompose(task, n=max_agents)
    if player:
        try: player.write_log(f"JARVIS: decomposed into {len(subtasks)} sub-tasks")
        except Exception: pass
    results = multi_agent.run_parallel(subtasks, _worker, max_workers=max_agents)
    lines = [f"## {st}\n{res}" for st, res in results]
    msg = "\n\n".join(lines)
    if player:
        try: player.write_log(f"JARVIS: {msg[:400]}")
        except Exception: pass
    return outcome.done("multi_agent", note=msg[:500], results=results)
