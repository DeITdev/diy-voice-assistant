# Product Requirements Document (PRD)
## Project: DIY Voice Assistant Speaker Integrated with Gen AI

| Field | Details |
| :--- | :--- |
| **Document Version** | 1.0 (Master Plan) |
| **Status** | Ready for Implementation |
| **Edge Hardware Platform** | Raspberry Pi 4 Model B (Raspberry Pi OS + SSH pre-configured) |
| **AI Infrastructure** | Self-Hosted Local AI Server (LAN-based STT, LLM, and TTS) |
| **Target Form Factor** | Compact, low-cost smart speaker (Google Nest-inspired aesthetic) |

---

## 1. Executive Summary & Product Overview

### 1.1 Vision
Build an affordable, privacy-first, hands-free smart speaker powered by a **Raspberry Pi 4 Model B** and raw **I2S digital audio modules**. Unlike commercial smart speakers tied to proprietary cloud ecosystems, all generative intelligence—Speech-to-Text (STT), Large Language Model (LLM) reasoning, and Text-to-Speech (TTS)—runs on our own **local AI server** over the local network (LAN).

### 1.2 Primary Objectives
1. **Low-Cost, Clean Audio Hardware:** Achieve clear voice capture and crisp speaker output using minimal, inexpensive I2S breakout boards (INMP441 + MAX98357A).
2. **100% Local AI Ownership:** Zero reliance on external cloud AI APIs (no Google Assistant, OpenAI, or subscription dependencies).
3. **Hands-Free "Nest-Like" Experience:** Always-on local wake-word detection, automatic end-of-speech detection, concise spoken answers, and automatic startup on power-on.
4. **Clean Aesthetic:** House the hardware in a compact, fabric-wrapped cylindrical or 3D-printed enclosure suitable for a desk or living room shelf.

### 1.3 Scope & Boundaries
* **In Scope (V1 MVP):** Hardware assembly, I2S duplex audio setup, local wake-word detection on Pi 4, HTTP/REST integration with local STT/LLM/TTS server, `systemd` auto-start daemon, and end-to-end verification.
* **Out of Scope (V1 MVP):** Cloud remote access outside LAN, multi-room synchronized music playback, acoustic echo cancellation (AEC) barge-in during playback, and smart home IoT device relays (reserved for V2/V3).

### 1.4 High-Level System Architecture

```text
+-------------------------------------------------------------------+
|               EDGE DEVICE: RASPBERRY PI 4 MODEL B                 |
|                                                                   |
|  [INMP441 I2S Mic] ---> ALSA (softvol boost) ---> openWakeWord    |
|                                                        |          |
|                                               (Wake Word Detected)|
|                                                        v          |
|  [MAX98357A Amp] <--- aplay <--- Audio Player     VAD Recorder    |
|         |                             ^                |          |
|  [2" 4-ohm Speaker]                   |                |          |
+---------------------------------------|----------------|----------+
                                        |                |
                          WAV Audio Out |   LAN (HTTP)   | WAV Audio In
                                        |                v
+---------------------------------------|---------------------------+
|                 LOCAL AI SERVER (PC / HOME SERVER)                |
|                                                                   |
|   [1. STT Service]  --->  [2. Local LLM]  --->  [3. Local TTS]    |
|   (Faster-Whisper)       (Ollama / vLLM)       (Kokoro / Piper)   |
+-------------------------------------------------------------------+
```

---

## 2. Phase 1: Hardware Specifications & Assembly

### 2.1 Pre-Existing Baseline
The following baseline is already prepared and excluded from the shopping list:
* **Raspberry Pi 4 Model B** with official 5V / 3A USB-C power supply and microSD card.
* **Raspberry Pi OS (64-bit)** installed, connected to local Wi-Fi/Ethernet, with **SSH enabled** and accessible.

### 2.2 Bill of Materials (BOM)

