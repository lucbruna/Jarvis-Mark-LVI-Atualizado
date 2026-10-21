"""core/noise_gate.py - simple amplitude noise gate for the microphone.

Not a real noise suppressor (that needs RNNoise/DeepFilterNet), but a cheap
gate that drops blocks whose RMS is below a threshold, so room hum and fan
noise do not reach the model or the wake word. Cheap enough to run on every
audio block. Threshold is configurable; 0 disables.
"""
from __future__ import annotations

import os


def _threshold() -> float:
    try:
        return float(os.environ.get("JARVIS_NOISE_GATE", "40"))
    except Exception:
        return 40.0


def gate(samples, threshold: float | None = None) -> bool:
    """Return True if the block should be KEPT (loud enough)."""
    thr = _threshold() if threshold is None else threshold
    if thr <= 0:
        return True
    try:
        import numpy as np
        x = np.asarray(samples, dtype=np.float32)
        if x.size == 0:
            return False
        rms = float((x * x).mean() ** 0.5)
        return rms >= thr
    except Exception:
        return True
