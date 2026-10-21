"""JARVIS plugin - Spotify control via spotipy."""
from __future__ import annotations

import json
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "spotify_control",
    "description": "Control Spotify: play, pause, next, previous, search, volume.",
    "brief": "Spotify: play/pause/next/prev/search/volume.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "play|pause|next|previous|search|volume|current"},
            "query": {"type": "STRING", "description": "Search query (search/play)."},
            "volume": {"type": "INTEGER", "description": "Volume 0-100 (volume)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _sp():
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        return None, "spotipy not installed. Run: pip install spotipy"
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=cfg.get("spotify_client_id", ""),
            client_secret=cfg.get("spotify_client_secret", ""),
            redirect_uri=cfg.get("spotify_redirect_uri", "http://localhost:8888/callback"),
            scope="user-modify-playback-state user-read-playback-state",
        ))
        return sp, None
    except Exception as e:
        return None, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    sp, err = _sp()
    if err:
        return outcome.failed("spotify_control", err)
    try:
        if action == "play":
            q = params.get("query", "")
            if q:
                res = sp.search(q, limit=1, type="track")
                if res["tracks"]["items"]:
                    uri = res["tracks"]["items"][0]["uri"]
                    sp.start_playback(uris=[uri])
                    return outcome.done("spotify_control", note=f"playing: {res['tracks']['items'][0]['name']}")
            sp.start_playback()
            return outcome.done("spotify_control", note="resumed")
        if action == "pause":
            sp.pause_playback()
            return outcome.done("spotify_control", note="paused")
        if action == "next":
            sp.next_track()
            return outcome.done("spotify_control", note="next track")
        if action == "previous":
            sp.previous_track()
            return outcome.done("spotify_control", note="previous track")
        if action == "volume":
            vol = int(params.get("volume", 50))
            sp.volume(vol)
            return outcome.done("spotify_control", note=f"volume {vol}")
        if action == "current":
            cur = sp.current_playback()
            if cur and cur.get("item"):
                return outcome.done("spotify_control", note=f"{cur['item']['name']} — {cur['item']['artists'][0]['name']}")
            return outcome.done("spotify_control", note="nothing playing")
        if action == "search":
            q = params.get("query", "")
            res = sp.search(q, limit=5, type="track")
            lines = [f"- {t['name']} — {t['artists'][0]['name']}" for t in res["tracks"]["items"]]
            return outcome.done("spotify_control", note="\n".join(lines))
        return outcome.failed("spotify_control", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("spotify_control", str(e))
