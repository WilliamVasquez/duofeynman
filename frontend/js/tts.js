// TTS unificado: backend (Edge → Piper) con caché, fallback a speechSynthesis.
const TTS = (() => {
  const cache = new Map();   // key="voice|text" → blobUrl
  const CACHE_MAX = 40;      // tope: al superarlo se libera el blob más viejo
  let currentAudio = null;
  let playbackVersion = 0;

  function _cachePut(key, url) {
    if (cache.size >= CACHE_MAX) {
      const oldestKey = cache.keys().next().value;
      URL.revokeObjectURL(cache.get(oldestKey));
      cache.delete(oldestKey);
    }
    cache.set(key, url);
  }
  let preferredVoice = Store.get("duofeynman_voice") || "aria";
  let availableVoices = ["aria", "jenny", "guy", "davis", "sonia", "ryan", "natasha"];

  // Nivel del usuario: el backend lo usa para la velocidad de habla, así que
  // entra en la clave del cache. Si no, al subir de nivel seguiríamos oyendo
  // el audio viejo (más lento) mientras dure la sesión.
  let level = "";
  function setLevel(l) { level = l || ""; }

  function setVoice(v) {
    preferredVoice = v;
    Store.set("duofeynman_voice", v);
  }
  function getVoice() { return preferredVoice; }
  function getVoices() { return availableVoices; }

  async function refreshStatus() {
    try {
      const s = await API.ttsStatus();
      if (s.voices && s.voices.length) availableVoices = s.voices;
      return s;
    } catch {
      return null;
    }
  }

  function stop() {
    playbackVersion++;
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio = null;
    }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }

  function _fallbackBrowser(text) {
    if (!window.speechSynthesis) return;
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US";
    u.rate = 0.9;
    const voices = window.speechSynthesis.getVoices();
    // Preferir voces que parezcan más naturales (Google, "Natural", "Online")
    const english = voices.filter(v => v.lang.startsWith("en"));
    const best = english.find(v => /google|natural|online|neural/i.test(v.name)) || english[0];
    if (best) u.voice = best;
    window.speechSynthesis.speak(u);
  }

  async function speak(text, voiceOverride) {
    if (!text) return;
    stop();
    const version = playbackVersion;
    const voice = voiceOverride || preferredVoice;
    const key = `${voice}|${level}|${text}`;

    // Cache hit
    if (cache.has(key)) {
      currentAudio = new Audio(cache.get(key));
      currentAudio.play().catch(() => { if (version === playbackVersion) _fallbackBrowser(text); });
      return;
    }

    let url = null;
    try {
      const blob = await API.tts(text, voice, level);
      if (version !== playbackVersion) return;
      url = URL.createObjectURL(blob);
      currentAudio = new Audio(url);
      await currentAudio.play();
      if (version !== playbackVersion) { URL.revokeObjectURL(url); return; }
      // Cachear recién DESPUÉS de que play() funcione: si falla, revocamos
      // el blob URL (sino queda huérfano en memoria — leak progresivo).
      _cachePut(key, url);
    } catch (e) {
      if (url && !cache.has(key)) URL.revokeObjectURL(url);
      console.warn("TTS backend no disponible, usando navegador:", e.message);
      if (version === playbackVersion) _fallbackBrowser(text);
    }
  }

  return { speak, stop, setVoice, getVoice, getVoices, setLevel, refreshStatus };
})();
