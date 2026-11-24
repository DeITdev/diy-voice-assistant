// DOM Elements
const statCpu = document.getElementById("statCpu");
const statRam = document.getElementById("statRam");
const statTemp = document.getElementById("statTemp");
const statDisk = document.getElementById("statDisk");
const activeInRamBadge = document.getElementById("activeInRamBadge");
const modelSelect = document.getElementById("modelSelect");
const chatLog = document.getElementById("chatLog");
const audioPlayer = document.getElementById("audioPlayer");
const btnRecord = document.getElementById("btnRecord");
const micHint = document.getElementById("micHint");
const textPrompt = document.getElementById("textPrompt");
const btnSend = document.getElementById("btnSend");
const checkSpeaker = document.getElementById("checkSpeaker");
const timingInfo = document.getElementById("timingInfo");
const btnPlayLastSpeaker = document.getElementById("btnPlayLastSpeaker");
const nativeAudioInput = document.getElementById("nativeAudioInput");

// Recording state
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// 1. Fetch System Telemetry
async function updateStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();

    statCpu.textContent = `${data.cpu_percent}%`;
    statRam.textContent = `${data.ram.free_gb} GB`;
    statTemp.textContent = `${data.cpu_temp} °C`;
    statDisk.textContent = `${data.disk.free_gb} GB`;

    activeInRamBadge.textContent = `RAM: ${data.active_in_ram}`;
    activeInRamBadge.style.color = data.active_in_ram === "Idle" ? "var(--text-muted)" : "var(--success)";
  } catch (err) {
    console.error("Gagal update status:", err);
  }
}

// Poll status every 4 seconds
setInterval(updateStatus, 4000);
updateStatus();

// 2. Model Selection Change
modelSelect.addEventListener("change", async () => {
  const selected = modelSelect.value;
  const formData = new FormData();
  formData.append("model_name", selected);
  try {
    await fetch("/api/model/select", {
      method: "POST",
      body: formData
    });
  } catch (err) {
    console.error("Gagal ganti model:", err);
  }
});

// Helper: Append Chat Message
function appendMessage(sender, text, meta = "") {
  const msgDiv = document.createElement("div");
  msgDiv.className = `msg ${sender}`;
  msgDiv.innerHTML = text.replace(/\n/g, "<br>");

  if (meta) {
    const metaDiv = document.createElement("div");
    metaDiv.className = "msg-meta";
    metaDiv.textContent = meta;
    msgDiv.appendChild(metaDiv);
  }

  chatLog.appendChild(msgDiv);
  chatLog.scrollTop = chatLog.scrollHeight;
  return msgDiv;
}

// 3. Send Text Message
async function sendTextMessage() {
  const text = textPrompt.value.trim();
  if (!text) return;

  textPrompt.value = "";
  appendMessage("user", text);

  const loadingMsg = appendMessage("bot", "<em>Sedang berpikir...</em>");
  timingInfo.textContent = "Memproses...";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: text,
        model: modelSelect.value,
        play_on_speaker: checkSpeaker.checked
      })
    });

    const data = await res.json();
    loadingMsg.innerHTML = data.reply;

    const meta = `⚡ Berpikir: ${data.elapsed_llm}s | 🔊 Suara: ${data.elapsed_tts}s`;
    const metaDiv = document.createElement("div");
    metaDiv.className = "msg-meta";
    metaDiv.textContent = meta;
    loadingMsg.appendChild(metaDiv);

    timingInfo.textContent = `Selesai (${data.elapsed_llm + data.elapsed_tts}s)`;

    if (data.audio_url) {
      audioPlayer.src = data.audio_url;
      audioPlayer.style.display = "block";
      audioPlayer.play().catch(() => {});
    }
  } catch (err) {
    loadingMsg.innerHTML = `<span style="color: var(--danger)">Terjadi kesalahan: ${err.message}</span>`;
  }
}

btnSend.addEventListener("click", sendTextMessage);
textPrompt.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendTextMessage();
});

