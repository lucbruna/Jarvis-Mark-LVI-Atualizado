"""core/i18n.py - minimal internationalization helper.

Loads a JSON dictionary of translations for the active locale from
config/i18n/<lang>.json. Falls back to the key itself when no translation
is present, so callers can always print t("some.key") safely. Locale is read
from config or env (JARVIS_LANG).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_LOCALE = None
_STRINGS: dict = {}


def _locale() -> str:
    global _LOCALE
    if _LOCALE is not None:
        return _LOCALE
    lang = os.environ.get("JARVIS_LANG", "").strip()
    if not lang:
        try:
            import json as _j
            cfg = _j.loads((_BASE / "config" / "api_keys.json").read_text(encoding="utf-8"))
            lang = (cfg.get("language") or cfg.get("ui_language") or "").strip()
        except Exception:
            lang = ""
    _LOCALE = (lang or "en").lower()[:2]
    return _LOCALE


def load() -> dict:
    global _STRINGS
    if _STRINGS:
        return _STRINGS
    p = _BASE / "config" / "i18n" / f"{_locale()}.json"
    try:
        if p.exists():
            _STRINGS = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        _STRINGS = {}
    return _STRINGS


def t(key: str, **fmt) -> str:
    load()
    # support dotted keys
    cur = _STRINGS
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            cur = None
            break
    if not isinstance(cur, str):
        cur = key
    try:
        return cur.format(**fmt) if fmt else cur
    except Exception:
        return cur
