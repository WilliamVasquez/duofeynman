// Comprensión auditiva: audio primero, texto opcional, resultado persistente.
const Listening = (() => {
  let version = 0, audioVersion = 0, exercise = null, audio = null, url = null;
  let ready = false, completed = false;
  function stop() {
    version++; audioVersion++;
    if (audio) audio.pause();
    if (url) URL.revokeObjectURL(url);
    audio = null; url = null;
  }
  function transcript(data) {
    document.getElementById('listening-text').innerHTML = `<p>${I18n.html(data.audio_en, data.audio_es)}</p>`;
  }
  async function play(slow) {
    if (!exercise) return;
    const request = ++audioVersion;
    TTS.stop();
    if (audio) audio.pause();
    if (url) URL.revokeObjectURL(url);
    url = null;
    try {
      const blob = await API.listeningAudio(exercise.id, slow);
      if (request !== audioVersion) return;
      url = URL.createObjectURL(blob); audio = new Audio(url);
      await audio.play();
      if (request !== audioVersion) return;
      ready = true;
      document.getElementById('listening-check').disabled = completed;
    } catch (err) { if (request === audioVersion) UI.toast(err.message, {type: 'warn'}); }
  }
  async function load(slug) {
    UI.show('view-listening'); stop();
    const request = version;
    exercise = null; ready = false; completed = false;
    const root = document.getElementById('listening-content');
    root.textContent = 'Loading…';
    try {
      const data = await API.listeningNext(slug);
      if (request !== version) return;
      exercise = data;
      root.innerHTML = `<div class="practice-panel"><strong>${UI.escape(data.level)} · Listening</strong><p>${I18n.html('Listen, then choose the meaning. You can replay the audio.', 'Escuchá y elegí el significado. Podés repetir el audio.')}</p>
        <div class="practice-actions"><button id="listening-play" class="btn-primary">🔊 Play</button><button id="listening-slow" class="btn-secondary">🐢 Slower</button></div>
        <h3>${I18n.html(data.question_en, data.question_es)}</h3><form id="listening-form"><fieldset><legend>${I18n.html('Choose one answer', 'Elegí una respuesta')}</legend>
        ${data.options.map((o, i) => `<label class="listening-option"><input type="radio" name="meaning" value="${i}" required>${I18n.html(o.en, o.es)}</label>`).join('')}
        </fieldset><button id="listening-check" class="btn-primary" disabled>Check</button></form>
        <div id="listening-feedback" aria-live="polite"></div><button id="listening-reveal" class="btn-ghost">${I18n.html('Reveal text (guided practice)', 'Mostrar texto (práctica con ayuda)')}</button>
        <div id="listening-text"></div><button id="listening-next" class="btn-secondary">Next exercise →</button></div>`;
      document.getElementById('listening-play').onclick = () => play(false);
      document.getElementById('listening-slow').onclick = () => play(true);
      document.getElementById('listening-next').onclick = () => load();
      document.getElementById('listening-reveal').onclick = async () => {
        try {
          const result = await API.listeningReveal(data.id);
          if (request !== version) return;
          transcript(result); ready = true;
          document.getElementById('listening-check').disabled = completed;
        } catch (err) { UI.toast(err.message, {type: 'error'}); }
      };
      document.getElementById('listening-form').onsubmit = async e => {
        e.preventDefault();
        if (!ready || completed) return;
        const choice = new FormData(e.target).get('meaning');
        if (choice === null) return;
        const btn = document.getElementById('listening-check');
        if (btn.disabled) return;
        btn.disabled = true;
        try {
          const result = await API.listeningCheck(data.id, Number(choice));
          if (request !== version) return;
          completed = true; transcript(result);
          document.getElementById('listening-feedback').innerHTML = `<h4>${I18n.html(result.score ? 'Correct!' : 'Listen for this detail:', result.score ? '¡Correcto!' : 'Prestá atención a este detalle:')}</h4>
            <p>${I18n.html(data.options[result.correct].en, data.options[result.correct].es)}</p>
            <p>${I18n.html(result.explanation_en, result.explanation_es)}</p>
            <p>${I18n.html(result.assisted ? 'Saved as guided practice.' : 'Listening result saved.', result.assisted ? 'Guardado como práctica con ayuda.' : 'Resultado de escucha guardado.')}</p>`;
        } catch (err) { if (request === version) {btn.disabled = false; UI.toast(err.message, {type: 'error'});} }
      };
    } catch (err) { if (request === version) root.textContent = err.message; }
  }
  return {load, stop};
})();
