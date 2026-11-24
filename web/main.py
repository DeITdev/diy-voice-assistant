import os
import sys
import time
import json
import wave
import tempfile
import subprocess
import urllib.request
from typing import Optional

import psutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from piper import PiperVoice
from faster_whisper import WhisperModel

app = FastAPI(title="DIY Voice Assistant Web Management")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
AUDIO_OUTPUT_DIR = os.path.join(BASE_DIR, "audio_cache")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

# Model paths
PIPER_MODEL_PATH = "/home/nova/models/piper/id_ID-news_tts-medium.onnx"
PIPER_CONFIG_PATH = "/home/nova/models/piper/id_ID-news_tts-medium.onnx.json"
WHISPER_DIR = "/home/nova/models/whisper"

# State
CURRENT_MODEL = "qwen2.5:1.5b"
LATEST_AUDIO_PATH = os.path.join(AUDIO_OUTPUT_DIR, "latest_response.wav")

# Lazy-loaded Whisper & Piper
_whisper_model = None
_piper_voice = None

def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root=WHISPER_DIR)
    return _whisper_model

def get_piper():
    global _piper_voice
    if _piper_voice is None:
        _piper_voice = PiperVoice.load(PIPER_MODEL_PATH, config_path=PIPER_CONFIG_PATH)
    return _piper_voice

def query_ollama(prompt: str, model: str) -> str:
    system_prompt = (
        "Kamu adalah asisten suara pintar berbahasa Indonesia di Raspberry Pi. "
        "Jawab pertanyaan berikut secara singkat, padat, dan ramah dalam 1 atau 2 kalimat saja. "
        "Jangan gunakan simbol aneh, tabel, atau markdown bintang karena jawabanmu akan langsung diucapkan lewat suara.\n\n"
        f"Pertanyaan: {prompt}\nJawaban:"
    )
    req_data = json.dumps({
        "model": model,
        "prompt": system_prompt,
        "stream": False
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "").strip()

def synthesize_audio(text: str, output_path: str):
    voice = get_piper()
    with wave.open(output_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

def get_cpu_temp() -> float:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        return 0.0

class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    play_on_speaker: Optional[bool] = False

@app.get("/api/status")
def get_status():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu_percent = psutil.cpu_percent(interval=None)
    temp = get_cpu_temp()

    # Get ollama models
    models = ["qwen2.5:1.5b", "gemma2-lokal:latest"]
    active_in_ram = "Idle"
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
    except Exception:
        pass

    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/ps")
        with urllib.request.urlopen(req, timeout=2) as resp:
            ps_data = json.loads(resp.read().decode("utf-8"))
            running = ps_data.get("models", [])
            if running:
                active_in_ram = running[0].get("name", "Idle")
    except Exception:
        pass

    return {
        "current_model": CURRENT_MODEL,
        "available_models": models,
        "active_in_ram": active_in_ram,
        "cpu_percent": cpu_percent,
        "cpu_temp": temp,
        "ram": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "free_gb": round(mem.available / (1024**3), 2),
            "percent": mem.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent
        }
    }

@app.post("/api/model/select")
def set_model(model_name: str = Form(...)):
    global CURRENT_MODEL
    CURRENT_MODEL = model_name
    return {"status": "ok", "current_model": CURRENT_MODEL}

@app.post("/api/chat")
def chat_text(req: ChatRequest):
    model_to_use = req.model or CURRENT_MODEL
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt tidak boleh kosong")

    t0 = time.time()
    try:
        reply = query_ollama(prompt, model_to_use)
    except Exception as e:
        reply = f"Maaf, gagal memanggil model {model_to_use}: {e}"
    t_llm = round(time.time() - t0, 2)

    t0 = time.time()
    try:
        synthesize_audio(reply, LATEST_AUDIO_PATH)
        has_audio = True
    except Exception as e:
        has_audio = False
    t_tts = round(time.time() - t0, 2)

    if req.play_on_speaker and has_audio:
        try:
            subprocess.Popen(["aplay", "-q", "-D", "plughw:2,0", LATEST_AUDIO_PATH])
        except Exception:
            subprocess.Popen(["aplay", "-q", LATEST_AUDIO_PATH])

    return {
        "model": model_to_use,
        "prompt": prompt,
        "reply": reply,
        "elapsed_llm": t_llm,
        "elapsed_tts": t_tts,
        "audio_url": f"/api/audio/latest.wav?t={int(time.time())}" if has_audio else None
    }

@app.post("/api/voice-chat")
async def chat_voice(file: UploadFile = File(...), model: Optional[str] = Form(None), play_on_speaker: Optional[bool] = Form(False)):
    model_to_use = model or CURRENT_MODEL

    # Save uploaded audio to temp file
    suffix = os.path.splitext(file.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    t0 = time.time()
    try:
        whisper = get_whisper()
        segments, info = whisper.transcribe(tmp_path, language="id")
        transcribed_text = " ".join([s.text for s in segments]).strip()
    except Exception as e:
        transcribed_text = ""
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    t_stt = round(time.time() - t0, 2)

    if not transcribed_text:
        return {
            "error": "Suara tidak terdengar jelas atau kosong. Silakan coba lagi.",
            "elapsed_stt": t_stt
        }

    # Query LLM
    t0 = time.time()
    reply = query_ollama(transcribed_text, model_to_use)
    t_llm = round(time.time() - t0, 2)

    # Synthesize TTS
    t0 = time.time()
    synthesize_audio(reply, LATEST_AUDIO_PATH)
    t_tts = round(time.time() - t0, 2)

    if play_on_speaker:
        try:
            subprocess.Popen(["aplay", "-q", "-D", "plughw:2,0", LATEST_AUDIO_PATH])
        except Exception:
            subprocess.Popen(["aplay", "-q", LATEST_AUDIO_PATH])

    return {
        "model": model_to_use,
        "transcribed_text": transcribed_text,
        "reply": reply,
        "elapsed_stt": t_stt,
        "elapsed_llm": t_llm,
        "elapsed_tts": t_tts,
        "audio_url": f"/api/audio/latest.wav?t={int(time.time())}"
    }

@app.get("/api/audio/latest.wav")
def get_latest_audio():
    if not os.path.exists(LATEST_AUDIO_PATH):
        raise HTTPException(status_code=404, detail="Audio belum dibuat")
    return FileResponse(LATEST_AUDIO_PATH, media_type="audio/wav")

@app.post("/api/play-speaker")
def play_speaker():
    if not os.path.exists(LATEST_AUDIO_PATH):
        raise HTTPException(status_code=404, detail="Audio belum dibuat")
    try:
        subprocess.Popen(["aplay", "-q", "-D", "plughw:2,0", LATEST_AUDIO_PATH])
    except Exception:
        subprocess.Popen(["aplay", "-q", LATEST_AUDIO_PATH])
    return {"status": "playing"}

# Mount frontend static files
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
