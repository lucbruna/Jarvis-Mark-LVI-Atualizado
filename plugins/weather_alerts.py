"""JARVIS plugin - weather alerts for severe conditions."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "weather_alerts",
    "description": "Fetch weather alerts/warnings for a location via OpenWeatherMap or NWS (US).",
    "brief": "Weather alerts for severe conditions.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "location": {"type": "STRING", "description": "City or lat,lon."},
            "provider": {"type": "STRING", "description": "openweather (default) or nws (US only)."},
        },
        "required": ["location"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    location = params.get("location", "")
    provider = (params.get("provider") or "openweather").lower()
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        key = cfg.get("openweather_api_key", "")
    except Exception:
        key = ""
    if provider == "nws":
        # NWS alerts by point (requires lat,lon)
        try:
            url = f"https://api.weather.gov/alerts/active?point={location}"
            req = urllib.request.Request(url, headers={"User-Agent": "JARVIS"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            alerts = data.get("features", [])
            if not alerts:
                return outcome.done("weather_alerts", note="No active alerts")
            lines = [f"- {a['properties'].get('event')}: {a['properties'].get('headline')}" for a in alerts[:10]]
            return outcome.done("weather_alerts", note="\n".join(lines), count=len(alerts))
        except Exception as e:
            return outcome.failed("weather_alerts", str(e))
    # OpenWeatherMap
    if not key:
        return outcome.failed("weather_alerts", "OpenWeatherMap API key not configured")
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={key}&units=metric"
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
        weather = data.get("weather", [{}])[0].get("description", "")
        temp = data.get("main", {}).get("temp", "?")
        msg = f"{location}: {weather}, {temp}°C"
        # Simple alert logic
        alerts = []
        if "storm" in weather or "thunder" in weather:
            alerts.append("Thunderstorm warning")
        if temp is not None and (temp > 35 or temp < -10):
            alerts.append(f"Extreme temperature: {temp}°C")
        note = msg + ("\nAlerts: " + ", ".join(alerts) if alerts else "\nNo severe alerts")
        return outcome.done("weather_alerts", note=note, alerts=alerts)
    except Exception as e:
        return outcome.failed("weather_alerts", str(e))