| Category | Component | Required Specs | Qty | Est. Cost (IDR) | Notes |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Audio Input** | INMP441 MEMS Microphone Module | I2S digital, 24-bit, omnidirectional, 3.3V logic | 1 | Rp 20.000 – 35.000 | Buy with pre-soldered pins if no soldering iron |
| **Audio Output** | MAX98357A Class-D Amp + DAC | I2S digital input, 3.2W at 4 ohms, 5V power | 1 | Rp 25.000 – 40.000 | Includes screw terminal for speaker wires |
| **Transducer** | Full-Range Mini Speaker | 2-inch (50mm), 4-ohm impedance, 3W rating | 1 | Rp 15.000 – 30.000 | Avoid 8-ohm tiny buzzers; 4-ohm 3W maximizes volume |
| **Wiring** | Dupont Jumper Wires (F/F & M/F) | 10cm–15cm length (keep short to avoid I2S noise) | 1 pack | Rp 10.000 – 15.000 | At least 15 wires needed |
| **Prototyping** | Mini Breadboard (170-point) | Solderless tie-points | 1 | Rp 8.000 – 15.000 | Used to split shared I2S clock pins cleanly |
| **Enclosure (Opt.)** | Cylinder Container + Grill Cloth | Cardboard/plastic tube + heather gray fabric | 1 | Rp 15.000 – 30.000 | Or 3D-printed smart speaker shell |
| **Visuals (Opt.)** | WS2812B RGB LED Ring | 8-LED or 12-LED ring, 5V | 1 | Rp 15.000 – 25.000 | Optional V2 Nest-style light ring |

### 2.3 Electrical & I2S Bus Design
Both the INMP441 microphone and MAX98357A amplifier operate on the Raspberry Pi 4's single **PCM / I2S bus**:
* **Shared Clocks (Pi Output to Both Boards):**
  * **Bit Clock (`BCLK` / `SCK`)** on **GPIO 18 (Physical Pin 12)**.
  * **Word Select / Left-Right Clock (`LRC` / `WS`)** on **GPIO 19 (Physical Pin 35)**.
* **Dedicated Data Lines:**
  * **Audio Data IN (`PCM_DIN`)** on **GPIO 20 (Physical Pin 38)** receives microphone data from `INMP441 SD`.
  * **Audio Data OUT (`PCM_DOUT`)** on **GPIO 21 (Physical Pin 40)** sends playback audio to `MAX98357A DIN`.

### 2.4 Complete GPIO Pinout Mapping

#### A. INMP441 Microphone Connections (6 Wires)
| INMP441 Pin | Pi 4 Physical Pin | Pi 4 BCM GPIO / Rail | Critical Requirement |
| :--- | :--- | :--- | :--- |
| **VDD** | **Pin 1** | **3.3V Power** | **CRITICAL: Strictly 3.3V. 5V permanently destroys the mic.** |
| **GND** | **Pin 6** | **Ground** | Common ground rail. |
| **L/R** | **Pin 6** (or Breadboard GND) | **Ground** | Must be tied to GND to select Left channel; floating causes static. |
| **SCK** | **Pin 12** *(Shared)* | **GPIO 18 (`PCM_CLK`)** | Shared via breadboard hub with MAX98357A `BCLK`. |
| **WS** | **Pin 35** *(Shared)* | **GPIO 19 (`PCM_FS`)** | Shared via breadboard hub with MAX98357A `LRC`. |
| **SD** | **Pin 38** | **GPIO 20 (`PCM_DIN`)** | Digital audio stream into the Pi. |

#### B. MAX98357A Amplifier Connections (5 Wires + 2 Speaker Leads)
| MAX98357A Pin | Pi 4 Physical Pin | Pi 4 BCM GPIO / Rail | Critical Requirement |
| :--- | :--- | :--- | :--- |
| **VIN** | **Pin 2** | **5V Power** | 5V provides full 3W Class-D speaker output. |
| **GND** | **Pin 14** | **Ground** | Common ground rail. |
| **BCLK** | **Pin 12** *(Shared)* | **GPIO 18 (`PCM_CLK`)** | Shared via breadboard hub with INMP441 `SCK`. |
| **LRC** | **Pin 35** *(Shared)* | **GPIO 19 (`PCM_FS`)** | Shared via breadboard hub with INMP441 `WS`. |
| **DIN** | **Pin 40** | **GPIO 21 (`PCM_DOUT`)** | Digital audio stream out of the Pi. |
| **GAIN** | *Unconnected* | — | Defaults to 9dB gain (optimal voice clarity without clipping). |
| **SD** | *Unconnected* | — | Defaults to active + mixed mono (Left+Right)/2 output. |
| **Speaker +/-** | *Screw Terminal* | — | Connect directly to the 2-inch 4-ohm 3W speaker wires. |

