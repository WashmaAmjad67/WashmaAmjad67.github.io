# Atlas — local desktop assistant

A Python app for Windows 10/11 that opens in your browser. Local chat and scene prompts run through **Ollama**, with no API key or per-message fee. SQLite keeps conversations and notes on your computer. Voice transcription uses faster-whisper on your CPU; speech playback uses your browser/Windows voice.

## Windows setup (8 GB RAM, no GPU)

1. Install **Python 3.11 or newer** from https://www.python.org/downloads/windows/ (enable the Python launcher).
2. Install **Ollama for Windows** from https://ollama.com/download/windows and open it. Windows 10 must be version 22H2 or newer for Ollama; use Windows 11 if possible.
3. Download/extract this project into a folder you can write to. Double-click **setup-windows.bat**. It creates an isolated Python environment, installs dependencies including local voice support, creates `.env` if absent, and downloads `qwen2.5:1.5b` (about 1 GB). Keep several GB of free disk space for dependencies, models, and data.
4. Double-click **start-windows.bat**. Your browser opens when the server is ready. Keep its terminal open; close it or press Ctrl+C to stop Atlas. Keep Ollama running.
5. Allow microphone access in current Edge or Chrome. Click **Record**, speak, then **Finish recording**. Edit the transcript and press **Send**. The first transcription downloads the Whisper `base` model; later transcription is local. Enable **Read aloud** for spoken replies and use **Stop speaking** to interrupt.

The app uses http://127.0.0.1:8000 locally. This is a browser-based desktop application, not a native Windows executable. It cannot be hosted on GitHub Pages. The included scripts have been inspected but require a Windows machine for full validation.

### If something fails

- `py` not found: install Python including the launcher, then reopen the setup script.
- Model cannot connect: open Ollama, then run `ollama list` and `ollama pull qwen2.5:1.5b` in a terminal.
- Out of memory: close other apps. Set `OLLAMA_MODEL=qwen2.5:0.5b` in `.env` and run `ollama pull qwen2.5:0.5b`. Restart Atlas. Smaller models are less accurate.
- Speech recognition takes time: CPU transcription is slower than cloud services. For less memory use set `LOCAL_STT_MODEL=tiny` in `.env`.
- Port 8000 is already in use: stop the other program before starting Atlas. Do not expose this app to your network or the public Internet.
- Research fails: it needs access to `en.wikipedia.org`. Chat and notes do not need the Internet once models are downloaded.
- Browser voice availability and offline playback depend on installed Windows/browser voices. Select/install an offline Windows voice for fully offline playback.

## Features and present limits

- Streaming chat, saved conversations, auto titles, a safe basic Markdown subset, cancel control, and answer-to-note actions.
- Notes: create, edit, tags, SQLite FTS5 search, and confirmation before permanent deletion. Type exactly `save this as a note` to save the last assistant reply. Other note operations use the Notes panel; unrestricted model-selected note tools are not implemented.
- Local research: reads up to three **Wikipedia article introductions** from its API and shows source cards. This is limited reference research, not general web research or an authoritative source verification system. The model is asked to cite supplied links; citation accuracy and factual coverage are not guaranteed. A URL check is not evidence that every claim is supported.
- Scene studio: structured scene fields and copyable image prompts. Small models may produce invalid structured output; the API reports this as a failure rather than pretending it succeeded.
- Local record/transcribe, editable transcript, browser read-aloud, stop playback. No wake word or background listening. First-run model downloads require Internet.
- **Local image generation is not included.** Copy the prompt into your image tool. An optional OpenAI image adapter is available when that provider is explicitly configured, with a paid-action confirmation.
- Chat history is limited to the last 30 messages and the local model's 4096-token context. Earlier context can be lost. Small local models can hallucinate.
- No autonomous background tasks, OS control, sending email, or purchases.

## Optional OpenAI mode

Only if you choose a cloud provider, edit your local `.env`:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=your-key-entered-locally
OPENAI_MODEL=gpt-4.1-mini
```

Restart the app. This sends messages/audio and research requests to the provider and incurs API charges. OpenAI mode uses its hosted web-search tool; image generation is a separate explicit paid action. Never share or commit `.env`. Keep `AI_PROVIDER=ollama` for local operation. API keys are not needed for local mode.

## Development

Python 3.11+ is required. From this folder:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
# Optional local microphone transcription:
python -m pip install faster-whisper
# Copy .env.example to .env, then start Ollama and pull the configured model.
python launch.py
python -m pytest -q
python -m ruff check .
```

Architecture: `assistant_app/main.py` owns FastAPI routes and streaming events; `provider.py` has local/OpenAI adapters; `research.py` reads fixed Wikipedia API endpoints; `db.py` owns SQLAlchemy/SQLite storage and transactional FTS updates; `static/` contains the no-build browser UI. Tables are initialized automatically without dropping existing data. Schema migrations will be needed for future schema changes. `launch.py` opens the browser after readiness.

## Storage, trust, and validation

Data lives in `data/assistant.db` and generated images in `data/images/`. Close Atlas before backing up the entire `data` folder. `.env` and `data/` are ignored by Git. Storage is local but **not encrypted**. Any user with access to your Windows account/files can read it. There is no remote login or multi-user isolation. The server binds only to loopback, validates Host/Origin and a custom write header, limits write frequency and text sizes, and uses provider request timeouts. The upload handler rejects recordings over 20 MB after multipart parsing; this is not an Internet-facing hardened service. Web data is treated as untrusted reference text, and source URLs are shown. These measures do not make small models immune to prompt injection or inaccurate answers.

Automated API tests use fake providers for repeatable chat/scene/research/error tests and real SQLite for persistence/FTS. They do **not** prove Ollama inference, external search, microphone access, Windows launchers, or optional paid provider APIs work on your desktop. Use the checklist below after installation.

### Desktop acceptance checklist

- Send two related questions, reload the page, reopen the conversation, and continue it.
- Create a tagged note, search for a word in its body, edit it, and verify both cancel and confirm for deletion.
- Record a sentence, edit its transcript, send it, enable read-aloud, and stop the voice.
- Enable Research for a Wikipedia topic and inspect the returned source cards and claims.
- Create a scene, copy the prompt, and verify all structured fields are present.
- Close Atlas, start it again, and check that chats and notes remain.

A development Dockerfile is included (not exercised in this workspace). If you use it, publish **only** `127.0.0.1:8000:8000`, mount a persistent data volume, and configure `OLLAMA_URL` for your host's Ollama service. The Windows scripts are the recommended route. CI runs pytest and Ruff without making paid API calls.
