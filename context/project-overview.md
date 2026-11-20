# DIY Voice Assistant Speaker Integrated with Gen AI

## Overview

A privacy-first, hands-free smart speaker powered by a **Raspberry Pi 4 Model B** and raw **I2S digital audio modules** (`INMP441` MEMS microphone + `MAX98357A` Class-D amplifier/DAC + 2-inch 4-ohm 3W speaker). Unlike commercial smart speakers tied to cloud ecosystems, all generative AI workloads—Speech-to-Text (STT), Large Language Model (LLM) reasoning, and Text-to-Speech (TTS)—run on a self-hosted **Local AI Server** over the local network (LAN), delivering fast, Nest-like voice interaction with zero cloud dependencies.

Source of truth for hardware, endpoints, and acceptance criteria: [prd_diy_voice_assistant_speaker_integrated_with_gen_ai.md](file:///Users/Danar/Project/Ngoding/diy-voice-assistant/prd_diy_voice_assistant_speaker_integrated_with_gen_ai.md).

## Goals

1. **Low-Cost, Clean Audio Hardware:** Capture clear room-distance speech and play crisp audio using `INMP441` + `MAX98357A` on the Pi 4's shared I2S bus (`googlevoicehat-soundcard` overlay + ALSA `softvol` boost).
2. **100% Local AI Ownership:** Zero external cloud AI APIs or subscriptions; all STT (`faster-whisper`), LLM (`Ollama`/`vLLM`/`llama.cpp`), and TTS (`Kokoro-FastAPI`/`Piper`) run on the user's LAN server.
3. **Hands-Free Appliance UX:** Always-on local wake-word detection (`openWakeWord`), automatic end-of-speech VAD, concise plain-text spoken replies, and headless boot auto-start via `systemd`.
4. **Fast End-to-End Latency:** Target **~2.5 s** total response turnaround on a GPU server (or **~5.4 s** on a CPU-only server) from end-of-speech to speaker playback.
5. **Clean Enclosure:** Compact, fabric-wrapped cylindrical or 3D-printed smart speaker housing with acoustic separation between mic and speaker.

## Core User Flow

1. **Boot & `IDLE`:** On power-on, `voice-assistant.service` starts automatically and streams 80 ms (`1280` samples at 16 kHz) audio frames from ALSA into `openWakeWord`.
2. **Wake & `LISTENING`:** When the wake word (e.g., *"Hey Jarvis"*) crosses `WAKE_WORD_THRESHOLD`, the Pi plays `chime_wake.wav` and records 16 kHz 16-bit mono WAV audio until `SILENCE_DURATION_SEC` (1.5 s) of silence or `MAX_RECORD_SEC` (10 s).
3. **Process & `THINKING`:** Microphone capture pauses. The Pi posts the WAV to the LAN STT endpoint, appends the transcript to the rolling short-term history (`LLM_HISTORY_TURNS`), requests a concise plain-text reply from the LAN LLM, and synthesizes a WAV stream from the LAN TTS endpoint.
4. **Respond & `SPEAKING`:** The Pi plays the synthesized WAV through the `MAX98357A` via `aplay -q` while keeping the microphone muted to prevent acoustic feedback/self-triggering, flushes the capture buffer, resets wake-word state, and returns to `IDLE`.
5. **Fault Recovery (`ERROR`):** On network timeout (`HTTP_TIMEOUT_SEC`, 25 s) or server HTTP 5xx, the Pi plays `chime_err.wav` (or an offline fallback WAV) and returns cleanly to `IDLE`.

## Features

### Edge Audio & Hardware Layer (Raspberry Pi 4)
- Duplex I2S bus wiring (`GPIO 18` BCLK, `GPIO 19` LRCLK, `GPIO 20` DIN, `GPIO 21` DOUT)
- Boot firmware I2S configuration (`/boot/firmware/config.txt`) and ALSA `softvol` Mic Boost (`/etc/asound.conf`)
- Headless `systemd` daemon (`voice-assistant.service`) with `journalctl` logging

### Edge Voice Client (Python)
- `IDLE -> LISTENING -> THINKING -> SPEAKING -> ERROR` state machine
- Local wake-word detection via `openWakeWord` (ONNX runtime, <30% Pi 4 CPU in `IDLE`)
- End-of-speech VAD (`webrtcvad` or RMS energy threshold) and empty-utterance skip
- Short-term multi-turn conversation buffer (`LLM_HISTORY_TURNS`)
- Environment-driven configuration via `.env`

### Local AI Server Stack (LAN Host)
- OpenAI-compatible STT endpoint (`POST /v1/audio/transcriptions` via `faster-whisper`)
- OpenAI-compatible LLM endpoint (`POST /v1/chat/completions` via `Ollama` / `vLLM` / `llama.cpp`) with spoken-friendly system prompt
- OpenAI-compatible TTS endpoint (`POST /v1/audio/speech` via `Kokoro-FastAPI` or `Piper TTS`)

## Scope

### In Scope (V1 MVP)
- Hardware BOM assembly, I2S wiring, and electrical safety verification (Stage 1)
- Pi 4 OS duplex I2S + ALSA `softvol` configuration and loopback audio tests (Stage 2)
- LAN-hosted STT, LLM, and TTS services with standalone `curl` verification (Stage 3)
- Python edge voice client, `.env` configuration contract, `systemd` auto-start, and E2E test matrix `E2E-01`..`E2E-08` (Stage 4)
- Mechanical enclosure assembly and post-enclosure acoustic re-verification

### Out of Scope (V1 MVP / Reserved for V2+)
- Cloud remote access outside the LAN
- Multi-room synchronized music playback
- Acoustic echo cancellation (AEC) barge-in during speaker playback
- Sentence-level LLM-to-TTS token streaming (<1.5 s perceived latency)
- WS2812B RGB LED status ring animations
- Custom wake-word ONNX model training
- LLM tool calling (timers, weather, Home Assistant / MQTT smart-home controls)

## Success Criteria

1. **Stage 1 & 2 Pass:** Pre-power voltage/pinout checks pass (`3.3V` to `INMP441`, `5V` to `MAX98357A`); `aplay -l`, `arecord -l`, `speaker-test`, and 1-meter `arecord`/`aplay` produce clean audio (`HW-01`..`HW-04`).
2. **Stage 3 Pass:** Standalone `curl` checks from Pi 4 to Local AI Server STT, LLM, and TTS endpoints return HTTP 200 within latency targets.
3. **Stage 4 Pass (`E2E-01`..`E2E-08`):**
   - Reliable wake-word pickup at 0.5 m and 2.0 m inside the enclosure (`>= 4/5` attempts).
   - Multi-turn context retained across consecutive wakes.
   - Zero self-triggering from speaker playback at 80% volume.
   - Graceful handling of silent utterances and Local AI Server offline/restart recovery.
   - Unattended boot startup within 45 s and 2-hour soak stability (`IDLE` CPU <30%, temp <65°C, zero memory leaks).