#### C. Visual 40-Pin Header Reference
Orient the Raspberry Pi 4 with the **USB/Ethernet ports facing downward**:

```text
          [ TOP EDGE OF PI 4 ]
  (Pin 1)  3.3V   [X] [X]  5V     (Pin 2)  <-- INMP441 VDD (1) | MAX98357A VIN (2)
  (Pin 3)  GPIO2  [ ] [ ]  5V     (Pin 4)
  (Pin 5)  GPIO3  [ ] [X]  GND    (Pin 6)  <-- INMP441 GND + L/R
  (Pin 7)  GPIO4  [ ] [ ]  GPIO14 (Pin 8)
  (Pin 9)  GND    [ ] [ ]  GPIO15 (Pin 10)
  (Pin 11) GPIO17 [ ] [X]  GPIO18 (Pin 12) <-- SHARED: INMP441 SCK + MAX98357A BCLK
  (Pin 13) GPIO27 [ ] [X]  GND    (Pin 14) <-- MAX98357A GND
     ...     ...            ...     ...
  (Pin 35) GPIO19 [X] [ ]  GPIO16 (Pin 36) <-- SHARED: INMP441 WS + MAX98357A LRC
  (Pin 37) GPIO26 [ ] [X]  GPIO20 (Pin 38) <-- INMP441 SD (Audio In)
  (Pin 39) GND    [ ] [X]  GPIO21 (Pin 40) <-- MAX98357A DIN (Audio Out)
        [ USB / ETHERNET PORTS ]
```

### 2.5 Step-by-Step Hardware Assembly Procedure
1. **Power Down Safely:** Over SSH, execute `sudo shutdown -h now`. Wait until the green activity LED stops flashing, then unplug the USB-C power cable.
2. **Prepare Modules:** Solder header pins onto the INMP441 and MAX98357A if unpopulated. Screw or solder the speaker leads into the MAX98357A output terminal.
3. **Create Shared Bus Rows on Breadboard:** Designate three separate rows on the mini breadboard:
   * Row A = **Common GND** (connect Pi Pin 6, Pi Pin 14, Mic GND, Mic L/R, Amp GND).
   * Row B = **Shared BCLK** (connect Pi Pin 12, Mic SCK, Amp BCLK).
   * Row C = **Shared LRCLK** (connect Pi Pin 35, Mic WS, Amp LRC).
4. **Connect Dedicated Power & Data Wires:**
   * Route Pi Pin 1 (3.3V) directly to Mic `VDD`.
   * Route Pi Pin 2 (5V) directly to Amp `VIN`.
   * Route Pi Pin 38 (GPIO 20) directly to Mic `SD`.
   * Route Pi Pin 40 (GPIO 21) directly to Amp `DIN`.
5. **Pre-Power Inspection:** Verify zero wire crossings between Pin 1 (3.3V) and Pin 2 (5V), confirm wire lengths are under 15 cm, and ensure the tiny gold acoustic pinhole on the INMP441 is unobstructed.

### 2.6 Mechanical Enclosure & Acoustic Requirements
* **Acoustic Separation:** Mount the INMP441 microphone at the **top** of the enclosure facing upward (with an exposed pinhole or behind breathable grill cloth) and mount the 2-inch speaker facing **forward** or separated by an internal foam/cardboard baffle to minimize direct chassis vibration into the mic.
* **Resonance Chamber:** Enclosing the back of the 2-inch speaker inside a rigid tube (cardboard cylinder, bamboo cup, or 3D-printed shell) significantly boosts vocal fullness compared to an open bare speaker.
* **Thermal Clearance:** Leave ventilation slots near the bottom/rear of the enclosure for the Raspberry Pi 4 CPU and cut an access slot for the USB-C power cable.

---

## 3. Phase 2: Software Architecture & Configuration

### 3.1 Part A: Raspberry Pi 4 OS & Audio Layer

#### Step 1: Enable Duplex I2S Driver
SSH into the Raspberry Pi 4 and edit the boot firmware configuration:

```bash
sudo nano /boot/firmware/config.txt
```

