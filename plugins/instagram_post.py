"""
Instagram helper: opens Instagram (posting requires the mobile app/API; this opens the site).
"""
import webbrowser

PLUGIN = {
    "name": "instagram_post",
    "description": "Open Instagram in the browser. Direct posting is not supported by the public API; use for quick access.",
    "parameters": {
        "type": "OBJECT",
        "properties": {"url": {"type": "STRING", "description": "Optional Instagram URL to open"}},
        "required": [],
    },
}


def run(parameters, player=None, session_memory=None) -> str:
    url = (parameters.get("url") or "").strip() or "https://www.instagram.com/"
    try:
        webbrowser.open(url)
        if player:
            try:
                player.write_log("JARVIS: Instagram opened.")
            except Exception:
                pass
        return "Instagram opened in your browser."
    except Exception as e:
        return f"Sir, instagram_post failed: {e}"
