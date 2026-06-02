// Modo Dictado: el backend nos da una frase + texto para TTS; el usuario escribe.
const Dictation = (() => {
  let currentTarget = null;
  let currentTopic = null;
  let slowMode = false;

  async function load() {
    const hintEl = document.getElementById("dictation-hint");
    hintEl.textContent = "Cargando frase...";
    document.getElementById("dict-input").value = "";
    document.getElementById("dict-words").textContent = "0";
    document.getElementById("dict-feedback").classList.add("hidden");
    slowMode = false;
    try {
      const data = await API.dictationNext();
      currentTarget = data.tts_text;
      currentTopic = data.topic_id;
      hintEl.textContent = `Pista: tema sobre "${data.hint_es}" — ${data.word_count} palabras.`;
      // Auto-play
      setTimeout(() => play(), 400);
    } catch (err) {
      hintEl.textContent = "Error: " + err.message;
    }
  }

  function play() {
    if (!currentTarget) return;
    TTS.speak(currentTarget);
  }

  function playSlow() {
    if (!currentTarget) return;
    slowMode = true;
    // El TTS del backend ya viene con rate=-10%. Para "más lento" usamos
    // el speechSynthesis del navegador con rate bajo (siempre funciona).
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(currentTarget);
      u.lang = "en-US";
      u.rate = 0.6;
      const voices = window.speechSynthesis.getVoices();
      const v = voices.find(x => x.lang.startsWith("en"));
      if (v) u.voice = v;
      window.speechSynthesis.speak(u);
    } else {
      TTS.speak(currentTarget);
    }
  }

  async function check() {
    const input = document.getElementById("dict-input").value.trim();
    if (input.length < 1 || !currentTarget) return;
    try {
      const res = await API.dictationCheck({
        topic_id: currentTopic,
        user_input: input,
        target_sentence: currentTarget,
      });
      _renderFeedback(res);
    } catch (err) {
      alert("Error: " + err.message);
    }
  }

  function _renderFeedback(r) {
    const fb = document.getElementById("dict-feedback");
    fb.classList.remove("hidden");
    document.getElementById("dict-score-fill").style.width = `${Math.round(r.score * 100)}%`;
    document.getElementById("dict-encouragement").textContent = r.feedback_es;

    const diff = document.getElementById("dict-diff");
    let html = `
      <h4>Frase correcta:</h4>
      <p style="background:#ecfdf5;padding:10px;border-radius:8px;font-style:italic">${r.target}</p>
      <h4 style="margin-top:12px">Tu respuesta:</h4>
      <p style="background:#fef3c7;padding:10px;border-radius:8px">${r.you_wrote}</p>
    `;
    if (r.word_diff.missing && r.word_diff.missing.length) {
      html += `<p style="margin-top:10px"><strong>Te faltaron:</strong> <span style="color:#ef4444">${r.word_diff.missing.join(", ")}</span></p>`;
    }
    if (r.word_diff.extra && r.word_diff.extra.length) {
      html += `<p><strong>De más:</strong> <span style="color:#f59e0b">${r.word_diff.extra.join(", ")}</span></p>`;
    }
    diff.innerHTML = html;
  }

  function init() {
    document.getElementById("btn-dict-play").onclick = play;
    document.getElementById("btn-dict-slow").onclick = playSlow;
    document.getElementById("btn-dict-check").onclick = check;
    document.getElementById("btn-dict-next").onclick = load;
    document.getElementById("dict-input").addEventListener("input", (e) => {
      const c = (e.target.value.trim().match(/\S+/g) || []).length;
      document.getElementById("dict-words").textContent = c;
    });
  }

  return { load, init };
})();
