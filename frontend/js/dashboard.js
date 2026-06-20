// Vista Dashboard: stats, gráfico de 7 días, logros.
const Dashboard = (() => {
  async function render() {
    const root = document.getElementById("dashboard-content");
    root.innerHTML = `
      <div class="dash-stats">
        <div class="skeleton skeleton-stat"></div><div class="skeleton skeleton-stat"></div>
        <div class="skeleton skeleton-stat"></div><div class="skeleton skeleton-stat"></div>
      </div>
      <div class="skeleton skeleton-card" style="height:140px"></div>
      <div class="skeleton skeleton-card" style="height:140px"></div>
    `;
    try {
      const data = await API.dashboard();
      const s = data.summary;
      root.innerHTML = `
        <div class="dash-stats">
          <div class="dash-stat"><div class="stat-num">🔥 ${s.streak_days}</div><div class="stat-label">Racha días</div></div>
          <div class="dash-stat"><div class="stat-num">⭐ ${s.total_xp}</div><div class="stat-label">XP total</div></div>
          <div class="dash-stat"><div class="stat-num">✅ ${s.mastered_topics}</div><div class="stat-label">Temas dominados</div></div>
          <div class="dash-stat"><div class="stat-num">📊 ${Math.round((s.average_score||0)*100)}%</div><div class="stat-label">Score promedio</div></div>
        </div>

        <div class="chart-card">
          <h4>Fluidez últimos 7 días</h4>
          <div class="chart" id="chart-fluency"></div>
        </div>

        <div class="chart-card">
          <h4>Score últimos 7 días</h4>
          <div class="chart" id="chart-score"></div>
        </div>

        <h4 class="section-title">🏆 Logros desbloqueados (${data.achievements_unlocked.length})</h4>
        <div class="achievements-grid" id="ach-unlocked"></div>

        <h4 class="section-title" style="margin-top:20px">🔒 Logros pendientes</h4>
        <div class="achievements-grid" id="ach-locked"></div>
      `;

      _renderChart("chart-fluency", data.last_7_days, "fluency");
      _renderChart("chart-score", data.last_7_days, "score");
      _renderAchievements("ach-unlocked", data.achievements_unlocked, false);
      _renderAchievements("ach-locked", data.achievements_pending, true);

      // Cargar insights después (independiente)
      _renderInsights();
    } catch (err) {
      root.innerHTML = `<p style='color:red'>Error: ${UI.escape(err.message)}</p>`;
    }
  }

  async function _renderInsights() {
    try {
      const i = await API.insights();
      const root = document.getElementById("dashboard-content");

      const section = document.createElement("div");
      section.innerHTML = `
        <h4 class="section-title" style="margin-top:24px">🔬 Insights de tu aprendizaje</h4>

        <div class="chart-card">
          <h4>Tus promedios globales</h4>
          <div class="dash-stats" style="margin-bottom:0">
            <div class="dash-stat"><div class="stat-num">${Math.round(i.averages.score * 100)}%</div><div class="stat-label">Score promedio</div></div>
            <div class="dash-stat"><div class="stat-num">${Math.round(i.averages.fluency * 100)}%</div><div class="stat-label">Fluidez promedio</div></div>
            <div class="dash-stat"><div class="stat-num">${Math.round(i.averages.code_switch_rate * 100)}%</div><div class="stat-label">Code-switch promedio</div></div>
            <div class="dash-stat"><div class="stat-num">${i.averages.avg_words_per_attempt}</div><div class="stat-label">Palabras por intento</div></div>
          </div>
        </div>

        ${_renderSpanishLeaks(i.spanish_leaks)}
        ${_renderGrammarDrills(i.grammar_drills)}
        ${_renderWeakTopics(i.weak_topics)}
        ${_renderFastMastered(i.fast_mastered)}
        ${_renderErrorCategories(i.errors_by_category)}
      `;
      root.appendChild(section);
    } catch (err) {
      console.warn("Insights no disponibles:", err.message);
    }
  }

  function _renderSpanishLeaks(leaks) {
    if (!leaks || !leaks.length) return "";
    return `
      <div class="chart-card">
        <h4>🇪🇸 Palabras que más se te escapan en español</h4>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">
          Estas palabras las dijiste en español más de una vez. Aprendelas en inglés.
        </p>
        <div class="leak-chips">
          ${leaks.map(l => `<span class="leak-chip">${l.word} <strong>×${l.count}</strong></span>`).join("")}
        </div>
      </div>
    `;
  }

  function _renderGrammarDrills(drills) {
    if (!drills || !drills.length) return "";
    return `
      <div class="chart-card">
        <h4>📝 Errores gramaticales que repetís</h4>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">
          Estos errores los hiciste varias veces. Practicá la forma correcta.
        </p>
        <ul class="drill-list">
          ${drills.map(d => `
            <li>
              <span class="drill-wrong">${d.wrong}</span>
              <span class="drill-arrow">→</span>
              <span class="drill-fix">${d.fix || "—"}</span>
              <span class="drill-count">×${d.count}</span>
            </li>
          `).join("")}
        </ul>
      </div>
    `;
  }

  function _renderWeakTopics(weak) {
    if (!weak || !weak.length) return "";
    return `
      <div class="chart-card">
        <h4>🎯 Temas que más te cuestan</h4>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">
          Los 5 temas con score más bajo. Repetilos hasta dominarlos.
        </p>
        <ul class="weak-list">
          ${weak.map(w => `
            <li>
              <span>${w.prompt_es}</span>
              <span style="color:#ef4444;font-weight:700">${Math.round(w.avg_score * 100)}%</span>
            </li>
          `).join("")}
        </ul>
      </div>
    `;
  }

  function _renderFastMastered(fast) {
    if (!fast || !fast.length) return "";
    return `
      <div class="chart-card">
        <h4>⚡ Temas que dominaste rápido</h4>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">
          Estos los sacaste en 1-2 intentos. ¡Buen trabajo!
        </p>
        <ul class="weak-list">
          ${fast.map(w => `
            <li>
              <span>${w.prompt_es}</span>
              <span style="color:#10b981;font-weight:700">${Math.round(w.best_score * 100)}%</span>
            </li>
          `).join("")}
        </ul>
      </div>
    `;
  }

  function _renderErrorCategories(cats) {
    if (!cats || !cats.length) return "";
    const labels = {
      GRAMMAR: "Gramática",
      CODE_SWITCH: "Code-switching (español)",
      AI_CORRECTION: "Correcciones automáticas",
      PRONUNCIATION: "Pronunciación",
      VOCABULARY: "Vocabulario",
    };
    return `
      <div class="chart-card">
        <h4>📊 Distribución de errores</h4>
        <ul class="weak-list">
          ${cats.map(c => `
            <li>
              <span>${labels[c.category] || c.category}</span>
              <span style="font-weight:700">${c.count}</span>
            </li>
          `).join("")}
        </ul>
      </div>
    `;
  }

  function _renderChart(id, days, key) {
    const root = document.getElementById(id);
    if (!root) return;
    root.innerHTML = "";
    const max = Math.max(0.05, ...days.map(d => d[key] || 0));
    days.forEach(d => {
      const v = d[key] || 0;
      const heightPct = (v / max) * 100;
      const bar = document.createElement("div");
      bar.className = "chart-bar";
      bar.style.height = `${Math.max(2, heightPct)}%`;
      bar.style.opacity = d.count > 0 ? "1" : "0.25";
      const dayLabel = new Date(d.date + "T00:00:00").toLocaleDateString("es", { weekday: "short" });
      bar.innerHTML = `
        <span class="bar-value">${Math.round(v * 100)}%</span>
        <span class="bar-label">${dayLabel}</span>
      `;
      root.appendChild(bar);
    });
  }

  const ICONS = {
    trophy: "🏆", star: "⭐", flame: "🔥", "shield-check": "🛡️",
    zap: "⚡", footprints: "👣",
  };

  function _renderAchievements(id, list, locked) {
    const root = document.getElementById(id);
    if (!root) return;
    if (!list.length) {
      root.innerHTML = `<p style='color:#888;font-size:13px'>${locked ? "¡Los desbloqueaste todos!" : "Aún ninguno. Practicá para desbloquear."}</p>`;
      return;
    }
    root.innerHTML = list.map(a => `
      <div class="ach-card ${locked ? "locked" : ""}">
        <div class="ach-icon">${ICONS[a.icon] || "🏅"}</div>
        <div class="ach-title">${a.title_es}</div>
        <div class="ach-desc">${a.description_es}</div>
        <div class="ach-xp">+${a.xp} XP</div>
      </div>
    `).join("");
  }

  return { render };
})();
