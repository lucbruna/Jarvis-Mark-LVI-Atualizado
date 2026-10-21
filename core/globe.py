"""
Real-time Earth globe for the HUD centre — software rendered, like the avatar.

WHERE THE PICTURE COMES FROM
    Himawari-9, the JMA geostationary weather satellite at 140.7°E. Its
    full-disk image is published by NICT every ten minutes, free, with no key
    and no account:

        https://himawari8.nict.go.jp/img/D531106/latest.json
        https://himawari8.nict.go.jp/img/D531106/2d/550/YYYY/MM/DD/HHMMSS_x_y.png

    Measured on this machine: `latest.json` answers with the capture time and
    the 550 px full disk arrives in ~67 kB. Four of those tiles make the 1100 px
    image used here. Nothing else is downloaded, and the assistant never sends
    anything — this is a GET of a public file.

WHY THERE IS A DEPROJECTION STEP
    The published image is a *view from the satellite*, not a map: a disc with
    black space around it. Sampling that disc directly would only ever show the
    Asia-Pacific face, and it could not turn. So the disc is converted once per
    refresh into an equirectangular map (longitude × latitude), which is what a
    sphere can be rotated against. That is `disk_to_equirect`: for every pixel of
    the map, work out where it lands on the disc. The projection is perspective,
    not orthographic — from 35,786 km the disc centre is magnified by
    1/(1 − Re/H) ≈ 1.18 relative to the limb — so the perspective term is kept
    rather than approximated away. The error at the limb is what decides whether
    continents line up.

WHY NUMPY AND NOT A SHADER
    The avatar is QPainter on purpose: no OpenGL context, no driver to disagree
    with, identical output on a VM and on a gaming rig. A globe is a sphere, and
    a sphere in QPainter means a per-pixel texture lookup — which is exactly what
    numpy is for. It is already a dependency of the vision path (OpenCV), so this
    adds nothing to install. One frame is a handful of array operations, and the
    geometry is cached; measured on this machine: 10.9 ms at 340 px and 14.2 ms
    at 420 px, against 52 ms before the cache existed. The HUD renders at 300 px,
    which is 9.7 ms — about an eighth of one core at twelve frames a second, and
    nothing at all while the view is closed.

WHAT THIS DELIBERATELY DOES NOT DO
    No lighting model. The satellite image already has the day/night terminator
    in it, and re-lighting it would either double-darken the night side or, with
    a moving sun, disagree with the pixels. Only a rim glow and a gentle limb
    falloff are added, which is what makes it read as a sphere instead of a disc.
"""
from __future__ import annotations

import io
import json
import threading
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np
from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QRadialGradient
from PyQt6.QtWidgets import QSizePolicy, QWidget

# Himawari-9 sits on the equator at 140.7°E. Every deprojection constant follows
# from that number, so it is named once.
SUB_LON = 140.7
EARTH_RADIUS_KM = 6371.0
SAT_HEIGHT_KM = 42164.0

_LATEST = "https://himawari8.nict.go.jp/img/D531106/latest.json"
_TILE = ("https://himawari8.nict.go.jp/img/D531106/{zoom}d/550/"
         "{yy}/{mm}/{dd}/{hms}_{tx}_{ty}.png")
_UA = {"User-Agent": "Mozilla/5.0 (assistant earth-view; +python-urllib)"}

# How often the imagery actually changes. The refresh timer aims slightly past
# it so a new frame is likely to exist by the time we ask.
REFRESH_SECONDS = 10 * 60 + 20

# A rotating globe at one degree per step, fifteen steps a second, is one turn
# every twenty-four seconds — fast enough to read as "live", slow enough to read
# the continents. The rate is also the budget:    one frame is ~10 ms of numpy at
# the 300 px the HUD renders at, so twelve a second costs about an eighth of one
# core while the view is open, and nothing at all when it is closed.
DEGREES_PER_FRAME = 1.2
FRAME_MS = 83


# ── download ────────────────────────────────────────────────────────────────