Make the following changes:
1. Disable onboard 3.5mm audio by commenting out `#dtparam=audio=on`.
2. Prevent HDMI from claiming Card 0 by appending `,noaudio` to `dtoverlay=vc4-kms-v3d,noaudio` (optional but recommended).
3. Add the duplex I2S driver at the bottom of the file (do **not** add other conflicting DAC overlays):

```ini
#dtparam=audio=on
dtparam=i2s=on
dtoverlay=googlevoicehat-soundcard
```

Save and reboot (`sudo reboot`).

#### Step 2: Configure ALSA Softvol Gain Boost (`/etc/asound.conf`)
Because the INMP441 outputs raw 24-bit audio inside a 32-bit frame (`S32_LE`) with no hardware gain knob, default recordings are too quiet for far-field wake words. Create `/etc/asound.conf`:

```bash
sudo nano /etc/asound.conf
```

Insert the following configuration (confirm card number via `arecord -l`; adjust `card 0` if listed as `card 1`):

```ini
pcm.!default {
    type asym
    playback.pcm "speaker_out"
    capture.pcm "mic_boosted"
}

pcm.speaker_out {
    type plug
    slave.pcm "hw:0,0"
}

pcm.mic_raw {
    type hw
    card 0
    device 0
    channels 2
    format S32_LE
    rate 16000
}

pcm.mic_boosted {
    type softvol
    slave.pcm "mic_raw"
    control {
        name "Mic Boost"
        card 0
    }
    min_dB -5.0
    max_dB 30.0
    resolution 6
}
```

Initialize and save the software boost:

```bash
arecord -d 1 /dev/null
alsamixer
```
*In `alsamixer`: Press `F6` to select `sndrpigooglevoi`, press `F4` for Capture, raise **Mic Boost** to 75–85%, exit with `Esc`, and persist via `sudo alsactl store`.*

---

### 3.2 Part B: Edge Voice Client (Python on Raspberry Pi 4)

#### Functional Requirements
| Module | Responsibility | Recommended Library / Tool |
| :--- | :--- | :--- |
| **Audio I/O** | Read 16 kHz 16-bit mono chunks from ALSA default mic; play WAV output | `sounddevice` (PortAudio) + `aplay` |
| **Wake Word Engine** | Continuous low-CPU local listening (~10–15% CPU on Pi 4) | `openWakeWord` (ONNX runtime) |
| **End-of-Speech (VAD)** | Record user query after wake word; stop cleanly on 1.2–1.5s silence | `webrtcvad` or RMS energy threshold |
| **Feedback Chimes** | Play short local `.wav` tones on wake detection and error | Local bundled WAV assets (`chime_wake.wav`, `chime_err.wav`) |
| **HTTP Client** | Post recorded audio to Local AI Server and receive spoken audio | `requests` or `httpx` |
| **Process Manager** | Auto-start on boot, auto-restart on crash, log rotation | `systemd` service |

#### State Machine Specification
1. **`IDLE`:** Continuously streams 80 ms (`1280` samples at 16 kHz) audio frames into `openWakeWord`.
2. **`LISTENING`:** Triggered when wake-word confidence exceeds threshold (default `0.5`). Plays `chime_wake.wav`, records speech up to `max_record_sec` (e.g., 10s), and stops early when silence persists for `1.5s`.
3. **`THINKING`:** Pauses microphone capture, sends WAV payload to Local AI Server, and waits for response (timeout: 25s).
4. **`SPEAKING`:** Plays returned WAV/PCM audio through MAX98357A via `aplay`. Microphone stays muted during playback to prevent acoustic feedback / self-triggering.
5. **`ERROR`:** On network timeout or HTTP 5xx, plays `chime_err.wav` (or pre-recorded offline message *"Sorry, I cannot reach the AI server right now"*) and returns safely to `IDLE`.

