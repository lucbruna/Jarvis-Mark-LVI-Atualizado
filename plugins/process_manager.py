"""Process manager for JARVIS.

Lists and inspects running processes, and ends one when the user explicitly
asks. Ending a process is irreversible from the assistant's point of view, so
it always goes through the HUD confirmation gate in core/confirm.py: the model
cannot supply a "confirmed" flag and make it happen on its own.
"""
from __future__ import annotations

import os
import time

from core import confirm, outcome

try:
    import psutil
except Exception:
    psutil = None

# Processes Windows itself needs. Ending one of these can log the user out,
# break networking, or require a reboot to recover. The list is intentionally
# short: it protects the machine, not every application the user might dislike.
_PROTECTED = {
    "system",
    "system idle process",
    "registry",
    "memory compression",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "winlogon.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
}


PLUGIN = {
    "name": "process_manager",
    "description": (
        "Lists, finds, inspects and ends running processes. Use for 'what is "
        "using my RAM/CPU', 'is Chrome running', 'show me the top processes', "
        "or 'end process 1234' / 'kill notepad'. Ending a process is "
        "irreversible and always puts a confirmation on the user's screen; "
        "never claim it is done before they press CONFIRM."
    ),
    "brief": (
        "Lists/finds/inspects processes and ends one after an on-screen CONFIRM. "
        "Use for CPU/RAM usage and process names."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "list | find | info | kill",
                "enum": ["list", "find", "info", "kill"],
            },
            "sort": {
                "type": "STRING",
                "description": "For list: memory | cpu | name. Default memory.",
                "enum": ["memory", "cpu", "name"],
            },
            "limit": {
                "type": "INTEGER",
                "description": "For list: number of rows, 1-50. Default 15.",
            },
            "name": {
                "type": "STRING",
                "description": (
                    "For find/kill: process name or part of it, e.g. 'chrome' "
                    "or 'notepad.exe'."
                ),
            },
            "pid": {
                "type": "INTEGER",
                "description": "For info/kill: exact process ID.",
            },
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _ps():
    if psutil is None:
        raise RuntimeError(
            "psutil is not installed. Run: pip install psutil"
        )
    return psutil


def _show(player, title: str, text: str) -> None:
    if player and hasattr(player, "show_content"):
        try:
            player.show_content(title, text[:4000])
        except Exception:
            pass


def _snapshot(with_cpu: bool = True) -> list[dict]:
    ps = _ps()
    if with_cpu:
        try:
            for proc in ps.process_iter():
                try:
                    proc.cpu_percent(None)
                except Exception:
                    pass
            time.sleep(0.15)
        except Exception:
            pass

    rows = []
    for proc in ps.process_iter(
        ["pid", "name", "memory_info", "status", "cpu_percent"]
    ):
        try:
            info = proc.info
            mem = info.get("memory_info")
            mem_mb = (getattr(mem, "rss", 0) or 0) / (1024 * 1024)
            rows.append({
                "pid": int(info.get("pid") or 0),
                "name": str(info.get("name") or "?"),
                "cpu": float(info.get("cpu_percent") or 0.0),
                "mem_mb": float(mem_mb),
                "status": str(info.get("status") or "?"),
            })
        except (ps.NoSuchProcess, ps.AccessDenied):
            continue
        except Exception:
            continue
    return rows


def _table(rows: list[dict], limit: int | None = None) -> str:
    shown = rows[:limit] if limit else rows
    lines = [
        f"{'PID':>7}  {'NAME':<28} {'CPU%':>6} {'MEM MB':>8}  STATUS"
    ]
    for row in shown:
        name = (row.get("name") or "?")[:28]
        lines.append(
            f"{row['pid']:>7}  {name:<28} {row['cpu']:>6.1f} "
            f"{row['mem_mb']:>8.1f}  {row.get('status', '?')}"
        )
    if limit and len(rows) > limit:
        lines.append(f"... {len(rows) - limit} more")
    return "\n".join(lines)


def _matches(query: str) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    ps = _ps()
    rows = _snapshot(with_cpu=False)
    matches = []
    for row in rows:
        if q in (row.get("name") or "").lower():
            matches.append(row)
            continue
        # A process can be named node.exe while the meaningful word is in its
        # command line (a project name, for example). Include that too.
        try:
            proc = ps.Process(row["pid"])
            cmdline = " ".join(proc.cmdline()).lower()
            if q in cmdline:
                matches.append(row)
        except Exception:
            pass
    return matches


def _process_row(pid: int) -> dict | None:
    ps = _ps()
    try:
        proc = ps.Process(pid)
        info = proc.as_dict(
            attrs=[
                "pid", "name", "exe", "cmdline", "cwd", "username",
                "status", "create_time", "num_threads", "memory_info",
                "cpu_percent",
            ],
            ad_value="?",
        )
        mem = info.get("memory_info")
        info["mem_mb"] = round((getattr(mem, "rss", 0) or 0) / (1024 * 1024), 1)
        info.pop("memory_info", None)
        return info
    except ps.NoSuchProcess:
        return None
    except Exception:
        return None


def _kill(pid: int, name: str, player) -> str:
    ps = _ps()
    try:
        proc = ps.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except ps.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)

        if proc.is_running() and proc.status() != ps.STATUS_ZOMBIE:
            return outcome.failed(
                "process_manager",
                "the process is still running after terminate and kill",
                requested_action="kill", pid=pid, name=name,
            )

        if player and hasattr(player, "request_say"):
            try:
                player.request_say(
                    f"The process {name} with PID {pid} has been ended."
                )
            except Exception:
                pass

        return outcome.done(
            "process_manager", requested_action="kill",
            pid=pid, name=name, verified=True,
        )
    except ps.NoSuchProcess:
        return outcome.failed(
            "process_manager",
            "the process had already exited",
            requested_action="kill", pid=pid, name=name,
        )
    except Exception as e:
        return outcome.failed(
            "process_manager", str(e), requested_action="kill", pid=pid, name=name
        )


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = str(parameters.get("action") or "").strip().lower()

    try:
        if action == "list":
            rows = _snapshot()
            sort = str(parameters.get("sort") or "memory").strip().lower()
            if sort not in ("memory", "cpu", "name"):
                sort = "memory"
            key = {
                "memory": lambda r: r["mem_mb"],
                "cpu": lambda r: r["cpu"],
                "name": lambda r: (r.get("name") or "").lower(),
            }[sort]
            rows.sort(key=key, reverse=(sort != "name"))
            try:
                limit = int(parameters.get("limit") or 15)
            except Exception:
                limit = 15
            limit = max(1, min(50, limit))
            table = _table(rows, limit)
            _show(player, f"PROCESSES BY {sort.upper()}", table)
            return outcome.done(
                "process_manager", requested_action="list",
                count=len(rows), shown=min(limit, len(rows)), sort=sort,
            ) + "\n" + table

        if action == "find":
            query = str(parameters.get("name") or "").strip()
            if not query:
                return outcome.failed(
                    "process_manager",
                    "name is required for action='find'",
                    requested_action="find",
                )
            rows = _matches(query)
            if not rows:
                return outcome.done(
                    "process_manager", requested_action="find",
                    query=query, matches=0,
                ) + f"\nNo running process matches '{query}'."
            rows.sort(key=lambda r: (r.get("name") or "").lower())
            table = _table(rows, 25)
            _show(player, f"PROCESSES MATCHING {query.upper()}", table)
            return outcome.done(
                "process_manager", requested_action="find",
                query=query, matches=len(rows),
            ) + "\n" + table

        if action == "info":
            try:
                pid = int(parameters.get("pid") or 0)
            except Exception:
                pid = 0
            if pid <= 0:
                return outcome.failed(
                    "process_manager",
                    "a positive pid is required for action='info'",
                    requested_action="info",
                )
            info = _process_row(pid)
            if info is None:
                return outcome.failed(
                    "process_manager",
                    f"no running process has PID {pid}",
                    requested_action="info", pid=pid,
                )
            lines = []
            for key in (
                "pid", "name", "exe", "cmdline", "cwd", "username",
                "status", "num_threads", "mem_mb", "cpu_percent",
                "create_time",
            ):
                if key not in info:
                    continue
                value = info[key]
                if key == "create_time" and isinstance(value, (int, float)):
                    value = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(value)
                    )
                if isinstance(value, list):
                    value = " ".join(str(v) for v in value)
                lines.append(f"{key}: {value}")
            text = "\n".join(lines)
            _show(player, f"PROCESS {pid}", text)
            return outcome.done(
                "process_manager", requested_action="info", pid=pid
            ) + "\n" + text

        if action == "kill":
            raw_pid = parameters.get("pid")
            name = str(parameters.get("name") or "").strip()
            pid = 0
            target_name = name

            if raw_pid is not None and str(raw_pid).strip() != "":
                try:
                    pid = int(raw_pid)
                except Exception:
                    return outcome.failed(
                        "process_manager",
                        "pid must be an integer",
                        requested_action="kill",
                    )
                info = _process_row(pid)
                if info is None:
                    return outcome.failed(
                        "process_manager",
                        f"no running process has PID {pid}",
                        requested_action="kill", pid=pid,
                    )
                target_name = str(info.get("name") or name or "?")

            elif name:
                matches = _matches(name)
                exact = [
                    row for row in matches
                    if (row.get("name") or "").lower() == name.lower()
                ]
                pool = exact or matches
                if not pool:
                    return outcome.failed(
                        "process_manager",
                        f"no running process matches '{name}'",
                        requested_action="kill", name=name,
                    )
                if len(pool) > 1:
                    listing = ", ".join(
                        f"{row['pid']}={row.get('name', '?')}"
                        for row in pool[:10]
                    )
                    return outcome.ask(
                        "process_manager",
                        f"More than one process matches '{name}': {listing}. "
                        f"Which PID should I end?",
                        name=name, matches=len(pool),
                    )
                pid = int(pool[0]["pid"])
                target_name = str(pool[0].get("name") or name)

            else:
                return outcome.ask(
                    "process_manager",
                    "Which process should I end? Give me a PID or an "
                    "application name.",
                    requested_action="kill",
                )

            try:
                from memory.config_manager import get_unrestricted_mode
                _unlocked = get_unrestricted_mode()
            except Exception:
                _unlocked = False
            if not _unlocked and target_name.lower() in _PROTECTED:
                return outcome.failed(
                    "process_manager",
                    f"'{target_name}' is a protected Windows process; ending it "
                    f"can log you out or break the system",
                    requested_action="kill", pid=pid, name=target_name,
                )
            if not _unlocked and (pid in (0, 4) or pid == os.getpid()):
                return outcome.failed(
                    "process_manager",
                    "that process is protected or is JARVIS itself",
                    requested_action="kill", pid=pid, name=target_name,
                )

            if confirm.pending_title():
                return outcome.ask(
                    "process_manager",
                    "Another confirmation is already on screen. Confirm or "
                    "cancel it before ending a process.",
                    requested_action="kill", pid=pid, name=target_name,
                )

            info = _process_row(pid)
            mem = info.get("mem_mb") if info else "?"
            detail = (
                f"PID {pid} - {target_name}\n"
                f"Memory: {mem} MB\n\n"
                f"Ending a process is irreversible. Unsaved work in it will "
                f"be lost."
            )
            return confirm.request(
                "process_manager",
                f"End {target_name}?",
                detail,
                lambda: _kill(pid, target_name, player),
            )

        return outcome.failed(
            "process_manager",
            f"unknown action '{action}'",
            requested_action=action,
        )

    except Exception as e:
        return outcome.failed(
            "process_manager", str(e), requested_action=action
        )
