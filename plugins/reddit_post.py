"""
Reddit post plugin (script app). Creates a text post via Reddit API (password grant).
"""
import json
import urllib.parse
import urllib.request

PLUGIN = {
    "name": "reddit_post",
    "description": "Create a text post on Reddit using a script app. Use for posting updates or content to a subreddit.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "subreddit": {"type": "STRING", "description": "Subreddit name without r/"},
            "title": {"type": "STRING", "description": "Post title"},
            "text": {"type": "STRING", "description": "Post body (selftext)"},
            "client_id": {"type": "STRING", "description": "Optional Reddit client id"},
            "client_secret": {"type": "STRING", "description": "Optional Reddit client secret"},
            "username": {"type": "STRING", "description": "Optional Reddit username"},
            "password": {"type": "STRING", "description": "Optional Reddit password"},
        },
        "required": ["subreddit", "title"],
    },
}


def _cfg(key, parameters, namespace):
    v = (parameters.get(key) or "").strip()
    if v:
        return v
    try:
        from memory.config_manager import get_plugin_config
        return (get_plugin_config(namespace).get(key) or "").strip()
    except Exception:
        return ""


def run(parameters, player=None, session_memory=None) -> str:
    subreddit = (parameters.get("subreddit") or "").strip().lstrip("r/")
    title = (parameters.get("title") or "").strip()
    if not subreddit or not title:
        return "subreddit and title are required."
    text = parameters.get("text") or ""
    cid = _cfg("client_id", parameters, "reddit_post")
    csecret = _cfg("client_secret", parameters, "reddit_post")
    user = _cfg("username", parameters, "reddit_post")
    passwd = _cfg("password", parameters, "reddit_post")
    if not all([cid, csecret, user, passwd]):
        return "Reddit credentials not configured (reddit_post.*)."
    try:
        # password grant
        auth = (cid + ":" + csecret).encode()
        import base64
        auth_b64 = base64.b64encode(auth).decode()
        data = urllib.parse.urlencode({
            "grant_type": "password",
            "username": user,
            "password": passwd,
        }).encode()
        req = urllib.request.Request(
            "https://www.reddit.com/api/v1/access_token",
            data=data,
            headers={"Authorization": f"Basic {auth_b64}",
                     "User-Agent": "MarkLVI/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            token = json.loads(resp.read().decode())["access_token"]
        # submit
        form = urllib.parse.urlencode({
            "sr": subreddit,
            "kind": "self",
            "title": title,
            "text": text,
            "api_type": "json",
        }).encode()
        req2 = urllib.request.Request(
            "https://oauth.reddit.com/api/submit",
            data=form,
            headers={"Authorization": f"Bearer {token}",
                     "User-Agent": "MarkLVI/1.0"},
        )
        with urllib.request.urlopen(req2, timeout=20) as resp:
            out = json.loads(resp.read().decode())
        if player:
            try:
                player.write_log(f"JARVIS: Reddit post created in r/{subreddit}.")
            except Exception:
                pass
        return f"Reddit post created in r/{subreddit}."
    except Exception as e:
        return f"Sir, reddit_post failed: {e}"
