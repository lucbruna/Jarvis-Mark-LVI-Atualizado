import subprocess
PLUGIN = {"name": "azure_cli", "description": "Run an Azure CLI command (requires az configured).", "parameters": {"type": "OBJECT", "properties": {"command": {"type": "STRING"}}, "required": ["command"]}}
def run(parameters, player=None, session_memory=None):
    cmd = (parameters.get("command") or "").strip()
    if not cmd:
        return "No command provided."
    try:
        r = subprocess.run("az " + cmd, shell=True, capture_output=True, text=True, timeout=120)
        out = (r.stdout or r.stderr or "").strip()[:2000]
        if player:
            try: player.write_log(f"JARVIS: az {cmd}")
            except Exception: pass
        return out or f"az exited {r.returncode}."
    except Exception as e:
        return f"Sir, azure_cli failed: {e}"