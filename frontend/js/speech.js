// Wrapper de voz: STT (Web Speech API o MediaRecorder→Vosk) + TTS.
// Detecta automáticamente qué método usar según el navegador.
const Speech = (() => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const synth = window.speechSynthesis;
  const hasMediaRecorder = !!window.MediaRecorder && !!navigator.mediaDevices;

  const sttMode = SR ? "webspeech" : (hasMediaRecorder ? "recorder" : "none");

  // Estado externo: si el server tiene Vosk corriendo.
  // Se setea desde app.js llamando a API.sttStatus() al boot.
  let serverVoskAvailable = null;
  function setServerVoskAvailable(v) { serverVoskAvailable = !!v; }
  function getServerVoskAvailable() { return serverVoskAvailable; }

  // Devuelve true si el usuario PUEDE usar el micrófono según el modo + estado server.
  function canUseMic() {
    if (sttMode === "webspeech") return true;
    if (sttMode === "recorder") return serverVoskAvailable === true;
    return false;
  }

  // === Web Speech (Chrome / Edge) ===
  let recognition = null;
  let onResultCb = null;
  let onEndCb = null;
  let webSpeechActive = false;
  let webSpeechFinal = "";
  let webSpeechStart = 0;

  function initWebSpeech() {
    if (!SR) return false;
    recognition = new SR();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (e) => {
      let interim = "";
      webSpeechFinal = "";
      for (let i = 0; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) webSpeechFinal += t + " ";
        else interim += t;
      }
      if (onResultCb) onResultCb({ final: webSpeechFinal.trim(), interim: interim.trim() });
    };
    recognition.onerror = (e) => console.warn("STT error:", e.error);
    recognition.onend = () => {
      const duration = Math.round((Date.now() - webSpeechStart) / 1000);
      webSpeechActive = false;
      if (onEndCb) onEndCb({ transcript: webSpeechFinal.trim(), duration });
    };
    return true;
  }

  // === MediaRecorder fallback (Firefox y cualquier navegador sin Web Speech) ===
  let mediaStream = null;
  let mediaRecorder = null;
  let chunks = [];
  let recorderStart = 0;

  async function startRecorder() {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus") ? "audio/ogg;codecs=opus" : "");
    mediaRecorder = mime ? new MediaRecorder(mediaStream, { mimeType: mime }) : new MediaRecorder(mediaStream);
    chunks = [];
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
    mediaRecorder.start();
    recorderStart = Date.now();
  }

  async function stopRecorder() {
    return new Promise((resolve) => {
      if (!mediaRecorder || mediaRecorder.state === "inactive") {
        resolve(null);
        return;
      }
      mediaRecorder.onstop = async () => {
        const duration = Math.round((Date.now() - recorderStart) / 1000);
        const blob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
        mediaStream.getTracks().forEach(t => t.stop());
        resolve({ blob, duration });
      };
      mediaRecorder.stop();
    });
  }

  // === API pública ===
  async function start({ onResult, onEnd, onStatus }) {
    onResultCb = onResult;
    onEndCb = onEnd;

    if (sttMode === "webspeech") {
      if (!recognition && !initWebSpeech()) return false;
      webSpeechActive = true;
      webSpeechStart = Date.now();
      try { recognition.start(); return true; } catch (e) { console.warn(e); return false; }
    }

    if (sttMode === "recorder") {
      try {
        await startRecorder();
        if (onStatus) onStatus("Grabando... se transcribirá al soltar (Vosk).");
        return true;
      } catch (e) {
        alert("No pude acceder al micrófono: " + e.message);
        return false;
      }
    }

    alert("Tu navegador no permite grabar audio. Usá el modo Escribir.");
    return false;
  }

  async function stop({ uploadFn, onStatus } = {}) {
    if (sttMode === "webspeech") {
      if (recognition && webSpeechActive) {
        try { recognition.stop(); } catch {}
      }
      return;
    }

    if (sttMode === "recorder") {
      const result = await stopRecorder();
      if (!result) return;
      if (onStatus) onStatus("Transcribiendo... 🎧");
      let transcript = "";
      try {
        transcript = await uploadFn(result.blob);
      } catch (e) {
        console.warn(e);
        const msg = String(e.message || "");
        if (msg.includes("503") || msg.toLowerCase().includes("vosk")) {
          if (window.UI && UI.toast) {
            UI.toast(
              "Server transcription not configured. Use Chrome/Edge or the Write mode.",
              { type: "warn", duration: 5000 }
            );
          }
          if (onStatus) onStatus("⚠️ Transcription unavailable. Use Write mode.");
        } else {
          if (onStatus) onStatus("Couldn't transcribe. Try the Write mode.");
        }
      }
      if (onEndCb) onEndCb({ transcript: transcript || "", duration: result.duration });
    }
  }

  function speak(text, { rate = 0.9, pitch = 1 } = {}) {
    if (!synth) return;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US";
    u.rate = rate;
    u.pitch = pitch;
    const voices = synth.getVoices();
    const enVoice = voices.find(v => v.lang.startsWith("en"));
    if (enVoice) u.voice = enVoice;
    synth.speak(u);
  }

  return {
    mode: sttMode,           // "webspeech" | "recorder" | "none"
    supported: sttMode !== "none",
    isLive: () => sttMode === "webspeech",   // si muestra texto mientras hablás
    start,
    stop,
    speak,
    canUseMic,
    setServerVoskAvailable,
    getServerVoskAvailable,
  };
})();
