"""
Obsidian note creator.
"""
from pathlib import Path

PLUGIN = {
    "name": "obsidian_note",
    "description": (
        "Create a Markdown note in an Obsidian vault. Use for saving notes, "
        "ideas, meeting minutes and quick captures."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "Note title (used as filename)"},
            "content": {"type": "STRING", "description": "Markdown body"},
            "vault_path": {"type": "STRING", "description": "Optional vault path override"},
            "folder": {"type": "STRING", "description": "Subfolder inside the vault"},
        },
        "required": ["title"],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    title = (parameters.get("title") or "").strip()
    if not title:
        return "No title provided."
    content = parameters.get("content") or ""
    vault = (parameters.get("vault_path") or "").strip()
    if not vault:
        try:
            from memory.config_manager import get_plugin_config
            vault = (get_plugin_config("obsidian_note").get("vault_path") or "").strip()
        except Exception:
            vault = ""
    if not vault:
        return ("Obsidian vault path not configured. Set obsidian_note.vault_path "
                "in plugin settings.")
    folder = (parameters.get("folder") or "").strip()
    try:
        base = Path(vault).expanduser()
        target_dir = base / folder if folder else base
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_title = "".join(c for c in title if c not in '\\/:*?"<>|').strip() or "note"
        path = target_dir / f"{safe_title}.md"
        path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
        if player:
            try:
                player.write_log(f"JARVIS: Obsidian note created: {path}")
            except Exception:
                pass
        return f"Obsidian note created: {path.name}."
    except Exception as e:
        return f"Sir, obsidian_note failed: {e}"
