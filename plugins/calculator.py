"""Offline calculator for JARVIS.

Arithmetic is evaluated with a small AST walker, never `eval()`, so a sentence
that reaches this tool cannot execute code. Unit conversion, percentages and
base conversion are included because those are the sums people ask a voice
assistant for most often.
"""
from __future__ import annotations

import ast
import math
import operator

from core import outcome

_MAX_NODES = 250
_MAX_RESULT = 1e100

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_FUNCS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log,
    "log10": math.log10,
    "ln": math.log,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
}

_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}

# unit -> (category, factor to that category's base unit)
_UNITS = {
    # length (base: metre)
    "mm": ("length", 0.001),
    "cm": ("length", 0.01),
    "m": ("length", 1.0),
    "km": ("length", 1000.0),
    "in": ("length", 0.0254),
    "ft": ("length", 0.3048),
    "yd": ("length", 0.9144),
    "mi": ("length", 1609.344),
    "nmi": ("length", 1852.0),
    # mass (base: kilogram)
    "mg": ("mass", 0.000001),
    "g": ("mass", 0.001),
    "kg": ("mass", 1.0),
    "t": ("mass", 1000.0),
    "oz": ("mass", 0.028349523125),
    "lb": ("mass", 0.45359237),
    "st": ("mass", 6.35029318),
    # data (decimal and binary)
    "b": ("data", 1.0),
    "kb": ("data", 1000.0),
    "mb": ("data", 1000.0 ** 2),
    "gb": ("data", 1000.0 ** 3),
    "tb": ("data", 1000.0 ** 4),
    "kib": ("data", 1024.0),
    "mib": ("data", 1024.0 ** 2),
    "gib": ("data", 1024.0 ** 3),
    "tib": ("data", 1024.0 ** 4),
    # time (base: second)
    "ms": ("time", 0.001),
    "s": ("time", 1.0),
    "min": ("time", 60.0),
    "h": ("time", 3600.0),
    "day": ("time", 86400.0),
    "week": ("time", 604800.0),
    # volume (base: litre)
    "ml": ("volume", 0.001),
    "l": ("volume", 1.0),
    "gal": ("volume", 3.785411784),
    "qt": ("volume", 0.946352946),
    "pt": ("volume", 0.473176473),
    "cup": ("volume", 0.2365882365),
    "floz": ("volume", 0.0295735295625),
    # area (base: square metre)
    "m2": ("area", 1.0),
    "km2": ("area", 1_000_000.0),
    "cm2": ("area", 0.0001),
    "ft2": ("area", 0.09290304),
    "in2": ("area", 0.00064516),
    "acre": ("area", 4046.8564224),
    "ha": ("area", 10000.0),
    # speed (base: metre/second)
    "m/s": ("speed", 1.0),
    "km/h": ("speed", 1.0 / 3.6),
    "mph": ("speed", 0.44704),
    "knot": ("speed", 0.514444444444),
}

_ALIASES = {
    "c": "c", "celsius": "c", "centigrade": "c",
    "f": "f", "fahrenheit": "f",
    "k": "k", "kelvin": "k",
    "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "centimeter": "cm", "centimeters": "cm", "centimetre": "cm",
    "millimeter": "mm", "millimeters": "mm",
    "kilometer": "km", "kilometers": "km", "kilometre": "km",
    "inch": "in", "inches": "in",
    "foot": "ft", "feet": "ft",
    "yard": "yd", "yards": "yd",
    "mile": "mi", "miles": "mi",
    "gram": "g", "grams": "g",
    "kilogram": "kg", "kilograms": "kg",
    "milligram": "mg", "milligrams": "mg",
    "pound": "lb", "pounds": "lb", "lbs": "lb",
    "ounce": "oz", "ounces": "oz",
    "byte": "b", "bytes": "b",
    "kilobyte": "kb", "kilobytes": "kb",
    "megabyte": "mb", "megabytes": "mb",
    "gigabyte": "gb", "gigabytes": "gb",
    "terabyte": "tb", "terabytes": "tb",
    "second": "s", "seconds": "s", "sec": "s",
    "minute": "min", "minutes": "min",
    "hour": "h", "hours": "h", "hr": "h",
    "days": "day", "weeks": "week",
    "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "milliliter": "ml", "milliliters": "ml",
    "gallon": "gal", "gallons": "gal",
    "quart": "qt", "quarts": "qt",
    "pint": "pt", "pints": "pt",
    "cups": "cup",
    "fluidounce": "floz", "fluidounces": "floz",
    "squaremeter": "m2", "squaremeters": "m2",
    "squarekilometer": "km2", "squarekilometers": "km2",
    "squarefoot": "ft2", "squarefeet": "ft2",
    "squareinch": "in2", "squareinches": "in2",
    "hectare": "ha", "hectares": "ha",
    "acres": "acre",
    "mps": "m/s",
    "kmh": "km/h", "kph": "km/h",
    "knots": "knot",
}