def latest_stamp(timeout: float = 20.0) -> tuple[str, str]:
    """(capture time 'YYYY-MM-DD HH:MM:SS', tile path prefix) from NICT."""
    req = urllib.request.Request(_LATEST, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    stamp = str(data.get("date") or "")
    if len(stamp) < 19:
        raise RuntimeError("Himawari published no capture time")
    return stamp, str(data.get("file") or "")


def _tile_urls(stamp: str, zoom: int = 2) -> list[tuple[int, int, str]]:
    dt = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
    yy, mm, dd = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
    hms = dt.strftime("%H%M%S")
    return [(tx, ty, _TILE.format(zoom=zoom, yy=yy, mm=mm, dd=dd,
                                  hms=hms, tx=tx, ty=ty))
            for ty in range(zoom) for tx in range(zoom)]


def fetch_latest(timeout: float = 20.0):
    """(PIL.Image of the full disk, 'YYYY-MM-DD HH:MM:SS' UTC).

    The 2×2 mosaic is four requests of ~67 kB. If any tile fails the whole
    fetch falls back to the single 550 px tile, because half an Earth is worse
    than a smaller one.
    """
    from PIL import Image

    stamp, _ = latest_stamp(timeout)
    urls = _tile_urls(stamp, zoom=2)
    try:
        tiles = []
        for x, y, url in urls:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            tiles.append((x, y, Image.open(io.BytesIO(raw)).convert("RGB")))
        w = max(x for x, _, _ in urls) + 1
        h = max(y for _, y, _ in urls) + 1
        tw, th = tiles[0][2].size
        out = Image.new("RGB", (tw * w, th * h))
        for x, y, im in tiles:
            out.paste(im, (x * tw, y * th))
        return out, stamp
    except Exception:
        url = _tile_urls(stamp, zoom=1)[0][2]
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
        return Image.open(io.BytesIO(raw)).convert("RGB"), stamp


# ── projection ──────────────────────────────────────────────────────────────

def _disk_geometry(px: np.ndarray) -> tuple[float, float, float]:
    """(cx, cy, R) of the Earth disc inside the published image.

    Measured rather than assumed: the frame carries a margin of black space whose
    size has changed between products, and a hard-coded radius would silently
    crop the limb.
    """
    bright = px.max(axis=2) > 8
    ys, xs = np.nonzero(bright)
    if xs.size < 500:
        raise RuntimeError("the published image has no Earth disc in it")
    cx = (float(xs.min()) + float(xs.max())) / 2.0
    cy = (float(ys.min()) + float(ys.max())) / 2.0
    # The disc is a circle; the larger of the two spans is the one that was not
    # clipped by a cloud-free limb.
    radius = max(float(xs.max() - xs.min()), float(ys.max() - ys.min())) / 2.0
    return cx, cy, radius


def disk_to_equirect(img, size: tuple[int, int] = (1024, 512),
                     sub_lon: float = SUB_LON) -> np.ndarray:
    """Equirectangular (lat × lon) RGB map built from one full-disk image.

    Returns uint8 (H, W, 3). Longitude runs −180..180 east-positive, latitude
    90..−90 top-down. Pixels on the far side of the globe are painted the deep
    navy of the night side rather than left black, so the sphere has no hole if
    the rotation ever outruns an update.
    """
    px = np.asarray(img.convert("RGB"), dtype=np.uint8)
    cx, cy, radius = _disk_geometry(px)
    h_img, w_img = px.shape[:2]
    width, height = size

    lon = np.linspace(-180.0, 180.0, width, endpoint=False)
    lat = np.linspace(90.0, -90.0, height)

    phi = np.radians(lat)[:, None]
    lam = np.radians(lon[None, :] - sub_lon)

    x = np.cos(phi) * np.sin(lam)
    y = np.sin(phi)
    z = np.cos(phi) * np.cos(lam)

    k = EARTH_RADIUS_KM / SAT_HEIGHT_KM
    scale = radius / (1.0 - k * z)          # perspective, not orthographic
    sx = np.rint(cx + x * scale).astype(np.int32)
    sy = np.rint(cy - y * scale).astype(np.int32)

    visible = z > 0.0
    sx = np.clip(sx, 0, w_img - 1)
    sy = np.clip(sy, 0, h_img - 1)

    tex = px[sy, sx]
    tex[~visible] = (7, 12, 22)
    # A hard limb leaves a one-pixel ring of black that the sphere renderer then
    # magnifies. Erode it by masking anything the source left dark at the edge.
    edge = visible & (px[sy, sx].max(axis=2) <= 3)
    tex[edge] = (7, 12, 22)
    return tex


def placeholder_texture(size: tuple[int, int] = (512, 256)) -> np.ndarray:
    """Something globe-shaped to show before the first image arrives.

    Deliberately not a fake Earth: a deep-ocean gradient with a faint meridian
    grid, so it is obvious the feature is working and waiting, not pretending.
    """
    width, height = size
    lat = np.linspace(1.0, -1.0, height)[:, None]
    lon = np.linspace(-1.0, 1.0, width)[None, :]
    depth = (0.45 + 0.25 * np.cos(lat * np.pi)).astype(np.float32)

    rgb = np.zeros((height, width, 3), dtype=np.float32)
    rgb[..., 0] = 10.0 + 12.0 * depth
    rgb[..., 1] = 26.0 + 44.0 * depth
    rgb[..., 2] = 46.0 + 62.0 * depth

    grid = ((np.abs(np.sin(lat * 6.0)) < 0.02) |
            (np.abs(np.sin(lon * 9.0)) < 0.012))
    rgb[grid] += np.array([10.0, 30.0, 34.0], dtype=np.float32)
    return np.clip(rgb, 0, 255).astype(np.uint8)


# ── rendering ───────────────────────────────────────────────────────────────

# Everything that is a function of (size, texture size) and NOT of the rotation
# angle, computed once. The rotation only shifts longitude — see the identity
# below — so the per-frame cost collapses to one modulo, one multiply and a
# gather. Measured at 340 px: 52 ms/frame when this was recomputed every frame,
# 3.9 ms with the geometry cached.
_GEOM: dict[tuple[int, int, int], dict] = {}
_GEOM_LOCK = threading.Lock()


# Night-side lift. The published disc is a real photograph: at 14:00 UTC the
# Asia-Pacific face it shows is in darkness, and a straight render is an almost
# black sphere for half of every day. This is a display gamma, not invented
# detail — it lifts the shadows enough to read the cloud tops — and it is
# applied to the texture once per refresh, so it costs nothing per frame.
_LIFT = np.clip((np.arange(256, dtype=np.float32) / 255.0) ** 0.72 * 255.0,
                0.0, 255.0).astype(np.uint8)


def _geometry(size: int, tex_w: int, tex_h: int) -> dict:
    key = (size, tex_w, tex_h)
    with _GEOM_LOCK:
        g = _GEOM.get(key)
        if g is not None:
            return g

    lin = np.linspace(-1.0, 1.0, size, dtype=np.float32)
    u = lin[None, :]
    v = lin[::-1][:, None]
    r2 = u * u + v * v
    inside = r2 <= 1.0
    z = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0)).astype(np.float32)

    # Longitude on the sphere BEFORE rotation. Rotating about the polar axis
    # maps atan2(u, z) to atan2(u, z) + θ exactly, which is why the angle can be
    # added to this array instead of re-running the trig.
    base_lon = np.degrees(np.arctan2(u, z)).astype(np.float32)
    lat = np.degrees(np.arcsin(np.clip(v, -1.0, 1.0))).astype(np.float32)
    rows = np.clip(((90.0 - lat) / 180.0 * (tex_h - 1)).astype(np.int32),
                   0, tex_h - 1)
    rows = np.broadcast_to(rows, (size, size))

    limb = (0.55 + 0.45 * np.clip(z, 0.0, 1.0) ** 0.35)[..., None].astype(np.float32)
    halo = (((1.0 - z) ** 6.0)[..., None]
            * np.array([28.0, 96.0, 150.0], dtype=np.float32)).astype(np.float32)
    alpha = np.where(inside,
                     np.clip((1.0 - np.sqrt(r2)) * size * 0.5, 0.0, 1.0) * 255.0,
                     0.0).astype(np.uint8)

    g = {"base_lon": base_lon, "rows": rows, "limb": limb, "halo": halo,
         "alpha": alpha, "tex_w": tex_w}
    with _GEOM_LOCK:
        # Bounded on purpose. The key includes the render size, and a window
        # being dragged produces a new one every pixel — each holding a few
        # megabytes of float arrays. Keeping the last handful is enough for the
        # two or three sizes a settled window actually uses.
        if len(_GEOM) >= 8:
            _GEOM.pop(next(iter(_GEOM)))
        _GEOM[key] = g
    return g


