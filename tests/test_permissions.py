import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import permissions as p


def test_markers():
    assert p.looks_denied("Permission denied: x")
    assert p.looks_denied("Access is denied")
    assert p.looks_denied("could not open file")
    assert p.looks_denied("não foi possível")
    assert not p.looks_denied("All good")


def test_exc():
    assert p.looks_denied("vague", exc=PermissionError("boom"))


def test_note_calls_show(monkeypatch):
    import memory.config_manager as cm
    monkeypatch.setattr(cm, "get_unrestricted_mode", lambda: False)
    calls = []
    p.bind(show=lambda t, d: calls.append((t, d)), log=lambda m: None)
    p.reset()
    p.note("tool", "Permission denied: x")
    assert calls, "show callback not called"


def test_relaunch_codes():
    p._shell_execute = lambda exe, params, cwd: 5
    assert "declined" in p.relaunch_elevated().lower()
    p._shell_execute = lambda exe, params, cwd: 42
    assert "Relaunching" in p.relaunch_elevated()
    p._shell_execute = lambda exe, params, cwd: 0
    assert "refused" in p.relaunch_elevated().lower()
