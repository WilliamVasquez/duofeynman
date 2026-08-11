// Wrapper de voz: STT (Web Speech API o MediaRecorder→server) + TTS.
// Detecta automáticamente qué método usar según el navegador.
const Speech = (() => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const synth = window.speechSynthesis;
  const hasMediaRecorder = !!window.MediaRecorder && !!navigator.mediaDevices;

  const sttMode = SR ? "webspeech" : (hasMediaRecorder ? "recorder" : "none");

  // Estado externo: si el server puede transcribir (Whisper o Vosk).
  // Se setea desde app.js llamando a API.sttStatus() al boot.
  let serverSttAvailable = null;
  function setServerSttAvailable(v) { serverSttAvailable = !!v; }
  function getServerSttAvailable() { return serverSttAvailable; }

  // Devuelve true si el usuario PUEDE usar el micrófono según el modo + estado server.
  function canUseMic() {
    if (sttMode === "webspeech") return true;
    if (sttMode === "recorder") return serverSttAvailable === true;
    return false;
  }

  // === Web Speech (Chrome / Edge) ===
  let recognition = null;
  let onResultCb = null;
  let onEndCb = null;
  let webSpeechActive = false;    // el usuario sigue queriendo grabar
  let webSpeechFinal = "";        // final acumulado ENTRE re-starts
  let webSpeechSession = "";      // final de la sesión de reconocimiento actual
  let webSpeechStart = 0;
  let webSpeechFinished = false;  // evita disparar onEnd dos veces
  let restartCount = 0;

  // Chrome corta el reconocimiento tras unos segundos de silencio aunque
  // continuous=true. Reiniciamos, pero con techo: si el mic muere en silencio
  // no queremos un loop infinito de start/end.
  const MAX_RESTARTS = 20;

  // Errores que NO tienen sentido reintentar (sin permiso, sin micrófono...).
  const FATAL_ERRORS = new Set([
    "not-allowed", "service-not-allowed", "audio-capture",
    "language-not-supported", "bad-grammar",
  ]);

  // --- Sesgo por vocabulario esperado ---
  // Chrome devuelve varias hipótesis de transcripción. Con el vocabulario del
  // ejercicio actual podemos elegir la que más se le parece, en vez de confiar
  // ciegamente en la primera. Ayuda mucho con acento no nativo.
  let expectedTerms = [];

  function _norm(s) {
    return String(s)
      .toLowerCase()
      .replace(/[^a-z0-9'\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function _escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function setExpectedVocab(terms) {
    expectedTerms = (Array.isArray(terms) ? terms : [])
      .filter(t => typeof t === "string")
      .map(_norm)
      .filter(Boolean);
  }

  // Elige la alternativa con más términos esperados presentes.
  // Empate => gana la primera, que es la de mayor confianza según Chrome.
  function _pickAlternative(result) {
    if (!result || result.length === 0) return "";
    if (result.length === 1 || expectedTerms.length === 0) return result[0].transcript;

    let best = result[0].transcript;
    let bestScore = -1;
    for (let i = 0; i < result.length; i++) {
      const text = result[i].transcript;
      const norm = _norm(text);
      let score = 0;
      for (const term of expectedTerms) {
        // Frases de varias palabras: substring. Palabra sola: límite de palabra,
        // para que "go" no matchee dentro de "going".
        const hit = term.includes(" ")
          ? norm.includes(term)
          : new RegExp(`\\b${_escapeRe(term)}\\b`).test(norm);
        if (hit) score++;
      }
      if (score > bestScore) { bestScore = score; best = text; }
    }
    return best;
  }

  function _finishWebSpeech() {
    if (webSpeechFinished) return;
    webSpeechFinished = true;
    const duration = Math.round((Date.now() - webSpeechStart) / 1000);
    if (onEndCb) onEndCb({ transcript: webSpeechFinal.trim(), duration });
  }

  function initWebSpeech() {
    if (!SR) return false;
    recognition = new SR();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.maxAlternatives = 3;

    recognition.onresult = (e) => {
      let interim = "";
      let sessionFinal = "";
      for (let i = 0; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) sessionFinal += _pickAlternative(res) + " ";
        else interim += res[0].transcript;
      }
      webSpeechSession = sessionFinal.trim();
      // Hubo audio real: el contador de re-starts no debe agotarse por hablar mucho.
      restartCount = 0;
      const full = (webSpeechFinal + " " + webSpeechSession).trim();
      if (onResultCb) onResultCb({ final: full, interim: interim.trim() });
    };

    recognition.onerror = (e) => {
      console.warn("STT error:", e.error);
      if (FATAL_ERRORS.has(e.error)) webSpeechActive = false;
    };

    recognition.onend = () => {
      // Consolidar lo transcripto en esta sesión antes de un posible re-start:
      // al reiniciar, e.results arranca vacío.
      if (webSpeechSession) {
        webSpeechFinal = (webSpeechFinal + " " + webSpeechSession).trim();
        webSpeechSession = "";
      }
      if (webSpeechActive && restartCount < MAX_RESTARTS) {
        restartCount++;
        setTimeout(() => {
          if (!webSpeechActive) { _finishWebSpeech(); return; }
          try {
            recognition.start();
          } catch (err) {
            console.warn("No se pudo reiniciar STT:", err);
            webSpeechActive = false;
            _finishWebSpeech();
          }
        }, 120);
        return;
      }
      webSpeechActive = false;
      _finishWebSpeech();
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
      webSpeechFinal = "";
      webSpeechSession = "";
      webSpeechFinished = false;
      restartCount = 0;
      webSpeechStart = Date.now();
      try {
        recognition.start();
        return true;
      } catch (e) {
        console.warn(e);
        webSpeechActive = false;
        return false;
      }
    }

    if (sttMode === "recorder") {
      try {
        await startRecorder();
        if (onStatus) onStatus("Grabando... se transcribirá al soltar.");
        return true;
      } catch (e) {
        // Toast, no alert(): alert() puede no funcionar en WebView Android
        UI.toast("No pude acceder al micrófono: " + e.message, { type: "error", duration: 5000 });
        return false;
      }
    }

    UI.toast("Tu navegador no permite grabar audio. Usá el modo Escribir.", { type: "warn", duration: 5000 });
    return false;
  }

  async function stop({ uploadFn, onStatus } = {}) {
    if (sttMode === "webspeech") {
      // Bajar la bandera PRIMERO: así onend no reinicia el reconocimiento.
      webSpeechActive = false;
      if (recognition) {
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
        if (msg.includes("503") || /vosk|whisper|stt/i.test(msg)) {
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
    setExpectedVocab,
    setServerSttAvailable,
    getServerSttAvailable,
  };
})();
