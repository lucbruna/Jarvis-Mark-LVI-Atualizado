import subprocess, sys
PLUGIN = {"name": "apple_notes", "description": "Create a note in Apple Notes (macOS only).", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "body": {"type": "STRING"}}, "required": ["title"]}}
def run(parameters, player=None, session_memory=None):
    if sys.platform != "darwin":
        return "Apple Notes is only available on macOS."
    title = (parameters.get("title") or "").strip()
    body = parameters.get("body") or ""
    script = 'tell application "Notes" to tell account "iCloud" to make new note with properties {name:"%s", body:"%s"}' % (title, body)
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
        if player:
            try: player.write_log(f"JARVIS: Apple Note created: {title}")
            except Exception: pass
        return f"Apple Note created: {title}."
    except Exception as e:
        return f"Sir, apple_notes failed: {e}"