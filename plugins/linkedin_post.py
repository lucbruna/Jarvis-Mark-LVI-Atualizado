"""
LinkedIn post plugin: opens the LinkedIn share dialog with prefilled text.
"""
import urllib.parse
import webbrowser

PLUGIN = {
    "name": "linkedin_post",
    "description": "Open LinkedIn's share dialog with prefilled text (posts require manual confirmation in browser).",
    "parameters": {
        "type": "OBJECT",
        "properties": {"text": {"type": "STRING", "description": "Text to share"}},
        "required": ["text"],
    },
}


def run(parameters, player=None, session_memory=None) -> str:
    text = (parameters.get("text") or "").strip()
    if not text:
        return "No text provided."
    url = "https://www.linkedin.com/sharing/share-offsite/?url=" + urllib.parse.quote(text)
    try:
        webbrowser.open(url)
        if player:
            try:
                player.write_log("JARVIS: LinkedIn share dialog opened.")
            except Exception:
                pass
        return "LinkedIn share dialog opened in your browser."
    except Exception as e:
        return f"Sir, linkedin_post failed: {e}"
