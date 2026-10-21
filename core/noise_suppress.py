"""core/noise_suppress.py - optional DeepFilterNet noise suppression.

Falls back to a no-op when DeepFilterNet is not installed. Handles the
sample-rate mismatch between the microphone (16 kHz) and DeepFilterNet
(48 kHz) by resampling with linear interpolation.
"""
from __future__ import annotations

import os


def available() -> bool:
    try:
        import df  # noqa: F401
        return True
    except Exception:
        return False


def enabled() -> bool:
    return os.environ.get("JARVIS_NOISE_SUPPRESS", "").lower() in ("1", "true", "yes", "on") and available()


def _resample(x, src_sr, dst_sr):
    import numpy as np
    if src_sr == dst_sr:
        return x
    n = int(len(x) * dst_sr / src_sr)
    xp = np.linspace(0, 1, len(x))
    fp = x
    xq = np.linspace(0, 1, n)
    return np.interp(xq, xp, fp).astype(x.dtype)


def process(samples, src_sr: int = 16000):
    """Return processed samples (numpy array). Passthrough if unavailable."""
    if not enabled():
        return samples
    try:
        import numpy as np
        from df import enhance, init_df
        model, df_state, _ = init_df()
        arr = np.asarray(samples)
        orig_dtype = arr.dtype
        f32 = arr.astype("float32").reshape(-1)
        up = _resample(f32, src_sr, 48000)
        enhanced = enhance(model, df_state, up.reshape(-1, 1))
        enhanced = enhanced.reshape(-1)
        down = _resample(enhanced, 48000, src_sr)
        return down.astype(orig_dtype).reshape(arr.shape)
    except Exception:
        return samples
