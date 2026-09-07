// Vista SRS: lista de cards que vencen hoy.
const SRS = (() => {
  async function render(openTopicFn) {
    const root = document.getElementById("srs-content");
    root.innerHTML = `
      <div class="skeleton skeleton-line" style="width:70%"></div>
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
    `;
    try {
      const cards = await API.srsDue();
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
          <h5>🗣️ ${c.topic ? I18n.html(c.topic.prompt_en, c.topic.prompt_es) : UI.escape(c.front)}</h5>
          <div class="srs-meta">
            <span>Visto ${c.repetitions} veces</span>
            <span>Intervalo ${c.interval_days}d</span>
          </div>
        `;
        if (c.topic) {
          div.onclick = () => openTopicFn(c.topic);
          const start = document.createElement("button");
          start.type = "button"; start.className = "btn btn-small"; start.textContent = "Practice";
          start.onclick = e => { e.stopPropagation(); openTopicFn(c.topic); };
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

  return { render, dueCount };
})();
