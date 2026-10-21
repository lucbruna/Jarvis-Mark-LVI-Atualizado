import webbrowser
PLUGIN = {"name": "onenote_note", "description": "Open OneNote in the browser.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}}, "required": []}}
def run(parameters, player=None, session_memory=None):
    try:
        webbrowser.open("https://www.onenote.com/notebooks")
        if player:
            try: player.write_log("JARVIS: OneNote opened.")
            except Exception: pass
        return "OneNote opened in your browser."
    except Exception as e:
        return f"Sir, onenote_note failed: {e}"