"""core/multi_agent.py - simple multi-agent task orchestrator.

Decomposes a high-level task into sub-tasks (via Gemini) and runs them in
parallel, collecting results. Used by the multi_agent plugin.
"""
from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable


def decompose(task: str, n: int = 4) -> list[str]:
    """Ask Gemini to split a task into up to n independent sub-tasks."""
    try:
        from core import gemini
        prompt = (f"Break this task into up to {n} independent sub-tasks that can be "
                  f"executed in parallel. Return a JSON array of strings.\n\nTask: {task}")
        resp = gemini.call(prompt, tier=gemini.FAST, timeout_ms=20000)
        raw = getattr(resp, "text", "[]") if resp else "[]"
        import re
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))[:n]
    except Exception:
        pass
    return [task]


def run_parallel(subtasks: list[str], worker: Callable[[str], str], max_workers: int = 4) -> list[tuple[str, str]]:
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut = {ex.submit(worker, st): st for st in subtasks}
        for f in as_completed(fut):
            st = fut[f]
            try:
                results.append((st, f.result()))
            except Exception as e:
                results.append((st, f"error: {e}"))
    return results
