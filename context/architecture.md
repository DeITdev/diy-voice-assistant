# Architecture Context

## Stack

| Layer | Technology | Role |
| :--- | :--- | :--- |
| Edge Hardware | Raspberry Pi 4 Model B + `INMP441` + `MAX98357A` + 2" 4-ohm 3W Speaker | Always-on smart speaker I2S audio capture and Class-D playback |
| Edge OS & Audio | Raspberry Pi OS (64-bit, Debian), `googlevoicehat-soundcard`, ALSA `softvol` (`asound.conf`), `portaudio19-dev`, `aplay` | Duplex I2S kernel driver, software mic gain boost, and WAV playback |
| Edge Process Manager | `systemd` (`voice-assistant.service`) + `journalctl` | Headless boot auto-start, restart supervision, and log rotation |
| Edge Voice Client | Python >=3.11 (`uv` / `venv`), `sounddevice`, `openWakeWord` (ONNX), `webrtcvad` / RMS VAD, `numpy`, `httpx`, `tenacity`, `pydantic-settings` | Wake-word detection, VAD recording, state machine, resilient LAN HTTP client |
| Local AI Server (Orch.) | Docker Compose v2 (`compose.yaml`) on LAN PC / Home Server | Container lifecycle, healthchecks, named model volumes, LAN port binding |
| STT Service | `faster-whisper` (`faster-whisper-server` / Speaches or custom `FastAPI` wrapper) | `POST /v1/audio/transcriptions` (`small`/`medium`/`large-v3-turbo`) |
| LLM Service | `Ollama`, `vLLM`, or `llama.cpp` (`qwen2.5:7b` / `llama3.2`) | `POST /v1/chat/completions` with concise spoken-text system prompt |
| TTS Service | `Kokoro-FastAPI` or `Piper TTS` (or custom `FastAPI` wrapper) | `POST /v1/audio/speech` returning 16 kHz / 22.05 kHz mono `audio/wav` |
| Dev & QA Tooling | `pytest`, `pytest-cov`, `ruff`, `ty` | Unit/contract tests (mocked audio/HTTP), linting, formatting, static type checks |

## System Boundaries

```text
+-------------------------------------------------------------------+
|               EDGE DEVICE: RASPBERRY PI 4 MODEL B                 |
|  [INMP441 I2S Mic] -> ALSA (softvol) -> openWakeWord -> VAD       |
|  [MAX98357A Amp]   <- aplay          <- Audio Player <- StateMach |
+---------------------------------------|----------------|----------+
                                        | WAV Out        | WAV In
                                        | (LAN HTTP)     | (LAN HTTP)
+---------------------------------------|----------------v----------+
|                 LOCAL AI SERVER (LAN STATIC IP)                   |
|  [STT: faster-whisper :8000] -> [LLM: Ollama :11434] -> [TTS :8880]|
+-------------------------------------------------------------------+
```

Planned repository module boundaries (keeping I/O, state transitions, and server infrastructure decoupled):

- `src/voice_assistant/` — Edge Voice Client Python package (`src/` layout):
  - `config.py` — Typed `pydantic-settings` configuration loaded from `.env` at startup.
  - `state_machine.py` — Pure `IDLE -> LISTENING -> THINKING -> SPEAKING -> ERROR` coordinator and rolling `LLM_HISTORY_TURNS` buffer (injected dependencies, no direct hardware/network calls).
  - `audio/` — ALSA/PortAudio capture stream (`sounddevice`), end-of-speech VAD recorder, chime/response WAV playback (`aplay`), and buffer flush helpers.
  - `wakeword/` — `openWakeWord` ONNX frame scoring and state reset adapter.
  - `clients/` — `httpx` + `tenacity` API adapters for OpenAI-compatible STT, LLM, and TTS endpoints.
  - `main.py` — Application composition root wiring `Settings`, audio, wake word, and HTTP clients.
