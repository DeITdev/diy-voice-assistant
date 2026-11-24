# Progress Tracker

Update this file after every meaningful implementation change.

## Current Phase

- **Milestone 2/3 (Local AI Models & Edge Client Proof)** (In Progress) — Ollama LLM (`gemma2-lokal`), Piper TTS (`id_ID-news_tts-medium`), and Whisper Tiny STT successfully installed and tested locally on Raspberry Pi 4B.

## Current Goal

- Wire STT, LLM, and TTS into a unified voice pipeline / service and prepare hardware wiring (Milestone 1).

## Completed

- Implemented branch-aware `context-collaboration` workflow across [AGENTS.md](file:///home/nova/diy-voice-assistant/AGENTS.md) and [CLAUDE.md](file:///home/nova/diy-voice-assistant/CLAUDE.md), added `context/progress/.gitkeep` and `scripts/consolidate_progress.py`, and synced `context/architecture.md` and `context/ai-workflow-rules.md`.
- Authored Master PRD v1.0 ([prd_diy_voice_assistant_speaker_integrated_with_gen_ai.md](file:///home/nova/diy-voice-assistant/prd_diy_voice_assistant_speaker_integrated_with_gen_ai.md)).
- Installed 15 project-scoped implementation skills into `.agents/skills/` (16 total with `find-skills`) and locked versions in `skills-lock.json`.
- Populated all `context/` specification files aligned with the PRD.
- Configured local AI models on Raspberry Pi 4B:
  - **LLM (Otak):** Gemma 2 2B Q4_K_M (`gemma2-lokal`) and Qwen 2.5 1.5B (`qwen2.5:1.5b`, 986 MB download, 1.2 GB RAM) installed and verified in Ollama.
  - **TTS (Mulut):** Piper TTS with official Indonesian voice `id_ID-news_tts-medium` (61 MB) installed in `/home/nova/models/piper/`.
  - **STT (Telinga):** Faster-Whisper Tiny int8 (75 MB) installed in `/home/nova/models/whisper/`.
  - Authored [scripts/test_stt_tts.py](file:///home/nova/diy-voice-assistant/scripts/test_stt_tts.py) and verified end-to-end synthesis and transcription on Raspberry Pi 4 with 100% word accuracy.
  - Authored [scripts/demo_tanya_jawab.py](file:///home/nova/diy-voice-assistant/scripts/demo_tanya_jawab.py) with dynamic `--model` selection; confirmed Qwen 2.5 1.5B executes >2x faster (~27s vs ~64s) with higher RAM efficiency (1.2 GB vs 2.0 GB).
  - Built and deployed lightweight Web Management Dashboard (`web/main.py`, `web/static/index.html`, `web/static/app.js`) powered by FastAPI. Features real-time telemetry (CPU, RAM, Temp, Disk), dynamic model switcher (Qwen 2.5 vs Gemma 2), in-browser microphone voice chat via Whisper STT, text chat, audio playback in browser, and hardware 3.5mm jack speaker trigger.
  - Configured and activated `voice-assistant-web.service` via `systemd` ([scripts/voice-assistant-web.service](file:///home/nova/diy-voice-assistant/scripts/voice-assistant-web.service)). Dashboard and Ollama now auto-start synchronously on boot and gracefully terminate on shutdown.

## In Progress

- None yet.

## Next Up

1. Resolve open configuration/hardware questions below with the user.
2. **Milestone 1 (Hardware Bench Proof):** Assemble BOM on breadboard, verify Stage 1 pre-power checklist, configure Pi 4 `/boot/firmware/config.txt` + `/etc/asound.conf`, and pass Stage 2 (`HW-01`..`HW-04`).
3. **Milestone 2 (Local AI Server):** Author `server/compose.yaml` (STT `faster-whisper`, LLM `Ollama`/`vLLM`, TTS `Kokoro-FastAPI`/`Piper`) and pass Stage 3 `curl` tests.
4. **Milestone 3 (Edge Voice Client & Daemon):** Initialize `uv` Python project (`src/voice_assistant/`, `tests/`), implement config/clients/VAD/wakeword/state machine using TDD, deploy `voice-assistant.service`, and pass Stage 4 (`E2E-01`..`E2E-08`).
5. **Milestone 4 (Enclosure):** Assemble final enclosure and re-verify `E2E-02` and `E2E-04`.

## Open Questions

- **Local AI Server Hardware Profile:** Will the LAN server run with a dedicated NVIDIA GPU (enabling `faster-whisper` `large-v3-turbo` + `Kokoro-FastAPI` for ~2.5 s latency) or CPU-only (`small`/`int8` + `Piper TTS` for ~5.4 s latency)?
- **Static LAN IP:** What static IP is reserved for the Local AI Server (PRD example uses `192.168.1.50`)?
- **Target Language(s):** V1 MVP primary language — English only, Indonesian only, or bilingual (affects wake-word model, Whisper config, and Kokoro vs Piper voice selection)?
- **VAD Implementation:** Prefer `webrtcvad` (requires C build / wheel on aarch64) or pure-NumPy RMS energy threshold for V1 end-of-speech detection?
- **Pi 4 Python Runtime:** Deploy on Pi 4 using `uv` directly on 64-bit Raspberry Pi OS or `python3 -m venv` generated from `pyproject.toml`?

## Architecture Decisions

- **Split Edge/Server Topology:** Keep only wake-word detection (`openWakeWord`), VAD, and I2S audio I/O on the Raspberry Pi 4; offload STT, LLM, and TTS to a LAN Local AI Server to prevent Pi thermal throttling and hit ~2.5–5.4 s latency.
- **OpenAI-Compatible HTTP Contract:** Standardize on `/v1/audio/transcriptions`, `/v1/chat/completions`, and `/v1/audio/speech` configured via `.env` so STT/LLM/TTS engines can be swapped with zero code changes.
- **Half-Duplex Mute Over AEC (V1):** Mute microphone capture during `THINKING`/`SPEAKING` and flush buffer before returning to `IDLE` (`E2E-04`), deferring acoustic echo cancellation barge-in to V2+.
- **Modern Python & Compose v2 Tooling:** Standardize development on `uv`, `ruff`, `ty`, `pytest`, `pydantic-settings`, `httpx`, `tenacity`, and Docker Compose v2 (`compose.yaml`).

## Session Notes

- Repository currently contains only the PRD, `AGENTS.md`/`CLAUDE.md`, `context/*.md`, `.agents/skills/` (16 project-scoped skills), and `skills-lock.json` — no application source code (`src/`, `server/`, `tests/`) has been scaffolded yet.