// 4. Voice Recording via Phone/Browser Mic
btnRecord.addEventListener("click", async () => {
  // If getUserMedia is not supported (e.g. mobile HTTP), use native phone voice recorder
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    nativeAudioInput.click();
    return;
  }

  if (!isRecording) {
    // Start Recording
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunks.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        stream.getTracks().forEach(track => track.stop());
        await handleVoiceUpload(audioBlob);
      };

      mediaRecorder.start();
      isRecording = true;
      btnRecord.classList.add("recording");
      btnRecord.innerHTML = '<i class="fa-solid fa-stop"></i>';
      micHint.textContent = "Sedang Merekam... Klik untuk Kirim";
      micHint.style.color = "var(--danger)";
    } catch (err) {
      // Fallback: If getUserMedia permission was blocked, trigger native mobile recorder
      console.warn("getUserMedia failed, falling back to native file capture:", err);
      nativeAudioInput.click();
    }
  } else {
    // Stop Recording
    isRecording = false;
    btnRecord.classList.remove("recording");
    btnRecord.innerHTML = '<i class="fa-solid fa-microphone"></i>';
    micHint.textContent = "Memproses Suara...";
    micHint.style.color = "var(--text-muted)";
    mediaRecorder.stop();
  }
});

// Native Phone Audio Input fallback listener
nativeAudioInput.addEventListener("change", async () => {
  if (nativeAudioInput.files && nativeAudioInput.files[0]) {
    const file = nativeAudioInput.files[0];
    await handleVoiceUpload(file);
    nativeAudioInput.value = "";
  }
});

// 5. Handle Uploaded Voice Audio
async function handleVoiceUpload(audioBlob) {
  const userMsg = appendMessage("user", "🎙️ <em>[Mendengarkan suara Anda...]</em>");
  const loadingMsg = appendMessage("bot", "<em>Sedang memproses...</em>");
  timingInfo.textContent = "Transkripsi & Berpikir...";

  const formData = new FormData();
  formData.append("file", audioBlob, "user_voice.webm");
  formData.append("model", modelSelect.value);
  formData.append("play_on_speaker", checkSpeaker.checked);

  try {
    const res = await fetch("/api/voice-chat", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data.error) {
      userMsg.innerHTML = "🎙️ <em>(Suara tidak terdengar jelas)</em>";
      loadingMsg.innerHTML = `<span style="color: var(--danger)">${data.error}</span>`;
      timingInfo.textContent = "";
      micHint.textContent = "Klik untuk Mulai Bicara";
      return;
    }

    userMsg.innerHTML = `🎙️ "${data.transcribed_text}"`;
    loadingMsg.innerHTML = data.reply;

    const meta = `👂 STT: ${data.elapsed_stt}s | ⚡ LLM: ${data.elapsed_llm}s | 🔊 TTS: ${data.elapsed_tts}s`;
    const metaDiv = document.createElement("div");
    metaDiv.className = "msg-meta";
    metaDiv.textContent = meta;
    loadingMsg.appendChild(metaDiv);

    const total = (data.elapsed_stt + data.elapsed_llm + data.elapsed_tts).toFixed(2);
    timingInfo.textContent = `Total: ${total}s`;
    micHint.textContent = "Klik untuk Mulai Bicara";

    if (data.audio_url) {
      audioPlayer.src = data.audio_url;
      audioPlayer.style.display = "block";
      audioPlayer.play().catch(() => {});
    }
  } catch (err) {
    loadingMsg.innerHTML = `<span style="color: var(--danger)">Terjadi kesalahan: ${err.message}</span>`;
    micHint.textContent = "Klik untuk Mulai Bicara";
  }
}

// 6. Play on Pi Speaker Button
btnPlayLastSpeaker.addEventListener("click", async () => {
  try {
    await fetch("/api/play-speaker", { method: "POST" });
  } catch (err) {
    console.error("Gagal memutar di speaker:", err);
  }
});
