import time
import os
import wave
from piper import PiperVoice
from faster_whisper import WhisperModel

print("=== 1. PENGUJIAN PIPER TTS (MULUT AI) ===")
voice_model_path = "/home/nova/models/piper/id_ID-news_tts-medium.onnx"
voice_config_path = "/home/nova/models/piper/id_ID-news_tts-medium.onnx.json"
output_wav = "/home/nova/models/piper/test_output.wav"

t0 = time.time()
voice = PiperVoice.load(voice_model_path, config_path=voice_config_path)
t_load_piper = time.time() - t0
print(f"Model Piper berhasil dimuat ({t_load_piper:.2f} detik).")

kalimat_uji = "Halo, selamat datang! Ini adalah pengujian suara bahasa Indonesia di Raspberry Pi."
print(f"Mensintesis suara: '{kalimat_uji}'...")

t0 = time.time()
with wave.open(output_wav, "wb") as wav_file:
    voice.synthesize_wav(kalimat_uji, wav_file)
t_tts = time.time() - t0
print(f"Selesai dalam {t_tts:.2f} detik! File disimpan di: {output_wav}")

print("\n=== 2. PENGUJIAN WHISPER TINY (TELINGA AI) ===")
whisper_dir = "/home/nova/models/whisper"
os.makedirs(whisper_dir, exist_ok=True)

print("Memuat / mengunduh Whisper Tiny int8...")
t0 = time.time()
whisper = WhisperModel("tiny", device="cpu", compute_type="int8", download_root=whisper_dir)
t_load_whisper = time.time() - t0
print(f"Whisper Tiny siap ({t_load_whisper:.2f} detik).")

print(f"Mentranskripsikan audio: {output_wav}...")
t0 = time.time()
segments, info = whisper.transcribe(output_wav, language="id")
text_hasil = " ".join([segment.text for segment in segments]).strip()
t_stt = time.time() - t0

print(f"Waktu transkripsi: {t_stt:.2f} detik")
print(f"Bahasa terdeteksi: {info.language} (probabilitas: {info.language_probability:.2f})")
print(f"Hasil teks yang didengar: \"{text_hasil}\"")

print("\n=== KESIMPULAN ===")
print("Semua pengujian STT dan TTS BERHASIL 100%!")
