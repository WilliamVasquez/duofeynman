// Helpers de UI.
const UI = (() => {
  function show(viewId) {
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.getElementById(viewId).classList.add("active");
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function setUserHeader(user) {
    if (!user) return;
    document.getElementById("user-name").textContent = user.username || "amigo";
    document.getElementById("streak-days").textContent = user.streak_days || 0;
    document.getElementById("total-xp").textContent = user.total_xp || 0;
  }

  function renderModules(modules, onTopicClick) {
    const root = document.getElementById("modules");
    root.innerHTML = "";
    modules.forEach(m => {
      const card = document.createElement("div");
      card.className = "module-card";
      card.innerHTML = `
        <span class="module-level">${m.level}</span>
        <h4>${m.title_es}</h4>
        <p class="module-desc">${m.description_es}</p>
        <div class="lesson-list"></div>
      `;
      const lessonList = card.querySelector(".lesson-list");
      m.lessons.forEach(l => {
        const lessonEl = document.createElement("div");
        lessonEl.className = "lesson-item";
        lessonEl.innerHTML = `
          <h5>${l.title_es}</h5>
          <p class="lesson-obj">${l.objective_es}</p>
          <div class="topic-list"></div>
        `;
        const topicList = lessonEl.querySelector(".topic-list");
        l.topics.forEach(t => {
          const btn = document.createElement("button");
          btn.className = "topic-btn";
          btn.innerHTML = `
            <span>🗣️✍️ ${t.prompt_es}</span>
            <span class="difficulty">${"●".repeat(t.difficulty)}</span>
          `;
          btn.onclick = () => onTopicClick(t);
          topicList.appendChild(btn);
        });
        lessonList.appendChild(lessonEl);
      });
      root.appendChild(card);
    });
  }

  function renderTopic(topic) {
    document.getElementById("practice-title").textContent = "Practice";
    // Inmersión total: prompt EN protagonista. Click sobre el texto inglés → muestra ES inline DEBAJO.
    const promptEn = Profile.personalize(topic.prompt_en);
    const promptEs = Profile.personalize(topic.prompt_es);
    const promptEnEl = document.getElementById("prompt-en");
    const promptEsEl = document.getElementById("prompt-es");
    promptEnEl.innerHTML = `<span class="translatable" title="${promptEs.replace(/"/g, "&quot;")} (click for translation)">${promptEn}</span>`;
    promptEsEl.innerHTML = "";  // se llena dinámicamente al hacer click en el prompt
    // Click handler: inserta el ES debajo
    const enSpan = promptEnEl.querySelector(".translatable");
    enSpan.addEventListener("click", (e) => {
      e.stopPropagation();
      const existing = promptEsEl.querySelector(".es-inline");
      if (existing) { existing.remove(); return; }
      const span = document.createElement("div");
      span.className = "es-inline";
      span.textContent = promptEs;
      promptEsEl.appendChild(span);
    });

    // Personalizar el ejemplo para que cuando le des "Escuchar ejemplo" diga tu nombre
    topic.example_en = Profile.personalize(topic.example_en);

    const vocab = document.getElementById("vocab-list");
    vocab.innerHTML = "";
    (topic.key_vocabulary || []).forEach(v => {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${v.en}</strong> — ${v.es}`;
      vocab.appendChild(li);
    });

    document.getElementById("connectors-list").textContent =
      (topic.connectors || []).join(" · ") || "—";

    document.getElementById("transcript").textContent = "";
    document.getElementById("write-area").value = "";
    document.getElementById("write-words").textContent = "0";
    document.getElementById("feedback").classList.add("hidden");
  }

  function pct(v) { return `${Math.round((v || 0) * 100)}%`; }

  function renderFeedback(fb) {
    const el = document.getElementById("feedback");
    el.classList.remove("hidden");

    document.getElementById("score-fill").style.width = pct(fb.overall_score);
    document.getElementById("encouragement").textContent = fb.encouragement_es || "";

    document.getElementById("m-score").textContent = pct(fb.overall_score);
    document.getElementById("m-words").textContent = fb.word_count;
    document.getElementById("m-vocab").textContent = pct(fb.vocab_coverage);
    document.getElementById("m-connectors").textContent = pct(fb.connector_coverage);
    document.getElementById("m-cs").textContent = pct(fb.code_switch_rate);
    document.getElementById("m-fluency").textContent = pct(fb.fluency_score);

    // Sub-scores granulares
    _renderSubscores(fb.subscores || {}, fb);

    const errs = document.getElementById("errors-list");
    errs.innerHTML = "";
    if (!fb.errors || fb.errors.length === 0) {
      errs.innerHTML = `<li style="background:#ecfdf5;border-left-color:#10b981">¡Sin errores graves! 🎉</li>`;
    } else {
      fb.errors.slice(0, 8).forEach(e => {
        const li = document.createElement("li");
        const fix = e.suggestion ? ` → <em>${e.suggestion}</em>` : "";
        li.innerHTML = `<strong>${e.span_text}</strong>${fix}<br><small>${e.explanation_es || ""}</small>`;
        errs.appendChild(li);
      });
    }

    const soc = document.getElementById("socratic-list");
    soc.innerHTML = "";
    (fb.socratic_questions || []).forEach(q => {
      const li = document.createElement("li");
      li.textContent = q;
      li.style.cursor = "pointer";
      li.title = "Tocá para escuchar";
      li.onclick = () => TTS.speak(q);
      soc.appendChild(li);
    });

    const modelSec = document.getElementById("model-section");
    if (fb.model_answer_en) {
      modelSec.classList.remove("hidden");
      document.getElementById("model-answer").textContent = Profile.personalize(fb.model_answer_en);
    } else {
      modelSec.classList.add("hidden");
    }

    const nextBtn = document.getElementById("btn-next");
    nextBtn.classList.toggle("hidden", fb.next_action !== "MASTERED");
  }

  function _renderSubscores(s, fb) {
    let container = document.getElementById("subscores-block");
    if (!container) {
      container = document.createElement("div");
      container.id = "subscores-block";
      container.className = "subscores";
      document.getElementById("feedback").querySelector(".metrics").after(container);
    }
    const items = [
      { key: "vocabulary", label: "Vocabulario", icon: "📖", desc: "Cobertura + diversidad de palabras" },
      { key: "structure",  label: "Estructura",  icon: "🏗️", desc: "Conectores, tiempos verbales, oraciones" },
      { key: "naturalness",label: "Naturalidad", icon: "🌊", desc: "Sin code-switching, gramática limpia" },
      { key: "fluency",    label: "Fluidez",     icon: "💨", desc: "Velocidad y longitud" },
    ];
    container.innerHTML = `
      <h4 style="margin-bottom:8px">Detalle del score</h4>
      ${items.map(it => {
        const v = s[it.key] || 0;
        const pctv = Math.round(v * 100);
        return `
          <div class="subscore-row">
            <div class="subscore-head">
              <span>${it.icon} <strong>${it.label}</strong> <small style="color:#888">— ${it.desc}</small></span>
              <span class="subscore-val">${pctv}%</span>
            </div>
            <div class="subscore-bar"><div class="subscore-fill" style="width:${pctv}%"></div></div>
          </div>
        `;
      }).join("")}
      ${fb.tenses_used && fb.tenses_used.length ? `
        <p style="font-size:12px;color:var(--text-muted);margin-top:8px">
          Tiempos verbales detectados: ${fb.tenses_used.map(t => `<span class="tense-chip">${t.replace(/_/g, " ")}</span>`).join(" ")}
        </p>
      ` : ""}
      ${fb.sentence_count ? `
        <p style="font-size:12px;color:var(--text-muted)">Oraciones: ${fb.sentence_count} · Diversidad léxica: ${Math.round((fb.lexical_diversity || 0) * 100)}%</p>
      ` : ""}
    `;
  }

  function authError(msg) {
    document.getElementById("auth-error").textContent = msg || "";
  }

  // === Toast notifications ===
  let toastContainer = null;
  function _ensureToastContainer() {
    if (toastContainer) return toastContainer;
    toastContainer = document.createElement("div");
    toastContainer.id = "toast-container";
    document.body.appendChild(toastContainer);
    return toastContainer;
  }

  function toast(message, opts = {}) {
    const { type = "success", duration = 3000, icon = null } = opts;
    const container = _ensureToastContainer();
    // Máximo 3 toasts visibles: el más viejo se va (FIFO)
    while (container.children.length >= 3) container.firstElementChild.remove();
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    const defaultIcons = { success: "✓", error: "✕", info: "ℹ", warn: "⚠️" };
    el.innerHTML = `
      <span class="toast-icon">${icon || defaultIcons[type] || ""}</span>
      <span class="toast-msg">${message}</span>
    `;
    container.appendChild(el);
    requestAnimationFrame(() => el.classList.add("show"));
    setTimeout(() => {
      el.classList.remove("show");
      setTimeout(() => el.remove(), 300);
    }, duration);
  }

  function confetti(count = 50) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const colors = ["#0ea5e9", "#f97316", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444"];
    for (let i = 0; i < count; i++) {
      const p = document.createElement("div");
      p.className = "confetti-piece";
      p.style.left = Math.random() * 100 + "vw";
      p.style.background = colors[Math.floor(Math.random() * colors.length)];
      p.style.animationDuration = (1.8 + Math.random() * 1.6) + "s";
      p.style.animationDelay = (Math.random() * 0.4) + "s";
      p.style.transform = `rotate(${Math.random() * 360}deg)`;
      document.body.appendChild(p);
      setTimeout(() => p.remove(), 4200);
    }
  }

  return { show, setUserHeader, renderModules, renderTopic, renderFeedback, authError, toast, confetti };
})();
