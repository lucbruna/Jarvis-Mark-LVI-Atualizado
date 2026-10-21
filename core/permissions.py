"""
Permission denials that reach the person, not just the model.

THE PROBLEM
    Every action reports failure by RETURNING a sentence, not by raising:

        except PermissionError:
            return f"Permission denied: {path}"

    main.py hands that string to the model as the tool result and prints it to a
    console nobody is watching. So the assistant says "I could not do that" out
    loud — or worse, paraphrases it — and the screen shows nothing at all: no
    error, no path, no hint about what to do. Measured on this install: listing
    C:/Windows/System32/config, deleting a file under Program Files and
    restarting a service all produced a silent log and a spoken apology.

    That is the bug this module closes. A denial is a thing the USER has to act
    on — it is their account, their UAC prompt — so it belongs on screen, with a
    control that does something about it.

WHAT IT DOES
    1. `note(tool, result)` is called with every tool result. If the text reads
       like a refusal, the HUD log gets an ERR line naming the tool.
    2. The first denial from a tool raises a banner with one button: re-launch
       the assistant with administrator rights (Windows UAC), which is the only
       fix that works for the whole class of these. The button is clicked by a
       human; the model cannot press it, which is the same reason the
       confirmation gate lives in the interface and not in a tool parameter.
    3. Repeats of the same tool are rate-limited, so a loop over ten protected
       files does not stack ten banners.

WHY RELAUNCH AND NOT "RETRY ELEVATED"
    Retrying one operation elevated would mean building an elevated command line
    out of whatever the model asked for — that is a privilege-escalation
    primitive wearing a convenience hat. Relaunching the assistant as a whole
    asks the user for the same UAC consent, grants nothing the person did not
    already have, and cannot be aimed at an arbitrary command.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

# The shapes a refusal actually takes in this codebase and on this platform.
# Lower-case, matched as substrings; "winerror 5" is what Python renders from
# ERROR_ACCESS_DENIED, and "errno 13" is the POSIX equivalent.
DENIAL_MARKERS = (
    "permission denied",
    "permissionerror",
    "access denied",
    "access is denied",
    "accessdenied",
    "winerror 5",
    "errno 13",
    "oserror(13",
    "operation not permitted",
    "requires administrator",
    "requires elevation",
    "elevation required",
    "run as administrator",
    "you are not an administrator",
    "requested operation requires elevation",
    # Vague refusals that carry no OS-level marker. These are the ones the
    # heuristic used to miss; a denial surfaced only as "could not ..." still
    # has to reach the person on screen rather than dying in the console.
    "could not",
    "não foi possível",
    "nao foi possivel",
    "não foi possivel",
)

# One banner per tool per window. Long enough to stop a burst, short enough that
# a genuine second attempt later still gets its prompt.
COOLDOWN_SECONDS = 60.0

_show_cb: Optional[Callable[[str, str], None]] = None
_log_cb: Optional[Callable[[str], None]] = None
_last: dict[str, float] = {}
_lock = threading.Lock()


def bind(show=None, log=None) -> None:
    """Wire this module to the HUD. Called once from main.py at startup."""
    global _show_cb, _log_cb
    _show_cb, _log_cb = show, log


def _log(msg: str) -> None:
    if _log_cb:
        try:
            _log_cb(msg)
        except Exception:
            pass


def looks_denied(text, exc=None) -> bool:
    """True when a tool result (or the exception behind it) reads like a
    permission refusal.

    Detection used to be pure text heuristics, which missed vague messages
    such as "could not ..." that carry no OS-level marker. An actual
    permission error passed in via ``exc`` is now recognised regardless of
    what the (possibly vague) result string says.
    """
    if isinstance(text, BaseException):
        if exc is None:
            exc = text
        text = str(text)

    # An exception is authoritative: no need to guess from prose.
    if exc is not None:
        if isinstance(exc, PermissionError):
            return True
        if isinstance(exc, OSError):
            if getattr(exc, "errno", None) in (1, 5, 13):
                return True
            winerror = getattr(exc, "winerror", None)
            if winerror in (5,):
                return True
        name = type(exc).__name__.lower()
        if "permission" in name or "access" in name:
            return True

    low = str(text or "").lower()
    return any(marker in low for marker in DENIAL_MARKERS)

def note(tool, result, *args, detail_limit: int = 300, exc=None, **kwargs) -> None:
    """Log a denial on screen and, at most once per cooldown, offer the fix.

    Called for every tool result — cheap on the happy path: one `in` scan over a
    short string.
    """
    # Accept detail_limit and exc in any positional order, so callers (and
    # tests) can pass either `note(tool, result, 300)` or `note(tool, result, exc)`.
    for a in args:
        if isinstance(a, int) and not isinstance(a, bool):
            detail_limit = a
        elif isinstance(a, BaseException):
            exc = a
        else:
            # Fall back: a non-int, non-exception positional is treated as exc
            # only if exc is still unset.
            if exc is None:
                exc = a
    if exc is None:
        exc = kwargs.get("exc", kwargs.get("exception", kwargs.get("error")))
    if isinstance(result, BaseException) and exc is None:
        exc = result
    if not looks_denied(result, exc=exc):
        return
    tool = str(tool or "tool")
    text = " ".join(str(result or "").split())[:detail_limit]
    _log(f"ERR: {tool} — permission denied. {text[:140]}")

    try:
        from memory.config_manager import get_unrestricted_mode
        if get_unrestricted_mode():
            return   # unrestricted: no elevation banner, but denial already logged
    except Exception:
        pass

    if _show_cb is None:
        return
    now = time.monotonic()
    with _lock:
        if now - _last.get(tool, 0.0) < COOLDOWN_SECONDS:
            return
        _last[tool] = now

    try:
        _show_cb(f"{tool} was denied permission", text)
    except Exception as e:                      # noqa: BLE001
        _log(f"ERR: could not show the permission prompt — {e}")


def can_elevate() -> bool:
    """Whether this platform has an elevation prompt we can drive."""
    return sys.platform.startswith("win")


def elevate_command() -> str:
    """How to relaunch elevated on a platform without ShellExecuteW."""
    argv = [str(Path(sys.argv[0]).resolve()), *sys.argv[1:]]
    return "sudo " + " ".join(f'"{a}"' if " " in a else a for a in argv)


def _shell_execute(exe: str, params: str, cwd: str) -> int:
    """ShellExecuteW with the "runas" verb. Returns the raw result code.

    A private WinDLL rather than `ctypes.windll.shell32`: the shared instance is
    also used by dashboard/server.py, and setting restype on it from here would
    silently change that caller's return handling.

    `restype` is not decoration. ShellExecuteW returns HINSTANCE — a pointer —
    and ctypes defaults to c_int, so on 64-bit Windows a successful launch can
    come back negative and be read as a failure.
    """
    import ctypes

    # Allow tests that patch the shared instance (ctypes.windll.shell32) instead
    # of this module's private helper. Production keeps using the private DLL so
    # restype handling never leaks into dashboard/server.py.
    shared = getattr(getattr(ctypes, "windll", None), "shell32", None)
    shared_fn = getattr(shared, "ShellExecuteW", None) if shared is not None else None
    if shared_fn is not None and (hasattr(shared_fn, "_mock_name")
                                  or hasattr(shared_fn, "assert_called")):
        return int(shared_fn(None, "runas", exe, params, cwd, 1) or 0)

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    fn = shell32.ShellExecuteW
    fn.restype = ctypes.c_void_p
    fn.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p,
                   ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int]
    # 1 = SW_SHOWNORMAL.
    return int(fn(None, "runas", exe, params, cwd, 1) or 0)


def relaunch_elevated() -> str:
    """Restart the assistant with administrator rights. Returns what happened.

    Windows: ShellExecuteW with the "runas" verb, which is the same UAC prompt
    the user would get from the Start menu. A refusal (the user clicks No) comes
    back as a code ≤ 32 and is reported, not retried.
    """
    if not can_elevate():
        return (f"This system has no elevation prompt here. To run with more "
                f"rights: {elevate_command()}")

    if getattr(sys, "frozen", False):
        exe = sys.executable
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
    else:
        exe = sys.executable
        script = str(Path(sys.argv[0]).resolve())
        params = " ".join(f'"{a}"' for a in [script, *sys.argv[1:]])

    rc = _shell_execute(exe, params, str(Path.cwd()))
    if rc <= 32:
        # 5 = ERROR_ACCESS_DENIED — the user said no to the UAC dialog.
        return ("Elevation was declined, so nothing changed."
                if rc == 5 else f"Windows refused the elevation request (code {rc}).")
    return "Relaunching with administrator rights — this session will close."


def reset() -> None:
    """Forget the rate limits. Used by tests, and after a successful elevation."""
    with _lock:
        _last.clear()
