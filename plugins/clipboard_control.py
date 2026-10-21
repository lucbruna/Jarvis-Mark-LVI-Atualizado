"""Clipboard control for JARVIS.

Reads and writes the system clipboard, copies the current selection, pastes,
and keeps a short *in-memory* history so "put that back" works without writing
anything sensitive to disk.

The history is deliberately session-only: a clipboard can contain passwords,
tokens and private messages, and a file on disk outlives the reason it was
copied. It disappears when JARVIS restarts.
"""
from __future__ import annotations

import collections
import platform
import threading
import time

from core import outcome

try:
    import pyperclip
except Exception:
    pyperclip = None

_OS = platform.system()
_HISTORY = collections.deque(maxlen=20)
_HISTORY_LOCK = threading.Lock()
_MAX_READ = 4000


PLUGIN = {
    "name": "clipboard_control",
    "description": (
        "Reads, writes, appends to, clears, copies and pastes the system "
        "clipboard. Use for 'what is on my clipboard', 'copy this', 'put that "
        "on the clipboard', 'paste it', 'clear the clipboard', or 'show my "
        "clipboard history'. For copy and paste it sends the same Ctrl+C / "
        "Ctrl+V keystroke the user would. Do not use computer_settings for "
        "clipboard CONTENT: its copy/paste actions only send the keystroke and "
        "cannot read or write text."
    ),
    "brief": (
        "Reads/writes/copies/pastes the clipboard and keeps a short in-memory "
        "history. Use for clipboard content, not for ordinary typing."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "get | set | append | clear | copy | paste | history | restore"
                ),
                "enum": [
                    "get", "set", "append", "clear",
                    "copy", "paste", "history", "restore",
                ],
            },
            "text": {
                "type": "STRING",
                "description": "Text for action='set' or action='append'.",
            },
            "separator": {
                "type": "STRING",
                "description": (
                    "Separator used by action='append' between the old and new "
                    "text. Defaults to a newline; pass an empty string to join "
                    "with nothing."
                ),
            },
            "index": {
                "type": "INTEGER",
                "description": (
                    "History entry for action='restore': 1 is the most recent, "
                    "2 the one before it, and so on."
                ),
            },
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _clip():
    if pyperclip is None:
        raise RuntimeError(
            "pyperclip is not installed. Run: pip install pyperclip"
        )
    return pyperclip


def _read() -> str:
    return _clip().paste() or ""


def _write(text) -> None:
    _clip().copy(str(text))


def _remember(text: str, source: str) -> None:
    with _HISTORY_LOCK:
        _HISTORY.appendleft({
            "source": source,
            "text": str(text),
            "at": time.time(),
        })


def _history_rows() -> list[dict]:
    with _HISTORY_LOCK:
        return list(_HISTORY)


def _show(player, title: str, text: str) -> None:
    if player and hasattr(player, "show_content"):
        try:
            player.show_content(title, text[:_MAX_READ])
        except Exception:
            pass


def _restore_undo(old: str):
    def _restore():
        _write(old)
        return "Previous clipboard restored."
    return _restore


def _push_undo(label: str, old: str) -> None:
    try:
        from core.undo import push_undo
        push_undo(label, _restore_undo(old))
    except Exception:
        pass


def _clipboard_result(action: str, text: str) -> str:
    """A status line plus the text, wrapped as untrusted data for the model."""
    if not text:
        return outcome.done("clipboard_control", requested_action=action, chars=0, empty=True)
    shown = text[:_MAX_READ]
    line = outcome.done(
        "clipboard_control",
        requested_action=action,
        chars=len(text),
        truncated=len(text) > len(shown),
    )
    return line + "\n" + outcome.untrusted("clipboard", shown)


def _hotkey(keys: list[str]) -> None:
    try:
        import pyautogui
    except Exception as e:
        raise RuntimeError(f"pyautogui is not installed: {e}")
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    pyautogui.hotkey(*keys)


