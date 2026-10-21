# Offline Mode

Mark LVI can run fully offline:

1. Engine: choose a local provider (Ollama / LM Studio / llama.cpp / vLLM) in ENGINE & PROVIDERS.
2. STT: install faster-whisper (CPU) from the providers panel.
3. TTS: use Piper (neural, ~50 languages) or the system voice.
4. Wake word: openwakeword runs locally.
5. Web search falls back to DuckDuckGo; with no internet it returns cached results.
6. Memory, file tools, screen capture, and app control work without network.

No API key is required for a fully local setup.
PY