_TEMP_UNITS = {"c", "f", "k"}


PLUGIN = {
    "name": "calculator",
    "description": (
        "Does arithmetic, percentages, unit conversions and number-base "
        "conversions locally and exactly. Use for every sum, discount, tip, "
        "measurement conversion ('10 km in miles', '180 pounds in kg'), "
        "temperature conversion, percentage change, or base conversion "
        "('255 in hex'). Do not guess arithmetic yourself when this tool is "
        "available."
    ),
    "brief": (
        "Offline arithmetic, percentages, unit conversion and base conversion."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "evaluate | convert | percent | percent_change | base"
                ),
                "enum": [
                    "evaluate", "convert", "percent",
                    "percent_change", "base",
                ],
            },
            "expression": {
                "type": "STRING",
                "description": (
                    "For evaluate: a mathematical expression such as "
                    "'(1200 * 1.23) / 4' or 'sqrt(144) + 2^3'. Use a dot for "
                    "decimals; ^ is accepted as power."
                ),
            },
            "value": {
                "type": "STRING",
                "description": (
                    "For convert/percent/base: the value to use. A number, or "
                    "a number string for base conversion."
                ),
            },
            "from_unit": {
                "type": "STRING",
                "description": "For convert: current unit, e.g. km, kg, c, gb.",
            },
            "to_unit": {
                "type": "STRING",
                "description": "For convert: desired unit, e.g. mi, lb, f, kib.",
            },
            "percent": {
                "type": "STRING",
                "description": "For percent: the percentage, e.g. 15 for 15%.",
            },
            "old": {
                "type": "STRING",
                "description": "For percent_change: the original value.",
            },
            "new": {
                "type": "STRING",
                "description": "For percent_change: the new value.",
            },
            "from_base": {
                "type": "INTEGER",
                "description": "For base: source base, 2-36. Default 10.",
            },
            "to_base": {
                "type": "INTEGER",
                "description": "For base: target base, 2-36. Default 10.",
            },
        },
        "required": ["action"],
    },
    "tier": "core",
}


def _fail(reason: str, **facts) -> str:
    return outcome.failed("calculator", reason, **facts)


def _num(value, name: str) -> float:
    try:
        return float(str(value).replace(",", ".").strip())
    except Exception:
        raise ValueError(f"{name} must be a number")


def _fmt(value) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return str(value)
        if value == 0:
            return "0"
        return f"{value:.12g}"
    return str(value)


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("only numbers are allowed")
        return node.value

    if isinstance(node, ast.BinOp):
        fn = _BINOPS.get(type(node.op))
        if fn is None:
            raise ValueError("operator not allowed")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow):
            if abs(right) > 1000:
                raise ValueError("exponent is too large")
        result = fn(left, right)
        if isinstance(result, complex):
            raise ValueError("complex results are not supported")
        if abs(result) > _MAX_RESULT:
            raise ValueError("result is too large")
        return result

    if isinstance(node, ast.UnaryOp):
        fn = _UNARY.get(type(node.op))
        if fn is None:
            raise ValueError("operator not allowed")
        return fn(_eval_node(node.operand))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("only named functions are allowed")
        fn = _FUNCS.get(node.func.id)
        if fn is None:
            raise ValueError(f"function '{node.func.id}' is not allowed")
        if node.keywords:
            raise ValueError("keyword arguments are not allowed")
        args = [_eval_node(arg) for arg in node.args]
        if node.func.id == "round" and len(args) == 2:
            args[1] = int(args[1])
        return fn(*args)

    if isinstance(node, ast.Name):
        if node.id in _NAMES:
            return _NAMES[node.id]
        raise ValueError(f"unknown name '{node.id}'")

    raise ValueError("unsupported expression")


def _normalise_expr(expression: str) -> str:
    expr = str(expression or "").strip()
    expr = expr.replace("×", "*").replace("÷", "/").replace("−", "-")
    expr = expr.replace("^", "**")
    # A single comma with no function call is a decimal comma in pt-BR.
    if "(" not in expr and expr.count(",") == 1 and "." not in expr:
        expr = expr.replace(",", ".")
    return expr


