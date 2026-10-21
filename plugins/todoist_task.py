"""
Todoist task creator.
"""
import json
import urllib.request

PLUGIN = {
    "name": "todoist_task",
    "description": (
        "Add a task to Todoist. Use for to-dos, reminders and task capture."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "content": {"type": "STRING", "description": "Task text"},
            "due_string": {"type": "STRING", "description": "Natural language due date, e.g. 'tomorrow 5pm'"},
            "priority": {"type": "INTEGER", "description": "Priority 1-4 (4 highest)"},
            "api_token": {"type": "STRING", "description": "Optional Todoist API token override"},
        },
        "required": ["content"],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    content = (parameters.get("content") or "").strip()
    if not content:
        return "No task content provided."
    token = (parameters.get("api_token") or "").strip()
    if not token:
        try:
            from memory.config_manager import get_plugin_config
            token = (get_plugin_config("todoist_task").get("api_token") or "").strip()
        except Exception:
            token = ""
    if not token:
        return ("Todoist API token not configured. Set todoist_task.api_token "
                "in plugin settings.")
    payload = {"content": content}
    if parameters.get("due_string"):
        payload["due_string"] = parameters.get("due_string")
    if parameters.get("priority") is not None:
        try:
            payload["priority"] = int(str(parameters.get("priority")))
        except (TypeError, ValueError):
            pass
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.todoist.com/rest/v2/tasks",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        tid = result.get("id")
        if player:
            try:
                player.write_log(f"JARVIS: Todoist task created: {content}")
            except Exception:
                pass
        return f"Todoist task created (id {tid})."
    except Exception as e:
        return f"Sir, todoist_task failed: {e}"
