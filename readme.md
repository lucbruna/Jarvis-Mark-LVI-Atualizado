# JARVIS — Mark LVI (Mark-LVI)

> A voice-first desktop assistant with a holographic HUD, 160+ drop-in plugins,
> local/remote LLM providers, Docker & Git control, and an optional unrestricted mode.

![Python](https://img.shields.io/badge/python-3.11-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ What it can do

### 🎙️ Voice & conversation
- **Gemini Live** speech-to-speech by default (no separate STT/TTS needed).
- **Pipeline mode**: plug your own STT (Whisper), LLM (Ollama/LM Studio/vLLM/OpenAI-compatible) and TTS (Piper/system voices).
- Wake word ("Hey Jarvis"), push-to-talk, multi-language voice following.
- Reasoning models (`<think>` blocks) are filtered out of speech.

### 🖥️ Holographic HUD
- PyQt6 software-rendered animated head / reactor core, no GPU required.
- Permission, confirmation and content banners on screen.
- Audio device picker, settings panels, plugin manager.

### 📁 Files & desktop
- List, read, write, create, move, copy, rename, delete (to Recycle Bin), search, organize desktop.
- Disk usage, file info, largest files.
- Protected folders guarded by default; unlocked mode removes guards.

### 🌐 Web, media & vision
- Web search, URL fetch, browser control, YouTube playback on HUD.
- Screenshot / camera capture sent to the model.
- Image/video/audio processing, OCR, transcription, media creation.

### 🖥️ System & processes
- System status, CPU/RAM/GPU meters, volume, brightness, Wi-Fi.
- Process listing and controlled termination (protected OS processes guarded).
- Shutdown/restart with on-screen confirmation.

### 🐳 Docker & DevOps
- Docker status, start Docker Desktop, pull/run/stop/remove containers.
- Git clone + `docker compose up`.
- Docker Compose management (up/down/ps/logs/build/restart).
- Terraform, AWS/Azure/GCP CLIs, Jenkins triggers, GitLab/Bitbucket openers.

### 💬 Communication & productivity
- Slack, Discord, Reddit, Twitter/X, LinkedIn, Instagram, Twitch notifications.
- Email (Gmail/Outlook), Teams, Zoom, Webex, Google Meet.
- Calendar, contacts, notes (Obsidian, OneNote, Apple Notes, Notion), Todoist.
- Trello, Asana, Monday, Airtable, Jira, Confluence.
- Salesforce, HubSpot, Mailchimp, Stripe, PayPal.
- Password manager, TOTP, QR/barcode, unit converter, calculator, finances, habits, health, recipes, travel, weather, news.

### 🔐 Security & permissions
- Permission denials detected from tool results (text + real exceptions).
- Elevation via Windows UAC (ShellExecuteW `runas`) with return-code handling.
- Rate-limited banners, confirmation gate for irreversible actions.
- **Unrestricted mode** (opt-in) disables safe-path/process/confirmation guards.

### 📱 Remote dashboard
- FastAPI dashboard reachable from phone (firewall auto-config via UAC).
- TLS, QR pairing, remote keys.

### 🔌 Plugin system
- 160+ drop-in plugins in `plugins/`.
- Each plugin declares `PLUGIN` and `run()`; settings via `PLUGIN_SETTINGS`.
- Generic `PluginSettingsOverlay` renders forms automatically.

---

## 🚀 Installation

```bash
git clone https://github.com/lucbruna/Jarvis-Mark-LVI-Atualizado.git
cd Jarvis-Mark-LVI-Atualizado
python -m pip install -r requirements.txt
python -m pip install -r requirements-optional.txt   # heavy extras
python -m playwright install chromium
python main.py
```

### Optional dependencies
Heavy extras (Whisper, Piper, MediaPipe, pandas, pydub) are listed in
`requirements-optional.txt` and install with one click from the app.

### Windows-only
`comtypes`, `pycaw`, `pywin32`, `wmi`, `pywinauto` are installed automatically on Windows.

---

## ⚙️ Configuration

- `config/api_keys.json` — Gemini key, assistant name, voice, provider settings, plugin credentials.
- `memory/config_manager.py` — typed getters/setters for all settings.
- Unrestricted mode:
  ```json
  { "unrestricted_mode": true }
  ```
  or env `MARKLVI_UNRESTRICTED=1`, or via the **Customise Assistant** panel toggle.

### Plugin credentials
Stored under `plugin_config[<namespace>]` in `api_keys.json`. Configure via the
**Plugin Settings** overlay or programmatically:
```python
from memory.config_manager import save_plugin_config
save_plugin_config("slack_notify", {"webhook_url": "https://hooks.slack.com/..."})
```

---

## 🏗️ Architecture

```
core/        # permissions, confirm, sandbox, gemini, llm clients, updater, ...
actions/     # built-in tools (file_controller, desktop, computer_control, ...)
plugins/     # drop-in plugins (160+)
providers/   # STT/LLM/TTS providers + audio + schema
memory/      # config_manager, memory_manager, cache
dashboard/   # FastAPI remote dashboard
ui.py        # PyQt6 HUD
main.py      # orchestration, tool dispatch, permission gating
```

- Tool results flow through `permission_gate.note()` for denial detection.
- Irreversible actions go through `core.confirm.request()` (human gate).
- Untrusted content is wrapped with `core.outcome.untrusted()`.

---

## 🧪 Tests

```bash
python -m providers._tests          # provider self-tests
python -m pytest tests/ -q          # unit tests
python -m compileall -q .           # compile check
```

---

## 🐳 Docker

```bash
# Status
docker_control(action="status")
# Pull & run
docker_control(action="pull", image="nginx")
docker_control(action="run", image="nginx", ports="8080:80", name="web")
# Clone repo + compose
docker_control(action="clone", repo="https://github.com/user/repo.git", dest="./repo")
```

---

## 🔄 Auto-update from GitHub

To keep your fork in sync:

```bash
git remote add origin https://github.com/lucbruna/Jarvis-Mark-LVI-Atualizado.git
git branch -M main
git push -u origin main
```

The app includes `core/updater.py` for update checks; configure it to pull from
your fork's `main` branch.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🙏 Credits

Based on [Mark-LVI](https://github.com/FatihMakes/Mark-LVI) by FatihMakes,
extended with new plugins, unrestricted mode, download/install, Docker control,
and UI improvements.