def _unit(unit) -> str:
    text = str(unit or "").strip().lower()
    text = text.replace("°", "").replace("º", "").replace(" ", "")
    return _ALIASES.get(text, text)


def _to_celsius(value: float, unit: str) -> float:
    if unit == "c":
        return value
    if unit == "f":
        return (value - 32.0) * 5.0 / 9.0
    if unit == "k":
        return value - 273.15
    raise ValueError("unknown temperature unit")


def _from_celsius(value: float, unit: str) -> float:
    if unit == "c":
        return value
    if unit == "f":
        return value * 9.0 / 5.0 + 32.0
    if unit == "k":
        return value + 273.15
    raise ValueError("unknown temperature unit")


def _digit(n: int, base: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    out = []
    while n:
        out.append(digits[n % base])
        n //= base
    return sign + "".join(reversed(out))


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = str(parameters.get("action") or "").strip().lower()

    try:
        if action == "evaluate":
            expression = _normalise_expr(parameters.get("expression", ""))
            if not expression:
                return _fail("expression is required", requested_action=action)
            tree = ast.parse(expression, mode="eval")
            if sum(1 for _ in ast.walk(tree)) > _MAX_NODES:
                return _fail("expression is too complex", requested_action=action)
            result = _eval_node(tree)
            return outcome.done(
                "calculator", requested_action=action,
                expression=expression, result=_fmt(result),
            )

        if action == "convert":
            value = _num(parameters.get("value"), "value")
            from_unit = _unit(parameters.get("from_unit"))
            to_unit = _unit(parameters.get("to_unit"))
            if from_unit in _TEMP_UNITS or to_unit in _TEMP_UNITS:
                if from_unit not in _TEMP_UNITS or to_unit not in _TEMP_UNITS:
                    return _fail(
                        "temperature units cannot be converted to that unit",
                        **{"from": from_unit, "to": to_unit},
                    )
                result = _from_celsius(_to_celsius(value, from_unit), to_unit)
            else:
                if from_unit not in _UNITS or to_unit not in _UNITS:
                    return _fail(
                        f"unknown unit: {from_unit if from_unit not in _UNITS else to_unit}",
                        **{"from": from_unit, "to": to_unit},
                    )
                cat_from, factor_from = _UNITS[from_unit]
                cat_to, factor_to = _UNITS[to_unit]
                if cat_from != cat_to:
                    return _fail(
                        f"cannot convert {cat_from} to {cat_to}",
                        **{"from": from_unit, "to": to_unit},
                    )
                result = value * factor_from / factor_to
            return outcome.done(
                "calculator", requested_action=action,
                value=_fmt(value), **{"from": from_unit, "to": to_unit},
                result=_fmt(result),
            )

        if action == "percent":
            value = _num(parameters.get("value"), "value")
            pct = _num(parameters.get("percent"), "percent")
            result = value * pct / 100.0
            return outcome.done(
                "calculator", requested_action=action,
                value=_fmt(value), percent=_fmt(pct), result=_fmt(result),
            )

        if action == "percent_change":
            old = _num(parameters.get("old"), "old")
            new = _num(parameters.get("new"), "new")
            if old == 0:
                return _fail("old value cannot be zero", requested_action=action)
            change = (new - old) / abs(old) * 100.0
            direction = "increase" if change > 0 else "decrease" if change < 0 else "unchanged"
            return outcome.done(
                "calculator", requested_action=action,
                old=_fmt(old), new=_fmt(new),
                change_percent=_fmt(change), direction=direction,
            )

        if action == "base":
            raw = str(parameters.get("value") or "").strip()
            if not raw:
                return _fail("value is required", requested_action=action)
            try:
                from_base = int(parameters.get("from_base") or 10)
                to_base = int(parameters.get("to_base") or 10)
            except Exception:
                return _fail("bases must be integers", requested_action=action)
            if not (2 <= from_base <= 36 and 2 <= to_base <= 36):
                return _fail("bases must be between 2 and 36", requested_action=action)
            try:
                number = int(raw, from_base)
            except Exception:
                return _fail(
                    f"'{raw}' is not a valid base-{from_base} number",
                    requested_action=action,
                )
            return outcome.done(
                "calculator", requested_action=action,
                value=raw, from_base=from_base, to_base=to_base,
                result=_digit(number, to_base),
            )

        return _fail(f"unknown action '{action}'", requested_action=action)

    except Exception as e:
        return _fail(str(e), requested_action=action)
