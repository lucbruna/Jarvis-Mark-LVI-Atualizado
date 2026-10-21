"""JARVIS plugin - OBS Studio control via obs-websocket."""
from __future__ import annotations

import json
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "obs_control",
    "description": "Control OBS Studio: start/stop recording, start/stop streaming, switch scenes, toggle sources.",
    "brief": "OBS Studio: record/stream/scenes.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "start_recording|stop_recording|start_streaming|stop_streaming|set_scene|toggle_source"},
            "scene": {"type": "STRING", "description": "Scene name (set_scene)."},
            "source": {"type": "STRING", "description": "Source name (toggle_source)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _client():
    try:
        import obsws_python as obs
    except ImportError:
        return None, "obsws-python not installed. Run: pip install obsws-python"
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        host = cfg.get("obs_host", "localhost")
        port = int(cfg.get("obs_port", 4455))
        password = cfg.get("obs_password", "")
        cl = obs.ReqClient(host=host, port=port, password=password)
        return cl, None
    except Exception as e:
        return None, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    cl, err = _client()
    if err:
        return outcome.failed("obs_control", err)
    try:
        if action == "start_recording":
            cl.start_record()
            return outcome.done("obs_control", note="recording started")
        if action == "stop_recording":
            cl.stop_record()
            return outcome.done("obs_control", note="recording stopped")
        if action == "start_streaming":
            cl.start_stream()
            return outcome.done("obs_control", note="streaming started")
        if action == "stop_streaming":
            cl.stop_stream()
            return outcome.done("obs_control", note="streaming stopped")
        if action == "set_scene":
            cl.set_current_program_scene(params.get("scene", ""))
            return outcome.done("obs_control", note=f"scene: {params.get('scene')}")
        if action == "toggle_source":
            cl.set_source_enabled(params.get("source", ""), True)
            return outcome.done("obs_control", note=f"toggled {params.get('source')}")
        return outcome.failed("obs_control", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("obs_control", str(e))
