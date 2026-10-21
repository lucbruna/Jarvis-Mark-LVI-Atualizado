import subprocess
PLUGIN = {"name": "aws_cli", "description": "Run an AWS CLI command (requires aws configured).", "parameters": {"type": "OBJECT", "properties": {"command": {"type": "STRING"}}, "required": ["command"]}}
def run(parameters, player=None, session_memory=None):
    cmd = (parameters.get("command") or "").strip()
    if not cmd:
        return "No command provided."
    try:
        r = subprocess.run("aws " + cmd, shell=True, capture_output=True, text=True, timeout=120)
        out = (r.stdout or r.stderr or "").strip()[:2000]
        if player:
            try: player.write_log(f"JARVIS: aws {cmd}")
            except Exception: pass
        return out or f"aws exited {r.returncode}."
    except Exception as e:
        return f"Sir, aws_cli failed: {e}"