def _mod_key() -> str:
    return "command" if _OS == "Darwin" else "ctrl"


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = str(parameters.get("action") or "").strip().lower()

    try:
        if action == "get":
            text = _read()
            _show(player, "CLIPBOARD", text or "(empty)")
            return _clipboard_result("get", text)

        if action == "set":
            text = str(parameters.get("text") or "")
            if not text:
                return outcome.failed(
                    "clipboard_control",
                    "text is required for action='set'",
                    requested_action="set",
                )
            old = _read()
            _write(text)
            verified = _read() == text
            _remember(text, "set")
            _push_undo("clipboard set", old)
            if verified:
                return outcome.done(
                    "clipboard_control", requested_action="set", chars=len(text),
                    verified=True,
                )
            return outcome.unverified(
                "clipboard_control",
                "the clipboard did not read back exactly as written",
                requested_action="set", chars=len(text),
            )

        if action == "append":
            text = str(parameters.get("text") or "")
            if not text:
                return outcome.failed(
                    "clipboard_control",
                    "text is required for action='append'",
                    requested_action="append",
                )
            sep = parameters.get("separator")
            sep = "\n" if sep is None else str(sep)
            old = _read()
            new = old + (sep if old and sep else "") + text
            _write(new)
            verified = _read() == new
            _remember(new, "append")
            _push_undo("clipboard append", old)
            if verified:
                return outcome.done(
                    "clipboard_control", requested_action="append", chars=len(new),
                    verified=True,
                )
            return outcome.unverified(
                "clipboard_control",
                "the clipboard did not read back exactly as written",
                requested_action="append", chars=len(new),
            )

        if action == "clear":
            old = _read()
            _write("")
            verified = _read() == ""
            _remember("", "clear")
            _push_undo("clipboard clear", old)
            if verified:
                return outcome.done(
                    "clipboard_control", requested_action="clear", verified=True
                )
            return outcome.unverified(
                "clipboard_control",
                "the clipboard did not read back empty",
                requested_action="clear",
            )

        if action == "copy":
            before = _read()
            _hotkey([_mod_key(), "c"])
            time.sleep(0.35)
            after = _read()
            if after == before:
                return outcome.unverified(
                    "clipboard_control",
                    "the clipboard did not change; no text may have been "
                    "selected, or the focused application did not respond",
                    requested_action="copy",
                )
            _remember(after, "copy")
            _show(player, "CLIPBOARD", after)
            return _clipboard_result("copy", after)

        if action == "paste":
            text = _read()
            _hotkey([_mod_key(), "v"])
            return outcome.unverified(
                "clipboard_control",
                "the paste keystroke was sent, but the target application "
                "cannot confirm that it accepted it",
                requested_action="paste", chars=len(text),
            )

        if action == "history":
            rows = _history_rows()
            if not rows:
                return outcome.done(
                    "clipboard_control", requested_action="history", count=0
                )
            lines = []
            for i, row in enumerate(rows, 1):
                text = row.get("text") or ""
                preview = " ".join(text.split())[:70]
                if len(text) > 70:
                    preview += "..."
                lines.append(
                    f"{i}. {row.get('source', '?')} ({len(text)} chars): {preview}"
                )
            table = "\n".join(lines)
            _show(player, "CLIPBOARD HISTORY", table)
            return outcome.done(
                "clipboard_control", requested_action="history", count=len(rows)
            ) + "\n" + table

        if action == "restore":
            try:
                index = int(parameters.get("index") or 0)
            except Exception:
                index = 0
            rows = _history_rows()
            if index < 1 or index > len(rows):
                return outcome.failed(
                    "clipboard_control",
                    f"index must be between 1 and {len(rows)}",
                    requested_action="restore", index=index,
                )
            entry = rows[index - 1]
            text = entry.get("text") or ""
            old = _read()
            _write(text)
            verified = _read() == text
            _remember(text, "restore")
            _push_undo("clipboard restore", old)
            if verified:
                return outcome.done(
                    "clipboard_control",
                    requested_action="restore", index=index, chars=len(text),
                    verified=True,
                )
            return outcome.unverified(
                "clipboard_control",
                "the clipboard did not read back exactly as written",
                requested_action="restore", index=index, chars=len(text),
            )

        return outcome.failed(
            "clipboard_control",
            f"unknown action '{action}'",
            requested_action=action,
        )

    except Exception as e:
        return outcome.failed(
            "clipboard_control", str(e), requested_action=action
        )
