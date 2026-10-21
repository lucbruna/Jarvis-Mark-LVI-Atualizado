"""
The Earth, in real time, on the assistant's own display.

WHAT IT SHOWS
    Himawari-9 — the Japanese geostationary satellite at 140.7°E — rendered as
    a turning globe in the middle of the HUD, where the avatar normally is. The
    image it spins is the satellite's own full-disc photograph, renewed every
    ten minutes; the caption under the globe says the capture time in UTC so it
    is never mistaken for a picture of right now when the feed is late.

WHY THIS IS NOT A VIDEO PLAYER
    It looks like one — it takes the centre of the screen and gives it back —
    but there is no stream to play. No public RTSP/HLS feed of the whole Earth
    exists, and the ones that look like one are a camera on the ISS pointed at
    whatever it happens to be over. A photograph every ten minutes, deprojected
    onto a sphere, is a real globe that can turn and that never has a "no signal"
    card from somebody else's encoder.

WHAT IT COSTS
    One GET to a public NICT endpoint every ten minutes, no key, no account,
    nothing sent. Rendering is numpy on the Qt thread at fifteen frames a second
    while the view is open and zero when it is closed.
"""
from __future__ import annotations


def earth_globe(parameters: dict = None, player=None,
                response=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "open").strip().lower()

    if player is None:
        return "There is no display to show the Earth on."

    if action in ("close", "hide", "stop"):
        if hasattr(player, "globe_is_showing") and not player.globe_is_showing():
            return "The Earth view was not open."
        player.hide_globe()
        return "Closed the Earth view."

    if action in ("refresh", "update", "sync"):
        player.refresh_globe()
        return "Asking Himawari-9 for the newest image."

    if action in ("status", "check"):
        try:
            from core import globe
            stamp, _ = globe.latest_stamp(timeout=10)
            return f"The satellite image is from {stamp} UTC."
        except Exception as e:                          # noqa: BLE001
            return f"The satellite feed could not be reached: {e}"

    player.show_globe(str(params.get("source") or "himawari9"))
    # A status line rather than a finished sentence: the model writes the words,
    # in the user's own language — the same contract video_player uses.
    return "status=opening source=himawari9"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "earth_globe",
    "description": (
        "Shows the EARTH in real time on the assistant's own display, where the "
        "avatar normally is: a turning globe made from the live Himawari-9 "
        "satellite image, refreshed every ten minutes. Use it when the user "
        "wants to SEE the planet, the globe, the Earth from space, 'show me the "
        "Earth', 'open the globe', 'mostre o globo terrestre', 'abrir a Terra em "
        "tempo real', 'como está o planeta agora', 'close the globe'. No API "
        "key, no account and no stream URL is needed. Actions: 'open' (default), "
        "'close', 'refresh' to pull a newer image, 'status' to report the "
        "capture time. Do NOT use video_player for this: that one plays a video "
        "and has no globe in it."
    ),
    "brief": ("Shows a real-time globe of Earth from the Himawari-9 satellite "
              "on the HUD."),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": ("'open' (default), 'close', 'refresh' for a "
                                "newer satellite image, or 'status' for the "
                                "capture time."),
                "enum": ["open", "close", "refresh", "status"],
            },
            "source": {
                "type": "STRING",
                "description": ("Optional label for what the user asked for, in "
                                "their own words. The imagery is always "
                                "Himawari-9."),
            },
        },
        "required": ["action"],
    },
    "tier": "extra",
    "handler": earth_globe,
}
