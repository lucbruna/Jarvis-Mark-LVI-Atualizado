"""JARVIS plugin - recipe suggestions based on ingredients."""
from __future__ import annotations

from core import gemini, outcome


PLUGIN = {
    "name": "recipes",
    "description": "Suggest recipes based on available ingredients. Uses Gemini to generate recipe ideas.",
    "brief": "Recipe suggestions from ingredients.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "ingredients": {"type": "STRING", "description": "Comma-separated ingredients."},
            "diet": {"type": "STRING", "description": "Dietary preference (vegetarian, vegan, etc.)."},
            "count": {"type": "INTEGER", "description": "Number of recipes (default 3)."},
        },
        "required": ["ingredients"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    ingredients = params.get("ingredients", "")
    diet = params.get("diet", "")
    count = int(params.get("count", 3))
    prompt = f"Suggest {count} recipes using these ingredients: {ingredients}."
    if diet:
        prompt += f" Dietary preference: {diet}."
    prompt += " For each recipe: name, ingredients, steps, estimated time."
    try:
        resp = gemini.call(prompt, tier=gemini.SMART, timeout_ms=30000)
        text = getattr(resp, "text", "No response") if resp else "No response"
    except Exception as e:
        text = f"Failed: {e}"
    if player:
        try: player.write_log(f"JARVIS: {text[:300]}")
        except Exception: pass
    return outcome.done("recipes", note=text[:500], text=text)
