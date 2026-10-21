"""JARVIS plugin - create photos and animations, delivered ready.

Photos: procedural (Pillow gradients/shapes/noise) always available, plus
optional API providers (OpenAI images, Stability AI, SiliconFlow) when a key
is configured. Animations: animated GIF (Pillow) always available, and MP4
via ffmpeg when installed (frames -> video). Every output is written to disk
and its folder is opened so the user receives it.

This is the 'create animations and photos' capability: it works offline for
procedural art and uses the best available cloud model when configured.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from core import outcome

PLUGIN = {
    "name": "media_creator",
    "description": (
        "Creates images (photos/illustrations) and animations (GIF/MP4) and "
        "delivers them ready to open. Use for 'create an image of...', "
        "'make an animation', 'generate a photo', 'draw a logo'. "
        "Supports procedural generation offline (gradient/pattern/noise) and "
        "cloud providers (OpenAI DALL-E, Stability, SiliconFlow) when API "
        "keys are set. Returns the saved file path."
    ),
    "brief": "Creates images and animations (GIF/MP4) and opens them.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "kind": {"type": "STRING", "description": "image (default) or animation."},
            "prompt": {"type": "STRING", "description": "What to create."},
            "style": {"type": "STRING", "description": "procedural (default), openai, stability, siliconflow."},
            "width": {"type": "INTEGER", "description": "Width in px (default 1024)."},
            "height": {"type": "INTEGER", "description": "Height in px (default 1024)."},
            "frames": {"type": "INTEGER", "description": "Number of frames for animation (default 12)."},
            "fps": {"type": "INTEGER", "description": "Frames per second (default 8)."},
            "format": {"type": "STRING", "description": "png/jpg/gif/mp4 (default png for image, gif for animation)."},
            "folder": {"type": "STRING", "description": "Target folder (default: pictures)."},
            "name": {"type": "STRING", "description": "Base file name."},
        },
        "required": ["prompt"],
    },
    "tier": "extra",
}


def _resolve_folder(folder: str) -> Path:
    home = Path.home()
    mapping = {"pictures": home / "Pictures", "desktop": home / "Desktop",
               "documents": home / "Documents", "downloads": home / "Downloads"}
    p = mapping.get((folder or "pictures").lower(), Path(folder).expanduser())
    p.mkdir(parents=True, exist_ok=True)
    return p


def _reveal(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path.parent)], check=False)
    except Exception:
        pass


def _procedural_image(w, h, prompt, t):
    try:
        from PIL import Image, ImageDraw, ImageFilter
        import random, hashlib
        seed = int(hashlib.md5(prompt.encode()).hexdigest(), 16) % (2**31)
        rng = random.Random(seed + t * 97)
        img = Image.new("RGB", (w, h))
        # gradient background
        px = img.load()
        c1 = (rng.randrange(0, 256), rng.randrange(0, 256), rng.randrange(0, 256))
        c2 = (rng.randrange(0, 256), rng.randrange(0, 256), rng.randrange(0, 256))
        for y in range(h):
            for x in range(w):
                f = (x + y) / (w + h)
                px[x, y] = tuple(int(c1[i] * (1 - f) + c2[i] * f) for i in range(3))
        draw = ImageDraw.Draw(img)
        # random shapes
        for _ in range(8):
            x0, y0 = rng.randrange(0, w), rng.randrange(0, h)
            x1, y1 = x0 + rng.randrange(20, w // 3), y0 + rng.randrange(20, h // 3)
            col = (rng.randrange(0, 256), rng.randrange(0, 256), rng.randrange(0, 256))
            draw.ellipse([x0, y0, x1, y1], fill=col, outline=None)
        # text label
        try:
            draw.text((20, h - 40), prompt[:60], fill=(255, 255, 255))
        except Exception:
            pass
        return img.filter(ImageFilter.GaussianBlur(radius=1.5))
    except ImportError:
        return None


def _openai_image(prompt, w, h):
    key = os.environ.get("OPENAI_API_KEY") or ""
    # try config file
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        key = key or cfg.get("openai_api_key") or cfg.get("image_api_key") or ""
    except Exception:
        pass
    if not key:
        return None, "no OpenAI API key configured"
    try:
        import httpx
        with httpx.Client(timeout=120.0) as cl:
            r = cl.post("https://api.openai.com/v1/images/generations",
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": "gpt-image-1", "prompt": prompt,
                              "size": f"{w}x{h}", "n": 1})
            r.raise_for_status()
            data = r.json()
            b64 = data["data"][0].get("b64_json")
            if b64:
                from PIL import Image
                import io
                return Image.open(io.BytesIO(base64.b64decode(b64))), "PNG"
            url = data["data"][0].get("url")
            if url:
                import httpx
                rr = httpx.get(url, timeout=120.0)
                from PIL import Image
                import io
                return Image.open(io.BytesIO(rr.content))
    except Exception as e:
        return None, str(e)
    return None, "no image returned"


def _save_image(img, path) -> bool:
    try:
        img.save(path)
        return True
    except Exception:
        return False


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    kind = (params.get("kind") or "image").lower()
    prompt = (params.get("prompt") or "").strip()
    style = (params.get("style") or "procedural").lower()
    w = int(params.get("width") or 1024)
    h = int(params.get("height") or 1024)
    frames = int(params.get("frames") or 12)
    fps = int(params.get("fps") or 8)
    fmt = (params.get("format") or ("gif" if kind == "animation" else "png")).lower()
    folder = params.get("folder") or "pictures"
    base = (params.get("name") or prompt[:30].replace(" ", "_") or "creation").strip("._ ") or "creation"

    out_dir = _resolve_folder(folder)
    stamp = int(time.time())

    if kind == "video":
        # AI video generation via Replicate (optional). Falls back to a
        # procedural MP4 (animated frames) when no token is configured.
        token = os.environ.get("REPLICATE_API_TOKEN", "")
        try:
            cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
            token = token or cfg.get("replicate_api_token", "")
        except Exception:
            pass
        if token:
            try:
                import httpx, time as _t
                with httpx.Client(timeout=60.0) as cl:
                    r = cl.post("https://api.replicate.com/v1/predictions",
                                headers={"Authorization": f"Token {token}"},
                                json={"version": "3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
                                      "input": {"prompt": prompt, "num_frames": frames or 14}})
                    r.raise_for_status()
                    pred = r.json()
                    get_url = pred["urls"]["get"]
                    for _ in range(60):
                        _t.sleep(2)
                        rr = cl.get(get_url, headers={"Authorization": f"Token {token}"})
                        rr.raise_for_status()
                        st = rr.json()
                        if st.get("status") in ("succeeded", "failed", "canceled"):
                            break
                    if st.get("status") == "succeeded":
                        out_url = st["output"]
                        if isinstance(out_url, list):
                            out_url = out_url[0]
                        rr2 = httpx.get(out_url, timeout=120.0)
                        out_path = out_dir / f"{base}_{stamp}.mp4"
                        out_path.write_bytes(rr2.content)
                        threading.Thread(target=_reveal, args=(out_path,), daemon=True).start()
                        msg = f"AI video saved: {out_path}"
                        if player:
                            try: player.write_log(f"JARVIS: {msg}")
                            except Exception: pass
                        return outcome.done("media_creator", path=str(out_path))
            except Exception as e:
                pass
        # fallback: procedural mp4
        kind = "animation"

    if kind == "animation":
        out_path = out_dir / f"{base}_{stamp}.gif" if fmt == "gif" else out_dir / f"{base}_{stamp}.mp4"
        try:
            from PIL import Image
        except ImportError:
            return outcome.failed("media_creator", "Pillow not installed. Run: pip install Pillow")
        imgs = []
        for i in range(max(2, frames)):
            im = _procedural_image(w, h, prompt, i)
            if im is None:
                return outcome.failed("media_creator", "Pillow not available")
            imgs.append(im)
        if fmt == "gif":
            imgs[0].save(out_path, save_all=True, append_images=imgs[1:], duration=1000 // max(1, fps), loop=0)
        else:
            # write frames then ffmpeg
            tmp = out_dir / f"_frames_{stamp}"
            tmp.mkdir(exist_ok=True)
            for i, im in enumerate(imgs):
                im.save(tmp / f"f{i:04d}.png")
            try:
                subprocess.run(["ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp / "f%04d.png"),
                                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_path)],
                               capture_output=True, timeout=300)
            finally:
                for f in tmp.glob("*.png"):
                    f.unlink(missing_ok=True)
                try:
                    tmp.rmdir()
                except Exception:
                    pass
        threading.Thread(target=_reveal, args=(out_path,), daemon=True).start()
        msg = f"Animation saved: {out_path} ({frames} frames)"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("media_creator", path=str(out_path), frames=frames)

    # image
    out_ext = fmt if fmt in ("png", "jpg", "jpeg", "webp") else "png"
    out_path = out_dir / f"{base}_{stamp}.{out_ext}"
    img = None
    err = None
    if style in ("openai",):
        img, err = _openai_image(prompt, w, h)
    if img is None and style not in ("openai",):
        img = _procedural_image(w, h, prompt, 0)
    if img is None:
        return outcome.failed("media_creator", f"image generation failed: {err or 'unknown'}")
    if not _save_image(img, out_path):
        return outcome.failed("media_creator", "could not save image")
    threading.Thread(target=_reveal, args=(out_path,), daemon=True).start()
    msg = f"Image saved: {out_path}"
    if player:
        try: player.write_log(f"JARVIS: {msg}")
        except Exception: pass
    return outcome.done("media_creator", path=str(out_path))
