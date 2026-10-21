"""
Twitch helper: opens a Twitch channel or clip URL.
"""
import webbrowser

PLUGIN = {
    "name": "twitch_open",
    "description": "Open a Twitch channel or clip in the browser.",
    "parameters": {
        "type": "OBJECT",
        "properties": {"target": {"type": "STRING", "description": "Channel name or full URL"}},
        "required": ["target"],
    },
}


def run(parameters, player=None, session_memory=None) -> str:
    target = (parameters.get("target") or "").strip()
    if not target:
        return "No target provided."
    url = target if target.startswith("http") else f"https://www.twitch.tv/{target}"
    try:
        webbrowser.open(url)
        if player:
            try:
                player.write_log(f"JARVIS: Twitch opened: {url}")
            except Exception:
                pass
        return f"Twitch opened: {url}"
    except Exception as e:
        return f"Sir, twitch_open failed: {e}"