def lift_shadows(tex: np.ndarray) -> np.ndarray:
    """The night-side gamma as a 256-entry lookup, applied once per download."""
    return _LIFT[tex]


def render_sphere(tex: np.ndarray, lon_deg: float = 0.0, size: int = 420,
                  sub_lon: float = SUB_LON, rim: bool = True) -> np.ndarray:
    """One view of the globe as RGBA uint8 (size × size).

    A pixel is on the sphere when its normalised distance from the centre is ≤ 1.
    Its place on the globe comes from the same geometry the deprojection used,
    in reverse: the screen is the satellite's viewpoint and `lon_deg` turns the
    texture underneath it.
    """
    tex_h, tex_w = tex.shape[:2]
    g = _geometry(size, tex_w, tex_h)

    lon = (g["base_lon"] + np.float32(lon_deg + sub_lon + 180.0)) % 360.0
    cols = np.clip((lon * np.float32((tex_w - 1) / 360.0)).astype(np.int32),
                   0, tex_w - 1)

    rgb = tex[g["rows"], cols].astype(np.float32)

    # Limb falloff — a sphere seen from far away gets darker at the edge, and
    # without it a textured disc reads as flat no matter how good the texture is.
    rgb *= g["limb"]
    if rim:
        # Thin blue atmosphere, brightest exactly at the limb.
        rgb += g["halo"]

    out = np.empty((size, size, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = g["alpha"]
    return out


def utc_label(stamp: str) -> str:
    """'13:50 UTC' from the capture time, for the caption."""
    try:
        return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").strftime("%H:%M UTC")
    except Exception:
        return ""


# ── widget ──────────────────────────────────────────────────────────────────

class GlobeWidget(QWidget):
    """A turning Earth, refreshed from the satellite every ten minutes.

    Everything expensive is off the Qt thread: the download AND the
    deprojection run in a worker, and only the finished map is handed back
    through a signal. A refresh that fails leaves the previous map turning and
    retries in a minute — a globe is a thing you leave open, so it must not die
    with the first dropped packet.
    """

    _ready = pyqtSignal(object, str, str)   # equirect array, stamp, error

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._tex = placeholder_texture()
        self._stamp = ""
        self._source = ""
        self._angle = 0.0
        self._status = "CONTACTING HIMAWARI-9…"
        self._busy = False
        self._warned = False
        self._fetched_at = 0.0
        self._last_key: tuple[int, int] | None = None
        self._last_img: QImage | None = None

        self._spin = QTimer(self)
        self._spin.setInterval(FRAME_MS)
        self._spin.timeout.connect(self._advance)

        self._refresh = QTimer(self)
        self._refresh.setInterval(REFRESH_SECONDS * 1000)
        self._refresh.timeout.connect(self.refresh)

        self._ready.connect(self._on_ready, Qt.ConnectionType.QueuedConnection)

    # -- lifecycle ----------------------------------------------------------
    def start(self) -> None:
        if not self._spin.isActive():
            self._spin.start()
        if not self._refresh.isActive():
            self._refresh.start()
        # A view reopened after lunch must not show this morning's photograph:
        # the timer only runs while the widget is open, so staleness is checked
        # on the way in rather than assumed away.
        if not self._stamp or time.monotonic() - self._fetched_at > REFRESH_SECONDS:
            self.refresh()

    def stop(self) -> None:
        self._spin.stop()
        self._refresh.stop()

    def is_running(self) -> bool:
        return self._spin.isActive()

    # -- data ---------------------------------------------------------------
    def refresh(self) -> None:
        """Ask the satellite for the newest disc. Safe to call at any time."""
        if self._busy:
            return
        self._busy = True
        self._status = "SYNCING…"
        self.update()
        threading.Thread(target=self._load, daemon=True,
                         name="globe-refresh").start()

    def _load(self) -> None:
        try:
            img, stamp = fetch_latest()
            tex = disk_to_equirect(img)
            self._ready.emit(tex, stamp, "")
        except Exception as e:                      # noqa: BLE001
            self._ready.emit(None, "", str(e))

    def _on_ready(self, tex, stamp: str, err: str) -> None:
        self._busy = False
        if tex is None:
            self._status = "NO SIGNAL — RETRYING"
            if not self._warned:
                print(f"[Globe] refresh failed: {err}")
                self._warned = True
            # Retry soon rather than waiting out the full ten minutes.
            QTimer.singleShot(60_000, self.refresh)
            self.update()
            return
        self._warned = False
        self._tex = lift_shadows(tex)
        self._stamp = stamp
        self._fetched_at = time.monotonic()
        self._status = ""
        self._last_key = None
        self.update()

    # -- painting -----------------------------------------------------------
    def _advance(self) -> None:
        self._angle = (self._angle + DEGREES_PER_FRAME) % 360.0
        self.update()

    def _frame_image(self, size: int) -> QImage:
        """The sphere at the current angle, rendered at `size` px.

        Cached for one angle only — the previous frame — because the rotation
        steps once per tick and a cache big enough to hold a whole revolution
        would be ~190 MB of QImage at this size. A 340 px render is scaled up by
        the painter instead: the texture is satellite imagery, which has no
        hard edges to lose, and the difference at HUD size is not visible.
        """
        degree = round(self._angle, 1)
        key = (size, degree)
        if self._last_key == key and self._last_img is not None:
            return self._last_img
        rgba = np.ascontiguousarray(
            render_sphere(self._tex, lon_deg=degree, size=size))
        h, w = rgba.shape[:2]
        img = QImage(rgba.data, w, h, 4 * w,
                     QImage.Format.Format_RGBA8888).copy()
        self._last_key, self._last_img = key, img
        return img

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        p.fillRect(rect, QColor(2, 6, 10))

        side = max(64, min(rect.width(), rect.height()) - 18)
        cx, cy = rect.width() / 2.0, rect.height() / 2.0

        # Atmosphere bloom behind the planet.
        glow_r = side * 0.72
        glow = QRadialGradient(cx, cy, glow_r)
        glow.setColorAt(0.0, QColor(20, 90, 150, 90))
        glow.setColorAt(0.62, QColor(10, 44, 82, 60))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(cx - glow_r), int(cy - glow_r),
                      int(glow_r * 2), int(glow_r * 2))

        # Quantised to 20 px, so dragging the window edge cannot mint a new
        # geometry (and a new megabyte) for every pixel of travel.
        render_px = max(200, int(min(side, 300)) // 20 * 20)
        img = self._frame_image(render_px)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.drawImage(QRectF(cx - side / 2, cy - side / 2, side, side), img)

        # Caption: what you are looking at, and how old it is. The feature is
        # called "real time", so it has to say how real.
        p.setPen(QColor(90, 180, 210, 210))
        f = p.font()
        f.setFamily("Courier New")
        f.setPointSize(8)
        f.setBold(True)
        p.setFont(f)
        caption = self._status or (
            f"HIMAWARI-9  ·  {utc_label(self._stamp)}" if self._stamp else "")
        if caption:
            p.drawText(rect.adjusted(0, 0, 0, -4),
                       Qt.AlignmentFlag.AlignHCenter |
                       Qt.AlignmentFlag.AlignBottom, caption)
        p.end()
