// Vista SRS: lista de cards que vencen hoy.
const SRS = (() => {
  let openTopicCallback = null;
  let version = 0;
  async function render(openTopicFn) {
    openTopicCallback = openTopicFn || openTopicCallback;
    const currentVersion = ++version;
    const root = document.getElementById("srs-content");
    root.innerHTML = `
      <div class="skeleton skeleton-line" style="width:70%"></div>
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
    `;
    try {
      const cards = await API.srsDue();
      if (currentVersion !== version) return;
      if (!cards.length) {
        root.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">🎉</div>
            <h4>¡Nada para repasar hoy!</h4>
            <p>Volvé mañana o seguí con lecciones nuevas.</p>
          </div>
        `;
        return;
      }
      root.innerHTML = `
        <p style="color:var(--text-soft);margin-bottom:16px">
          ${I18n.html(`You have ${cards.length} ${cards.length === 1 ? "topic" : "topics"} to review. Choose one to practice. Your result sets the next review date.`, `Tenés ${cards.length} temas para repasar. Elegí uno para practicar; el resultado define la próxima fecha de repaso.`)}
        </p>
        <div id="srs-list"></div>
      `;
      const list = document.getElementById("srs-list");
      cards.forEach(c => {
        const div = document.createElement("div");
        div.className = "srs-card-item";
        div.innerHTML = `
          <h5>🗣️ ${c.card_type === 'ERROR_DRILL' ? `Correct: <span data-i18n-ignore>${UI.escape(c.front)}</span>` : c.topic ? I18n.html(c.topic.prompt_en, c.topic.prompt_es) : UI.escape(c.front)}</h5>
          <div class="srs-meta">
            <span>Visto ${c.repetitions} veces</span>
            <span>Intervalo ${c.interval_days}d</span>
          </div>
        `;
        if (c.topic || c.card_type === 'ERROR_DRILL') {
          const open = () => c.card_type === 'ERROR_DRILL' ? openDrill(c.id) : openTopicCallback(c.topic);
          div.onclick = open;
          const start = document.createElement("button");
          start.type = "button"; start.className = "btn btn-small"; start.textContent = "Practice";
          start.onclick = e => { e.stopPropagation(); open(); };
          div.appendChild(start);
        }
        list.appendChild(div);
      });
    } catch (err) {
      root.innerHTML = `<p style='color:red'>Error: ${UI.escape(err.message)}</p>`;
    }
  }

  async function dueCount() {
    try {
      const s = await API.srsStats();
      return s.due_today || 0;
    } catch { return 0; }
  }

  async function openDrill(id) {
    UI.show('view-srs');
    const currentVersion = ++version;
    const root = document.getElementById('srs-content');
    root.textContent = 'Loading…';
    try {
      const card = await API.drill(id);
      if (currentVersion !== version) return;
      root.innerHTML = `<div class="practice-panel"><h3>${I18n.html('Fix this phrase', 'Corregí esta frase')}</h3>
        <p>${I18n.html('Write the corrected phrase. Focus on this one mistake.', 'Escribí la frase corregida. Concentrate en este error.')}</p>
        <blockquote data-i18n-ignore>${UI.escape(card.front)}</blockquote>
        <form id="drill-form"><label for="drill-answer">${I18n.html('Your correction', 'Tu corrección')}</label>
        <input id="drill-answer" required maxlength="500" autocomplete="off"><button class="btn-primary" type="submit">Check</button></form>
        <div id="drill-feedback" aria-live="polite"></div><button type="button" id="drill-back" class="btn-ghost">Back to review</button></div>`;
      document.getElementById('drill-back').onclick = () => render(openTopicCallback);
      document.getElementById('drill-form').onsubmit = async e => {
        e.preventDefault();
        const btn = e.target.querySelector('button[type="submit"]');
        if (btn.disabled) return;
        btn.disabled = true;
        try {
          const result = await API.drillCheck(id, document.getElementById('drill-answer').value);
          if (currentVersion !== version) return;
          document.getElementById('drill-feedback').innerHTML = `<p>${I18n.html(result.correct ? 'Correct!' : 'Compare your answer with this correction:', result.correct ? '¡Correcto!' : 'Compará tu respuesta con esta corrección:')}</p>
            <p data-i18n-ignore><strong>${UI.escape(result.answer)}</strong></p>
            <p>${I18n.html('Why this correction?', result.explanation_es)}</p><p>Next review: ${UI.escape(result.due_date)}</p>`;
        } catch (err) { UI.toast(err.message, {type: 'error'}); }
        finally {btn.disabled = false;}
      };
    } catch (err) { if (currentVersion === version) root.textContent = err.message; }
  }
  return { render, dueCount, openDrill };
})();
