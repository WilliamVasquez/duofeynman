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
          Tenés <strong>${cards.length}</strong> ${cards.length === 1 ? "tema" : "temas"} para repasar.
          Tocá uno para practicarlo de nuevo — el algoritmo lo reagenda según cómo te salga.
        </p>
        <div id="srs-list"></div>
      `;
      const list = document.getElementById("srs-list");
      cards.forEach(c => {
        const div = document.createElement("div");
        div.className = "srs-card-item";
        div.innerHTML = `
          <h5>🗣️ ${c.topic ? c.topic.prompt_es : c.front}</h5>
          <div class="srs-meta">
            <span>Visto ${c.repetitions} veces</span>
            <span>Intervalo ${c.interval_days}d</span>
          </div>
        `;
        if (c.topic) {
          div.onclick = () => openTopicFn(c.topic);
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
