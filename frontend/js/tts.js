// TTS unificado: backend (Edge → Piper) con caché, fallback a speechSynthesis.
const TTS = (() => {
  const cache = new Map();   // key="voice|text" → blobUrl
  const CACHE_MAX = 40;      // tope: al superarlo se libera el blob más viejo
  let currentAudio = null;

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
    const best = voices.find(v => /google.*english/i.test(v.name))
              || voices.find(v => /natural|online|neural/i.test(v.name))
              || voices.find(v => v.lang.startsWith("en"));
    if (best) u.voice = best;
    window.speechSynthesis.speak(u);
  }

  async function speak(text, voiceOverride) {
    if (!text) return;
    stop();
    const voice = voiceOverride || preferredVoice;
    const key = `${voice}|${text}`;

    // Cache hit
    if (cache.has(key)) {
      currentAudio = new Audio(cache.get(key));
      currentAudio.play().catch(() => _fallbackBrowser(text));
      return;
    }

    try {
      const blob = await API.tts(text, voice);
      const url = URL.createObjectURL(blob);
      _cachePut(key, url);
      currentAudio = new Audio(url);
      await currentAudio.play();
    } catch (e) {
      console.warn("TTS backend no disponible, usando navegador:", e.message);
      _fallbackBrowser(text);
    }
  }

  return { speak, stop, setVoice, getVoice, getVoices, refreshStatus };
})();