#### Environment Setup on Pi 4
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip portaudio19-dev alsa-utils
mkdir -p ~/diy-voice-assistant && cd ~/diy-voice-assistant
python3 -m venv venv
source venv/bin/activate
pip install openwakeword sounddevice numpy requests python-dotenv
```

---

### 3.3 Part C: Local AI Server Stack (Self-Hosted Gen AI Backend)

The Local AI Server runs on a separate desktop PC, laptop, or home server on the same LAN. Keeping STT, LLM, and TTS on the local server eliminates Pi 4 thermal throttling and keeps end-to-end latency fast.

#### Recommended Self-Hosted Services
1. **Speech-to-Text (STT):**
   * **Engine:** `faster-whisper` (e.g., `faster-whisper-server` / Speaches via Docker, or a lightweight FastAPI wrapper around `faster-whisper`).
   * **Model:** `small` or `medium` (or `large-v3-turbo` if GPU is available) for high accuracy across English and Indonesian.
   * **Endpoint:** `POST http://<SERVER_IP>:8000/v1/audio/transcriptions` (OpenAI-compatible multipart WAV upload).
2. **Generative AI LLM:**
   * **Engine:** **Ollama**, **vLLM**, or **llama.cpp server**.
   * **Model:** Fast conversational model (e.g., `llama3.2`, `qwen2.5:7b`, or your custom fine-tuned model).
   * **System Prompt Requirement:** Instruct the LLM to output **plain, spoken-friendly text only** (no Markdown bullets, no asterisks, no URLs, max 2–3 concise sentences unless asked for details) so the TTS sounds natural.
   * **Endpoint:** `POST http://<SERVER_IP>:11434/v1/chat/completions` (OpenAI-compatible JSON).
3. **Text-to-Speech (TTS):**
   * **Engine:** **Kokoro-FastAPI** (`ghcr.io/remsky/kokoro-fastapi`, Apache 2.0, natural voices) for GPU/modern CPU servers, **Piper TTS** (`OHF-Voice/piper1-gpl`) for ultra-fast CPU synthesis and multi-language support (including Indonesian voices), or your own custom TTS HTTP server.
   * **Endpoint:** `POST http://<SERVER_IP>:8880/v1/audio/speech` returning `audio/wav` (16 kHz or 22.05 kHz mono PCM).

---

## 4. Phase 3: End-to-End System Integration

### 4.1 Network & Configuration Contract
Assign a **static LAN IP** (via router DHCP reservation) to the Local AI Server (e.g., `192.168.1.50`). Configure all endpoints in a single `.env` file on the Raspberry Pi 4 so switching models or servers requires zero code edits:

```ini
# /home/pi/diy-voice-assistant/.env
WAKE_WORD_MODEL=hey_jarvis
WAKE_WORD_THRESHOLD=0.5
SAMPLE_RATE=16000
SILENCE_THRESHOLD=400
SILENCE_DURATION_SEC=1.5
MAX_RECORD_SEC=10

STT_URL=http://192.168.1.50:8000/v1/audio/transcriptions
STT_MODEL=Systran/faster-whisper-small

LLM_URL=http://192.168.1.50:11434/v1/chat/completions
LLM_MODEL=qwen2.5:7b
LLM_HISTORY_TURNS=4

TTS_URL=http://192.168.1.50:8880/v1/audio/speech
TTS_VOICE=af_heart
HTTP_TIMEOUT_SEC=25
```

### 4.2 End-to-End Data Flow Specification

| Step | Actor | Action & Data Format |
| :---: | :--- | :--- |
| **1** | User | Speaks wake word (*"Hey Jarvis"*) followed by a query (*"What causes thunder?"*). |
| **2** | Pi 4 Edge Client | `openWakeWord` detects trigger; plays `chime_wake.wav`; VAD records 16 kHz 16-bit mono WAV buffer until 1.5s silence. |
| **3** | Pi 4 to Local Server (STT) | Sends `multipart/form-data` (`file=query.wav`) to `STT_URL`. Receives JSON `{"text": "What causes thunder?"}`. |
| **4** | Pi 4 to Local Server (LLM) | Appends user text to rolling short-term conversation buffer (`LLM_HISTORY_TURNS`), posts JSON to `LLM_URL`. Receives concise plain-text reply. |
| **5** | Pi 4 to Local Server (TTS) | Posts `{"input": "<reply>", "voice": "<TTS_VOICE>", "response_format": "wav"}` to `TTS_URL`. Receives binary WAV audio stream. |
| **6** | Pi 4 Edge Client | Writes/pipes WAV to `aplay -q`, waits until playback completes, flushes mic buffer, resets wake-word state, and returns to `IDLE`. |

### 4.3 Latency Budget Target
End-to-end response latency is defined from the moment the user stops speaking until the first audio plays out of the speaker:

