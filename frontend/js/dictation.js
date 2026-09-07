// Dictado: el servidor conserva la respuesta y sirve el audio por ID.
const Dictation = (() => {
  let exerciseId = null;
  let currentAudio = null;
  let audioUrl = null;
  let version = 0;
  let audioVersion = 0;

  function stop() {
    version++;
    audioVersion++;
    if (currentAudio) currentAudio.pause();
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    currentAudio = null;
    audioUrl = null;
  }

  async function load() {
    stop();
    const requestVersion = version;
    exerciseId = null;
    const hintEl = document.getElementById("dictation-hint");
    hintEl.textContent = "Cargando frase...";
    document.getElementById("dict-input").value = "";
    document.getElementById("dict-words").textContent = "0";
    document.getElementById("dict-feedback").classList.add("hidden");
    try {
      const data = await API.dictationNext();
      if (requestVersion !== version) return;
      exerciseId = data.dictation_id;
      hintEl.textContent = `${data.hint_en} — ${data.word_count} words.`;
      hintEl.title = data.hint_es;
      play();
    } catch (err) {
      hintEl.textContent = "Error: " + err.message;
    }
  }

  async function play(slow = false) {
    if (!exerciseId) return;
    const requestVersion = ++audioVersion;
    TTS.stop();
    if (currentAudio) currentAudio.pause();
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    audioUrl = null;
    try {
      const blob = await API.dictationAudio(exerciseId, slow);
      if (requestVersion !== audioVersion) return;
      audioUrl = URL.createObjectURL(blob);
      currentAudio = new Audio(audioUrl);
      await currentAudio.play();
    } catch (err) {
      if (requestVersion === audioVersion) UI.toast("Tap Play to hear the dictation. " + err.message, { type: "warn" });
    }
  }

  async function check() {
    const input = document.getElementById("dict-input").value.trim();
    if (input.length < 1 || !exerciseId) return;
    const id = exerciseId;
    const btn = document.getElementById("btn-dict-check");
    if (btn.disabled) return;
    btn.disabled = true;
    try {
      const res = await API.dictationCheck({
        dictation_id: id,
        user_input: input,
      });
      if (id === exerciseId) _renderFeedback(res);
    } catch (err) {
      UI.toast("Error: " + err.message, { type: "error", duration: 4000 });
    } finally {
      btn.disabled = false;
    }
  }

  function _renderFeedback(r) {
    const fb = document.getElementById("dict-feedback");
    fb.classList.remove("hidden");
    document.getElementById("dict-score-fill").style.width = `${Math.round(r.score * 100)}%`;
    document.getElementById("dict-encouragement").textContent = r.feedback_es;

    const diff = document.getElementById("dict-diff");
    const esc = UI.escape;
    let html = `
      <h4>Frase correcta:</h4>
      <p style="background:#ecfdf5;padding:10px;border-radius:8px;font-style:italic">${esc(r.target)}</p>
      <h4 style="margin-top:12px">Tu respuesta:</h4>
      <p data-i18n-ignore style="background:#fef3c7;padding:10px;border-radius:8px">${esc(r.you_wrote)}</p>
    `;
    if (r.word_diff.missing && r.word_diff.missing.length) {
      html += `<p style="margin-top:10px"><strong>Te faltaron:</strong> <span style="color:#ef4444">${esc(r.word_diff.missing.join(", "))}</span></p>`;
    }
    if (r.word_diff.extra && r.word_diff.extra.length) {
      html += `<p><strong>De más:</strong> <span data-i18n-ignore style="color:#f59e0b">${esc(r.word_diff.extra.join(", "))}</span></p>`;
    }
    diff.innerHTML = html;
  }

  let _inited = false;
  function init() {
    if (_inited) return;   // evitar listeners duplicados
    _inited = true;
    document.getElementById("btn-dict-play").onclick = () => play();
    document.getElementById("btn-dict-slow").onclick = () => play(true);
    document.getElementById("btn-dict-check").onclick = check;
    document.getElementById("btn-dict-next").onclick = load;
    document.getElementById("dict-input").addEventListener("input", (e) => {
      const c = (e.target.value.trim().match(/\S+/g) || []).length;
      document.getElementById("dict-words").textContent = c;
    });
  }

  return { load, init, stop };
})();
