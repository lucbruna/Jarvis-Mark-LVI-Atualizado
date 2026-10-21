"""
plugins/msi_afterburner_lite.py — ask Gemini for live MSI Afterburner readings.

Pure drag-and-drop: copy this one file into plugins/, restart the assistant, done. No
other file in the app needs to change and nothing here reaches into the assistant's
own hardware-monitoring code — it's a self-contained voice tool. Ask the assistant
about your CPU/GPU load or temperature and it reads the answer straight out
of MSI Afterburner's own sensors, which on most Windows machines are more
accurate (and, for GPU temperature, often the ONLY source) than what the OS
hands out to ordinary applications.

REQUIREMENTS
    - MSI Afterburner running.
    - In Afterburner: Settings -> Monitoring tab -> "Enable hardware
      monitoring shared memory support" checked (this is OFF by default).
    - Windows only.

HOW IT READS AFTERBURNER
    Afterburner publishes its live sensor readings into a small block of
    named shared memory (its "Hardware Monitoring" / MAHM interface) that any
    process may attach to read-only — no network call, no subprocess, nothing
    written back. This plugin attaches with plain ctypes, finds the CPU/GPU
    usage and temperature sensors by name, and reads them fresh on every
    request.

IF YOUR SENSOR NAMES DON'T MATCH
    Afterburner's labels vary by GPU vendor and motherboard sensor chip. This
    guesses the common ones ("CPU usage", "GPU usage", "CPU temperature",
    "GPU temperature"); the Plugin Manager's settings panel for "MSI
    Afterburner" lets you type the exact label Afterburner shows for your
    hardware if a guess doesn't match anything.
"""
from __future__ import annotations

import ctypes
import platform
import time

try:
    from memory.config_manager import get_plugin_setting
except Exception:
    def get_plugin_setting(namespace, key, default=None):   # settings panel unavailable: use defaults
        return default

PLUGIN = {
    "name": "afterburner_hardware_status",
    "description": (
        "Reports current CPU and GPU load, temperature, and fan speed, read live "
        "from MSI Afterburner's hardware sensors. Use this when the user asks "
        "about CPU/GPU usage, temperature, or fan speed, or specifically "
        "mentions Afterburner."
    ),
    "parameters": {"type": "OBJECT", "properties": {}},
}

PLUGIN_SETTINGS = {
    "namespace": "msi_afterburner_lite",
    "title": "\U0001F321  MSI AFTERBURNER",
    "fields": [
        {"key": "cpu_usage_name", "label": "CPU usage sensor name", "type": "text",
         "placeholder": "CPU usage"},
        {"key": "gpu_usage_name", "label": "GPU usage sensor name", "type": "text",
         "placeholder": "GPU usage"},
        {"key": "cpu_temp_name", "label": "CPU temperature sensor name", "type": "text",
         "placeholder": "CPU temperature"},
        {"key": "gpu_temp_name", "label": "GPU temperature sensor name", "type": "text",
         "placeholder": "GPU temperature"},
        {"key": "gpu_fan_name", "label": "GPU fan speed sensor name", "type": "text",
         "placeholder": "Fan speed"},
        {"key": "cpu_fan_name", "label": "CPU fan speed sensor name", "type": "text",
         "placeholder": "CPU fan  (rarely exposed by Afterburner — leave blank if unsure)"},
    ],
}

_NS = "msi_afterburner_lite"
_DEFAULT_NAMES = {
    "cpu_usage_name": "cpu usage",
    "gpu_usage_name": "gpu usage",
    "cpu_temp_name":  "cpu temperature",
    "gpu_temp_name":  "gpu temperature",
    "gpu_fan_name":   "fan speed",
    "cpu_fan_name":   "cpu fan",
}

_OS = platform.system()

# ── the MAHM shared-memory layout, confirmed against a live Afterburner ──────
# instance rather than taken from a write-up on faith — see the header check
# and the entry stride below for what that turned up.
_SEG_NAMES = ("MAHMSharedMemory", "MAHMSharedMemoryV2")
_SIGNATURE = b"MHAM"        # yes, MHAM — most write-ups have this backwards
_HEADER_LEN = 32            # dwSignature/dwVersion/dwHeaderSize/dwNumEntries/dwEntrySize/...
_NAME_LEN = 260             # each name/unit string in an entry (MAX_PATH), ANSI
# An entry holds 5 of those strings (name, units, localized name, localized
# units, recommended format) immediately followed by the live `data` float.
_VALUE_OFFSET = _NAME_LEN * 5
_FILE_MAP_READ = 0x0004

_kernel32 = None
if _OS == "Windows":
    _kernel32 = ctypes.windll.kernel32
    # ctypes.windll assumes a 32-bit return type unless told otherwise, which
    # truncates the 64-bit pointers these two hand back — dereferencing the
    # truncated address is a hard crash, not a catchable exception.
    _kernel32.OpenFileMappingW.restype  = ctypes.c_void_p
    _kernel32.OpenFileMappingW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
    _kernel32.MapViewOfFile.restype  = ctypes.c_void_p
    _kernel32.MapViewOfFile.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                        ctypes.c_uint32, ctypes.c_size_t]
    _kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]