$$T_{\text{total}} = T_{\text{VAD}} + T_{\text{STT}} + T_{\text{LLM}} + T_{\text{TTS}} + T_{\text{net}}$$

| Stage | Target (GPU Server) | Target (CPU-Only Server) | Optimization Lever |
| :--- | :---: | :---: | :--- |
| **End-of-Speech VAD ($T_{\text{VAD}}$)** | 1.2 s | 1.5 s | Tune silence duration tightly |
| **Speech-to-Text ($T_{\text{STT}}$)** | 0.3 s | 1.0 s | Use `int8` quantization & `beam_size=1` |
| **LLM Generation ($T_{\text{LLM}}$)** | 0.6 s | 2.0 s | Enforce 1–2 sentence system prompt |
| **TTS Synthesis ($T_{\text{TTS}}$)** | 0.3 s | 0.8 s | Use Piper/Kokoro; upgrade to sentence streaming in V2 |
| **LAN Transfer ($T_{\text{net}}$)** | 0.1 s | 0.1 s | Keep Pi 4 on 5 GHz Wi-Fi or Ethernet |
| **Total Turnaround ($T_{\text{total}}$)** | **~2.5 s** | **~5.4 s** | — |

### 4.4 Headless Auto-Start Daemon (`systemd`)
Create `/etc/systemd/system/voice-assistant.service` so the speaker boots automatically like a commercial appliance:

```ini
[Unit]
Description=DIY Gen AI Voice Assistant Client
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/diy-voice-assistant
ExecStart=/home/pi/diy-voice-assistant/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and manage the service over SSH:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now voice-assistant.service
journalctl -u voice-assistant.service -f
```

---

## 5. Phase 4: Testing, Verification & Acceptance Plan

Execute testing strictly in stages. Do not advance to the next stage until the current stage passes.

### 5.1 Stage 1: Hardware & Electrical Checklist (Pre-Power)
* [ ] **Voltage Safety:** INMP441 `VDD` is confirmed on Physical Pin 1 (3.3V), NOT Pin 2 (5V).
* [ ] **Amp Power:** MAX98357A `VIN` is confirmed on Physical Pin 2 (5V).
* [ ] **Channel Select:** INMP441 `L/R` is tied to Ground.
* [ ] **Shared Clocks:** Pin 12 (GPIO 18) connects to both `SCK` and `BCLK`; Pin 35 (GPIO 19) connects to both `WS` and `LRC`.
* [ ] **Data Direction:** Pin 38 (GPIO 20) goes to Mic `SD`; Pin 40 (GPIO 21) goes to Amp `DIN`.
* [ ] **Short Check:** No loose wire strands bridging adjacent GPIO pins.

### 5.2 Stage 2: Low-Level OS & ALSA Audio Unit Tests
Run the following commands over SSH after rebooting with the `googlevoicehat-soundcard` overlay:

| Test ID | Command | Expected Pass Result |
| :--- | :--- | :--- |
| **HW-01** | `aplay -l` | Lists `sndrpigooglevoi` as a playback card. |
| **HW-02** | `arecord -l` | Lists `sndrpigooglevoi` as a capture card. |
| **HW-03** | `speaker-test -c2 -twav -l1` | Clearly audible *"Front Left, Front Right"* test audio from the 2-inch speaker with no severe crackling. |
| **HW-04** | `arecord -D default -c1 -r 16000 -f S16_LE -d 5 test.wav && aplay test.wav` | Records 5 seconds of speech from 1 meter away and plays it back clearly and loudly without robotic distortion. |

### 5.3 Stage 3: Local AI Server Standalone API Tests (From Pi 4 via SSH)
Verify LAN reachability and payload contracts before running the full Python voice loop:

1. **STT Verification:**
   ```bash
   curl -X POST http://192.168.1.50:8000/v1/audio/transcriptions \
     -F file="@test.wav" -F model="Systran/faster-whisper-small"
   ```
   *Pass:* Returns HTTP 200 with accurate text matching `test.wav`.
2. **LLM Verification:**
   ```bash
   curl -X POST http://192.168.1.50:11434/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"qwen2.5:7b","messages":[{"role":"user","content":"Say hello in five words."}]}'
   ```
   *Pass:* Returns HTTP 200 JSON with concise response under 3 seconds.
