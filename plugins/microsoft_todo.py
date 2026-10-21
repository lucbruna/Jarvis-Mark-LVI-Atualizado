import webbrowser
PLUGIN = {"name": "microsoft_todo", "description": "Open Microsoft To Do in the browser.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}}, "required": []}}
def run(parameters, player=None, session_memory=None):
    try:
        webbrowser.open("https://to-do.office.com/tasks/")
        if player:
            try: player.write_log("JARVIS: Microsoft To Do opened.")
            except Exception: pass
        return "Microsoft To Do opened in your browser."
    except Exception as e:
        return f"Sir, microsoft_todo failed: {e}"