- `assets/` — Local audio chimes (`chime_wake.wav`, `chime_err.wav`, optional offline fallback WAV).
- `server/` — Local AI Server Docker Compose v2 stack (`compose.yaml`, `compose.override.yaml`, `.env.example`, system prompt config, and any custom `FastAPI` STT/TTS wrappers).
- `system/` — Raspberry Pi OS reference configs (`/boot/firmware/config.txt` snippet, `asound.conf`, `voice-assistant.service` `systemd` unit).
- `tests/` — `pytest` suite (`conftest.py`, unit tests with mocked audio/HTTP, integration contract tests).
- `context/` — Living project context, architecture, standards, workflow rules, progress tracker, and branch-isolated progress fragments (`context/progress/`).
- `scripts/` — Standalone PEP 723 maintenance/diagnostic scripts (including `scripts/consolidate_progress.py` for merging `context/progress/*.md` fragments into `context/progress-tracker.md`).

## Storage Model

- **Edge State (In-Memory Only in V1):**
  - Conversation context is held in an in-memory rolling buffer capped at `LLM_HISTORY_TURNS` (default `4` user/assistant turn pairs); no local database is used.
  - Recorded query audio and synthesized TTS WAV payloads live in memory or ephemeral `/tmp` files and are discarded immediately after the turn completes.
- **Edge Configuration & Static Assets (Filesystem):**
  - `.env` (gitignored) stores all endpoints, thresholds, and timeouts.
  - `assets/*.wav` holds bundled feedback chimes.
  - `/var/lib/alsa/asound.state` persists `Mic Boost` via `sudo alsactl store`.
- **Local AI Server Persistence (Docker Named Volumes):**
  - Model weights and caches (Whisper checkpoints, Ollama models, Kokoro/Piper voices) live in Docker named volumes so container upgrades do not re-download models.

## Network, Auth, and Access Model

- **LAN-Only Trust Boundary:**
  - The Local AI Server has a static LAN IP via router DHCP reservation (e.g., `192.168.1.50`), with Pi 4 connected over Ethernet or 5 GHz Wi-Fi.
  - Neither the Pi 4 SSH port nor the Local AI Server ports (`8000`, `11434`, `8880`) are exposed to the public internet.
- **Service Auth & Execution Privileges:**
  - Local LAN STT/LLM/TTS services use unauthenticated or optional local-token OpenAI-compatible HTTP endpoints inside the trusted home LAN.
  - `voice-assistant.service` runs as a non-root user (`pi` or dedicated service account in the `audio` group), never as `root` unless required for system-level config edits.

## Invariants

1. **Hardware Voltage Isolation:** `INMP441 VDD` MUST be wired strictly to **3.3V (Pin 1)**; 5V permanently destroys the MEMS microphone. `MAX98357A VIN` connects to **5V (Pin 2)**. Both share common `GND`, `GPIO 18` (`BCLK`/`SCK`), and `GPIO 19` (`LRC`/`WS`).
2. **Half-Duplex Self-Trigger Prevention:** Microphone capture MUST stay paused/muted during `THINKING` and `SPEAKING`. After `aplay` finishes, the input audio buffer MUST be flushed and `openWakeWord` state reset before transitioning back to `IDLE`.
3. **Bounded Network Calls & Safe Recovery:** Every LAN HTTP call MUST specify `HTTP_TIMEOUT_SEC` (default `25` s). Timeouts or HTTP 5xx errors MUST transition to `ERROR` (play `chime_err.wav`) and return cleanly to `IDLE` without crashing the daemon.
4. **Configuration Externalization:** All IP addresses, ports, model names, VAD thresholds, and timeouts MUST live in `.env` and be validated at startup—zero hardcoded server IPs or magic constants in application logic.
5. **Spoken-Friendly LLM Output:** The LLM system prompt MUST instruct the model to return plain spoken text only (no Markdown, bullets, asterisks, or URLs) in 1–3 concise sentences unless detailed explanation is requested.
6. **Pi 4 Thermal & CPU Ceiling:** Heavy inference (STT, LLM, TTS) MUST NOT run on the Raspberry Pi 4. The Pi 4 edge loop must keep `IDLE` CPU under `30%`, CPU temp under `65°C`, and memory flat across multi-hour runs.
