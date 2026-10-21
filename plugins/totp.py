"""JARVIS plugin - TOTP/2FA code generator."""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "totp",
    "description": "Generate TOTP/2FA codes from stored secrets. Actions: add, generate, list, remove.",
    "brief": "TOTP/2FA code generator.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add|generate|list|remove"},
            "name": {"type": "STRING", "description": "Account name (add/generate/remove)."},
            "secret": {"type": "STRING", "description": "Base32 secret (add)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_STORE = Path(__file__).resolve().parents[1] / "memory" / "totp_secrets.json"


def _load():
    try:
        if _STORE.exists():
            return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"secrets": {}}


def _save(d):
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def _generate(secret: str) -> str:
    try:
        import pyotp
    except ImportError:
        # fallback manual TOTP
        import hmac, hashlib, struct
        key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
        counter = int(time.time()) // 30
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        code = (struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF) % 1000000
        return f"{code:06d}"
    totp = pyotp.TOTP(secret)
    return totp.now()


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    d = _load()
    secrets = d.setdefault("secrets", {})
    if action == "add":
        name = params.get("name", "")
        secret = params.get("secret", "")
        if not name or not secret:
            return outcome.failed("totp", "name and secret required")
        secrets[name] = secret
        _save(d)
        return outcome.done("totp", note=f"added TOTP for {name}")
    if action == "generate":
        name = params.get("name", "")
        if name not in secrets:
            return outcome.failed("totp", f"no secret for {name}")
        code = _generate(secrets[name])
        msg = f"{name}: {code}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("totp", note=msg, code=code)
    if action == "list":
        lines = [f"- {n}" for n in secrets]
        return outcome.done("totp", note="\n".join(lines) or "no secrets", count=len(secrets))
    if action == "remove":
        name = params.get("name", "")
        if name in secrets:
            del secrets[name]
            _save(d)
            return outcome.done("totp", note=f"removed {name}")
        return outcome.failed("totp", f"not found: {name}")
    return outcome.failed("totp", f"unknown action: {action}")
