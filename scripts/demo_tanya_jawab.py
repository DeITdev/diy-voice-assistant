import sys
import time
import wave
import json
import urllib.request
import subprocess
import argparse
from piper import PiperVoice

def main():
    parser = argparse.ArgumentParser(description="Demo Tanya Jawab Asisten Suara Lokal")
    parser.add_argument("pertanyaan", nargs="*", default=["Halo, perkenalkan siapa kamu dan apa fungsi kamu?"], help="Pertanyaan untuk asisten")
    parser.add_argument("--model", default="qwen2.5:1.5b", help="Model Ollama yang digunakan (default: qwen2.5:1.5b atau gemma2-lokal)")
    args = parser.parse_args()

    pertanyaan_teks = " ".join(args.pertanyaan)
    model_ai = args.model

    print("=" * 60)
    print("  ASISTEN SUARA LOKAL RASPBERRY PI 4 (DEMO TANYA JAWAB)")
    print("=" * 60)
    print(f"[Model Otak AI]: {model_ai}")
    print(f"[Pengguna]: \"{pertanyaan_teks}\"")

    # 1. Panggil Otak AI via Ollama
    print(f"\n[Otak AI ({model_ai})]: Sedang berpikir & menyusun jawaban...")
    t0 = time.time()
    prompt = (
        "Kamu adalah asisten suara pintar berbahasa Indonesia di Raspberry Pi. "
        "Jawab pertanyaan berikut secara singkat, padat, dan ramah dalam 1 kalimat saja. "
        "Jangan gunakan simbol bintang atau markdown karena jawabanmu akan diucapkan lewat suara.\n\n"
        f"Pertanyaan: {pertanyaan_teks}\nJawaban:"
    )
    req_data = json.dumps({
        "model": model_ai,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=req_data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            jawaban_teks = data.get("response", "").strip()
    except Exception as e:
        jawaban_teks = f"Gagal menghubungi Ollama: {e}"
    t_llm = time.time() - t0

    print(f"[Otak AI Menjawab]: \"{jawaban_teks}\"")
    print(f"(Selesai berpikir dalam {t_llm:.2f} detik)")

    # 2. Panggil Mulut AI (Piper TTS)
    print("\n[Mulut AI (Piper)]: Mengubah jawaban menjadi suara manusia...")
    voice_model_path = "/home/nova/models/piper/id_ID-news_tts-medium.onnx"
    voice_config_path = "/home/nova/models/piper/id_ID-news_tts-medium.onnx.json"
    output_wav = "/home/nova/diy-voice-assistant/jawaban_asisten.wav"

    t0 = time.time()
    voice = PiperVoice.load(voice_model_path, config_path=voice_config_path)
    with wave.open(output_wav, "wb") as wav_file:
        voice.synthesize_wav(jawaban_teks, wav_file)
    t_tts = time.time() - t0

    print(f"(Suara selesai dibuat dalam {t_tts:.2f} detik)")
    print(f"File suara disimpan di: {output_wav}")

    # 3. Putar ke Audio Jack 3.5mm Pi 4
    print("\n[Speaker]: Memutar suara ke audio jack 3.5mm Raspberry Pi...")
    res = subprocess.run(["aplay", "-q", "-D", "plughw:2,0", output_wav], capture_output=True)
    if res.returncode != 0:
        subprocess.run(["aplay", "-q", output_wav], capture_output=True)

    print("\n" + "=" * 60)
    print(" Selesai! Hubungkan earphone/speaker ke jack 3.5mm untuk dengar.")
    print("=" * 60)

if __name__ == "__main__":
    main()