3. **TTS Verification:**
   ```bash
   curl -X POST http://192.168.1.50:8880/v1/audio/speech \
     -H "Content-Type: application/json" \
     -d '{"input":"System audio integration successful.","voice":"af_heart","response_format":"wav"}' \
     --output tts_test.wav && aplay tts_test.wav
   ```
   *Pass:* Plays clean synthesized voice through the MAX98357A speaker.

### 5.4 Stage 4: End-to-End Integration Test Matrix

| Test ID | Scenario | Steps | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **E2E-01** | **Close-Range Wake & Q&A** | Say wake word at 0.5m, ask a factual question. | Chime plays within 0.5s; accurate spoken answer delivered within latency target. |
| **E2E-02** | **Room-Distance Pickup** | Repeat E2E-01 at 2.0m distance inside the enclosure. | Wake word triggers reliably (at least 4 out of 5 attempts); STT transcribes accurately. |
| **E2E-03** | **Multi-Turn Context** | Ask *"Who invented Linux?"*, wait for reply, then wake and ask *"Where was he born?"* | LLM remembers previous turn context and answers correctly. |
| **E2E-04** | **Self-Trigger / Echo Prevention** | Trigger a 10-second spoken answer at 80% speaker volume. | Mic does not re-trigger wake word from its own speaker output. |
| **E2E-05** | **Empty / Silent Utterance** | Say wake word, then stay completely silent for 3 seconds. | Recorder times out cleanly, skips LLM/TTS call, returns to `IDLE` without crashing. |
| **E2E-06** | **Local Server Offline Recovery** | Stop local AI server, trigger wake word and ask a question, then restart server. | Plays offline error chime/message; next query succeeds automatically once server returns. |
| **E2E-07** | **Power Cycle & Headless Boot** | Unplug Pi 4 power, plug back in, wait 45 seconds without SSHing in. | `voice-assistant.service` starts automatically and responds to wake word. |
| **E2E-08** | **Thermal & Soak Stability** | Leave running in `IDLE` for 2 hours, perform 10 queries. | Pi 4 CPU stays under 30% in `IDLE`, temp under 65°C (`vcgencmd measure_temp`), zero memory leaks. |

### 5.5 Quick Troubleshooting Reference
* **No sound card listed in `aplay -l`:** Check `/boot/firmware/config.txt` for typos (`googlevoicehat-soundcard`) and ensure no second audio overlay is enabled.
* **Mic records pure silence or static:** Confirm INMP441 `L/R` is tied to GND, `SD` is on Pin 38 (not Pin 40), and `Mic Boost` is raised in `alsamixer`.
* **Speaker pops or distorts at high volume:** Ensure MAX98357A `VIN` is powered by 5V (Pin 2) with a proper 3A Pi power supply, and keep `GAIN` floating (9dB).
* **Wake word triggers randomly:** Increase `WAKE_WORD_THRESHOLD` from `0.5` to `0.65` or lower `Mic Boost` slightly in `alsamixer`.

---

## 6. Project Roadmap & Future Iterations

* **Milestone 1 (Hardware Bench Proof):** Purchase BOM, complete breadboard wiring, pass Stage 1 & Stage 2 audio loopback tests.
* **Milestone 2 (Local Server Ready):** Deploy local STT, LLM, and TTS endpoints on LAN server and pass Stage 3 `curl` tests.
* **Milestone 3 (MVP End-to-End):** Run Python voice client on Pi 4, configure `systemd`, and pass Stage 4 test matrix.
* **Milestone 4 (Nest-Style Enclosure):** Solder final compact wiring or prototype board, mount inside fabric-wrapped cylinder or 3D-printed enclosure, and re-verify E2E-02 and E2E-04.
* **Future Enhancements (V2+):**
  * **Sentence-Level Streaming:** Stream LLM tokens directly into TTS sentence-by-sentence to cut perceived latency under 1.5 seconds.
  * **WS2812B LED Ring:** Add Nest-style pulsing animations mapped to `IDLE`, `LISTENING`, `THINKING`, and `SPEAKING`.
  * **Custom Wake Word:** Train a personalized wake word ONNX model via `openWakeWord`.
  * **Tool Calling:** Give the local LLM function-calling tools (timers, weather, local smart-home MQTT/Home Assistant controls).