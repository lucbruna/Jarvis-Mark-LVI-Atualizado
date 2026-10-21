"""JARVIS plugin - secure password generator."""
from __future__ import annotations

import secrets
import string

from core import outcome


PLUGIN = {
    "name": "password_gen",
    "description": "Generate secure passwords and passphrases.",
    "brief": "Generate secure passwords.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "length": {"type": "INTEGER", "description": "Password length (default 16)."},
            "count": {"type": "INTEGER", "description": "Number of passwords (default 1)."},
            "passphrase": {"type": "BOOLEAN", "description": "Generate passphrase instead (default false)."},
            "words": {"type": "INTEGER", "description": "Number of words for passphrase (default 4)."},
        },
        "required": [],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    count = int(params.get("count", 1))
    if params.get("passphrase"):
        words_list = ["correct", "horse", "battery", "staple", "purple", "monkey", "dishwasher", "cloud", "thunder", "quantum"]
        import random
        n = int(params.get("words", 4))
        results = ["-".join(random.choice(words_list) for _ in range(n)) for _ in range(count)]
    else:
        length = int(params.get("length", 16))
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        results = ["".join(secrets.choice(alphabet) for _ in range(length)) for _ in range(count)]
    msg = "\n".join(results)
    return outcome.done("password_gen", note=msg, passwords=results)