def _u32(raw: bytes, offset: int) -> int:
    return int.from_bytes(raw[offset:offset + 4], "little", signed=False)


class _Afterburner:
    """Attaches lazily and re-attaches if Afterburner wasn't running yet the
    first time — nothing here runs until a request actually asks for it, so a
    machine without Afterburner running pays no cost just for having this
    file present."""

    def __init__(self):
        self._addr: int | None = None
        self._offsets: dict[str, int] = {}
        self._last_attempt = 0.0

    def _names(self) -> dict[str, str]:
        return {k: (get_plugin_setting(_NS, k) or "").strip().lower() or v
                for k, v in _DEFAULT_NAMES.items()}

    def ensure_attached(self) -> bool:
        if self._addr is not None:
            return True
        if time.time() - self._last_attempt < 5.0:
            return False   # don't hammer OpenFileMappingW on repeated failed queries
        self._last_attempt = time.time()
        if _OS != "Windows":
            return False
        for seg_name in _SEG_NAMES:
            try:
                if self._try_segment(seg_name):
                    return True
            except Exception:
                continue
        return False

    def _try_segment(self, seg_name: str) -> bool:
        handle = _kernel32.OpenFileMappingW(_FILE_MAP_READ, False, seg_name)
        if not handle:
            return False
        # 0 = map the whole section ("to the end of the mapping") — an
        # explicit size larger than the section's real size makes
        # MapViewOfFile fail outright rather than clamp.
        addr = _kernel32.MapViewOfFile(handle, _FILE_MAP_READ, 0, 0, 0)
        if not addr:
            return False
        header = ctypes.string_at(addr, _HEADER_LEN)
        if header[:4] != _SIGNATURE:
            _kernel32.UnmapViewOfFile(addr)
            return False

        header_size = _u32(header, 8)     # dwHeaderSize
        num_entries = _u32(header, 12)    # dwNumEntries
        entry_size  = _u32(header, 16)    # dwEntrySize
        if entry_size < _VALUE_OFFSET + 4 or not (0 < num_entries <= 4096):
            _kernel32.UnmapViewOfFile(addr)
            return False

        table = ctypes.string_at(addr, header_size + num_entries * entry_size)
        names = self._names()
        offsets: dict[str, int] = {}
        for i in range(num_entries):
            base = header_size + i * entry_size
            name = table[base:base + _NAME_LEN].split(b"\x00", 1)[0]
            name = name.decode("latin-1", "ignore").strip().lower()
            if not name:
                continue
            for key, want in names.items():
                if key not in offsets and want in name:
                    offsets[key] = base + _VALUE_OFFSET

        if not offsets:
            _kernel32.UnmapViewOfFile(addr)
            return False

        self._addr = addr
        self._offsets = offsets
        return True

    def read(self, key: str) -> float:
        off = self._offsets.get(key)
        if off is None or self._addr is None:
            return -1.0
        try:
            raw = ctypes.string_at(self._addr + off, 4)
            return float(ctypes.c_float.from_buffer_copy(raw).value)
        except Exception:
            return -1.0


_ab = _Afterburner()


def run(parameters: dict, player=None, session_memory=None) -> str:
    if _OS != "Windows":
        return "Sir, MSI Afterburner integration is Windows-only."

    if not _ab.ensure_attached():
        return ("Sir, I can't reach MSI Afterburner's hardware monitor. Make sure "
                "it's running, and that 'Enable hardware monitoring shared memory "
                "support' is checked under Settings -> Monitoring.")

    cpu, gpu = _ab.read("cpu_usage_name"), _ab.read("gpu_usage_name")
    cpu_t, gpu_t = _ab.read("cpu_temp_name"), _ab.read("gpu_temp_name")
    cpu_fan, gpu_fan = _ab.read("cpu_fan_name"), _ab.read("gpu_fan_name")

    parts = []
    if cpu >= 0:
        parts.append(f"CPU at {cpu:.0f} percent")
    if cpu_t >= 0:
        parts.append(f"{cpu_t:.0f} degrees")
    if cpu_fan >= 0:
        parts.append(f"CPU fan at {cpu_fan:.0f} percent")
    if gpu >= 0:
        parts.append(f"GPU at {gpu:.0f} percent")
    if gpu_t >= 0:
        parts.append(f"{gpu_t:.0f} degrees")
    if gpu_fan >= 0:
        parts.append(f"GPU fan at {gpu_fan:.0f} percent")

    if not parts:
        return ("Sir, Afterburner's hardware monitor is reachable, but none of its "
                "sensor names matched what I'm looking for. You can set the exact "
                "names in the MSI Afterburner plugin settings.")

    reply = f"Reading from MSI Afterburner: {', '.join(parts)}."
    if player:
        try:
            player.write_log(f"JARVIS: {reply}")
        except Exception:
            pass
    return reply
