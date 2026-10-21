"""JARVIS plugin - unit and currency converter."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "unit_converter",
    "description": "Convert units (length, weight, temperature, etc.) and currencies. Uses simple formulas and exchange rates API.",
    "brief": "Unit and currency converter.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "value": {"type": "NUMBER", "description": "Value to convert."},
            "from_unit": {"type": "STRING", "description": "Source unit/currency."},
            "to_unit": {"type": "STRING", "description": "Target unit/currency."},
        },
        "required": ["value", "from_unit", "to_unit"],
    },
    "tier": "extra",
}


# Simple conversion factors
_FACTORS = {
    ("m", "km"): 0.001, ("km", "m"): 1000,
    ("cm", "m"): 0.01, ("m", "cm"): 100,
    ("inch", "cm"): 2.54, ("cm", "inch"): 1 / 2.54,
    ("ft", "m"): 0.3048, ("m", "ft"): 1 / 0.3048,
    ("lb", "kg"): 0.453592, ("kg", "lb"): 1 / 0.453592,
    ("oz", "g"): 28.3495, ("g", "oz"): 1 / 28.3495,
    ("f", "c"): None, ("c", "f"): None,  # handled specially
    ("c", "k"): None, ("k", "c"): None,
}


def _convert_temp(value, from_u, to_u):
    f, t = from_u.lower(), to_u.lower()
    # to celsius first
    if f == "f":
        c = (value - 32) * 5 / 9
    elif f == "k":
        c = value - 273.15
    else:
        c = value
    if t == "f":
        return c * 9 / 5 + 32
    if t == "k":
        return c + 273.15
    return c


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    value = float(params.get("value", 0))
    from_u = params.get("from_unit", "").lower()
    to_u = params.get("to_unit", "").lower()

    # Temperature
    if from_u in ("c", "f", "k") and to_u in ("c", "f", "k"):
        result = _convert_temp(value, from_u, to_u)
        msg = f"{value} {from_u.upper()} = {result:.2f} {to_u.upper()}"
        return outcome.done("unit_converter", note=msg, result=result)

    # Currency
    if from_u in ("usd", "eur", "gbp", "try", "jpy", "brl") and to_u in ("usd", "eur", "gbp", "try", "jpy", "brl"):
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{from_u.upper()}"
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
            rate = data["rates"].get(to_u.upper(), 1)
            result = value * rate
            msg = f"{value} {from_u.upper()} = {result:.2f} {to_u.upper()}"
            return outcome.done("unit_converter", note=msg, result=result)
        except Exception as e:
            return outcome.failed("unit_converter", f"currency conversion failed: {e}")

    # Unit factors
    key = (from_u, to_u)
    if key in _FACTORS and _FACTORS[key] is not None:
        result = value * _FACTORS[key]
        msg = f"{value} {from_u} = {result:.4f} {to_u}"
        return outcome.done("unit_converter", note=msg, result=result)

    return outcome.failed("unit_converter", f"conversion not supported: {from_u} -> {to_u}")
