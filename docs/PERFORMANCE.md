# Performance Tuning

- Speculative decoding: use llama.cpp with `--draft` model for 2-3x speedup on local LLMs.
- Quantization: prefer Q4_K_M GGUF for best speed/quality tradeoff.
- Whisper: use `large-v3-turbo` on GPU, `base` on CPU.
- Piper: voices are cached after first load; keep the process warm.
- Cache: `core/cache.py` memoizes screen reads, web searches, and summaries.
- Noise gate: set `JARVIS_NOISE_GATE=60` to drop quiet blocks.
PY