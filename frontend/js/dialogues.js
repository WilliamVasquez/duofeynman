// Lista de diálogos + chat de role-play.
const Dialogues = (() => {
  let allDialogues = [];
  let current = null;          // dialogue cargado completo
  let turnIndex = 0;           // turno actual
  let scores = [];             // scores de cada turno user
  let chatRecording = false;

  // === Ejes de vida: cada slug de diálogo se mapea a una categoría ===
  // Las categorías cruzan con los "interests" del perfil para filtrar.
  const LIFE_AXES = [
    { key: "work_daily", interest: "work", icon: "💻", title: "Mi día laboral",
      slugs: ["daily-standup", "work-call-tech", "first-day-onboarding", "team-meeting-propose", "tough-feedback",
              "explain-project", "debugging-call", "detective-deduction"] },
    { key: "career", interest: "work", icon: "💼", title: "Mi carrera",
      slugs: ["job-interview", "salary-raise", "client-negotiation",
              "interview-experiences", "negotiate-salary-offer", "small-business-pitch"] },
    { key: "partner", interest: "relationship", icon: "❤️", title: "Con mi pareja",
      slugs: ["spouse-after-work", "couple-hard-talk", "couple-finances", "romantic-dinner-ask-out", "deep-talk",
              "describe-someone-i-met"] },
    { key: "adult", interest: "adult", icon: "🔥", title: "Adulto (+18)",
      slugs: ["intimate-motel", "spicy-couple-talk"] },
    { key: "out", interest: "shopping", icon: "🌆", title: "Saliendo de casa",
      slugs: ["uber-ride", "restaurant-order", "supermarket", "ask-directions", "food-allergies", "bank-open-account",
              "complain-service"] },
    { key: "health", interest: "health", icon: "🏥", title: "Cuando algo pasa",
      slugs: ["doctor-visit", "vet-visit", "emergency-911", "serious-apology"] },
    { key: "social", interest: "social", icon: "👥", title: "Lo social",
      slugs: ["party-meet", "phone-call-simple", "reconnect-old-friend", "give-condolences",
              "tell-life-story", "hypothetical-life", "deep-life-reflection", "gossip-friend", "talk-about-news",
              "catching-up-coworker"] },
    { key: "family", interest: "family", icon: "🎄", title: "Familia y fechas",
      slugs: ["christmas-in-laws"] },
    { key: "consumer", interest: "shopping", icon: "🛒", title: "Consumidor informado",
      slugs: ["tech-store-camera", "used-car-buy", "rent-apartment"] },
    { key: "travel", interest: "travel", icon: "✈️", title: "Cuando viajés",
      slugs: ["airport-checkin", "hotel-checkin", "immigration-airport", "missed-flight"] },
  ];

  function _categoryForSlug(slug) {
    return LIFE_AXES.find(a => a.slugs.includes(slug));
  }
  // Modo de input: "type" | "order"
  let inputMode = localStorage.getItem("duofeynman_input_mode") || "type";
  // Estado del word-order
  let bankWords = [];      // palabras disponibles {id, text}
  let outputWords = [];    // palabras seleccionadas en orden

  async function renderList() {
    const root = document.getElementById("dialogues-list");
    root.innerHTML = "<p style='color:#888;text-align:center'>Cargando...</p>";
    try {
      allDialogues = await API.dialoguesList();
      _renderFiltered();
    } catch (err) {
      root.innerHTML = `<p style='color:red'>${err.message}</p>`;
    }
  }

  function _renderFiltered() {
    const root = document.getElementById("dialogues-list");
    const showAdult = document.getElementById("show-adult").checked;
    const profile = Profile.get();
    const hidden = Profile.getHidden().dialogues;

    root.innerHTML = "";

    // Para cada eje, filtrar y renderizar si el interés está activo y hay items
    LIFE_AXES.forEach(axis => {
      // Si el perfil tiene desactivado este interés, saltar
      if (Profile.isFilled() && profile.interests && profile.interests[axis.interest] === false) {
        return;
      }
      // El eje "adult" además requiere checkbox de "Mostrar adultos"
      if (axis.key === "adult" && !showAdult) return;

      const items = allDialogues.filter(d => {
        if (!axis.slugs.includes(d.slug)) return false;
        if (hidden.includes(d.slug)) return false;
        if (!showAdult && d.is_adult) return false;
        return true;
      });

      if (!items.length) return;

      const section = document.createElement("div");
      section.className = "axis-section";
      section.innerHTML = `<h4 class="axis-title">${axis.icon} ${axis.title} <small>(${items.length})</small></h4>`;
      const grid = document.createElement("div");
      grid.className = "axis-grid";
      items.forEach(d => grid.appendChild(_dialogueCard(d)));
      section.appendChild(grid);
      root.appendChild(section);
    });

    // Diálogos sin eje (por si agregamos uno y olvidamos mapearlo)
    const mapped = new Set(LIFE_AXES.flatMap(a => a.slugs));
    const orphans = allDialogues.filter(d => !mapped.has(d.slug) && !hidden.includes(d.slug) && (showAdult || !d.is_adult));
    if (orphans.length) {
      const section = document.createElement("div");
      section.className = "axis-section";
      section.innerHTML = `<h4 class="axis-title">📦 Otros</h4>`;
      const grid = document.createElement("div");
      grid.className = "axis-grid";
      orphans.forEach(d => grid.appendChild(_dialogueCard(d)));
      section.appendChild(grid);
      root.appendChild(section);
    }

    if (!root.children.length) {
      root.innerHTML = `<div class='empty-state'><div class='empty-icon'>🙈</div><h4>No hay nada para mostrar</h4><p>Activá más áreas de interés en <strong>Mi perfil</strong> o quitá items ocultos.</p></div>`;
    }
  }

  function _dialogueCard(d) {
    const card = document.createElement("div");
    card.className = "dialogue-card";
    card.innerHTML = `
      <div class="dlg-icon">${d.icon}</div>
      <div class="dlg-body">
        <div class="dlg-title">
          ${Profile.personalize(d.title_es)}
          ${d.is_adult ? '<span class="adult-badge">+18</span>' : ''}
        </div>
        <div class="dlg-desc">${Profile.personalize(d.description_es)}</div>
        <div class="dlg-meta">${d.level} · Dificultad ${"●".repeat(d.difficulty)} · con ${Profile.personalize(d.npc_role_es)}</div>
      </div>
      <button class="dlg-hide-btn" title="No me sirve, ocultar">✕</button>
    `;
    card.querySelector(".dlg-body").onclick = () => start(d.id);
    card.querySelector(".dlg-icon").onclick = () => start(d.id);
    card.querySelector(".dlg-hide-btn").onclick = async (e) => {
      e.stopPropagation();
      if (confirm(`¿Ocultar "${d.title_es}"? Lo podés recuperar desde Mi perfil.`)) {
        await Profile.hideItem("dialogues", d.slug);
        _renderFiltered();
      }
    };
    return card;
  }

  async function start(dialogueId) {
    try {
      current = await API.dialogue(dialogueId);
      turnIndex = 0;
      scores = [];
      UI.show("view-chat");
      const oldBanner = document.getElementById("profile-banner");
      if (oldBanner) oldBanner.remove();

      // Título: EN como protagonista, ES como tooltip + click para expandir
      const titleEn = Profile.personalize(current.title_en);
      const titleEs = Profile.personalize(current.title_es);
      const titleEl = document.getElementById("chat-title");
      titleEl.innerHTML = `<span class="translatable" title="${_escapeAttr(titleEs)}">${titleEn}</span>`;
      _wireTranslatable(titleEl.querySelector(".translatable"), titleEs);

      // Scene context: SIEMPRE VISIBLE en inglés. Click sobre el texto inglés
      // → muestra la traducción ES inline debajo (sin ocultar el inglés).
      const setting = document.getElementById("chat-setting");
      const settingEs = Profile.personalize(current.setting_es);
      const settingEn = Profile.personalize(current.setting_en || current.setting_es);
      setting.innerHTML = `
        <div class="setting-label">📍 Scene context</div>
        <div class="setting-text translatable" title="${_escapeAttr(settingEs)} (click for Spanish)">${settingEn}</div>
      `;
      _wireTranslatable(setting.querySelector(".setting-text"), settingEs);

      // Banner de perfil: chip "Your profile" en inglés. Click → expande EN.
      // Ese EN es a su vez translatable → click → muestra ES inline debajo.
      const axis = _categoryForSlug(current.slug);
      const banner = axis ? Profile.practiceBanner(axis.interest) : Profile.practiceBanner(null);
      const oldBannerPrev = document.getElementById("profile-banner");
      if (oldBannerPrev) oldBannerPrev.remove();
      if (banner) {
        setting.insertAdjacentHTML("afterend", `
          <div class="profile-banner-wrap" id="profile-banner">
            <button type="button" class="profile-banner-chip" title="${_escapeAttr(banner.en)}">👤 Your profile</button>
            <div class="profile-banner-text hidden translatable" title="${_escapeAttr(banner.es)} (click for Spanish)">${banner.en}</div>
          </div>
        `);
        const wrap = document.getElementById("profile-banner");
        const chip = wrap.querySelector(".profile-banner-chip");
        const textEl = wrap.querySelector(".profile-banner-text");
        chip.onclick = () => {
          textEl.classList.toggle("hidden");
        };
        _wireTranslatable(textEl, banner.es);
      }
      document.getElementById("chat-messages").innerHTML = "";
      document.getElementById("chat-complete").classList.add("hidden");
      document.getElementById("chat-input-zone").classList.add("hidden");
      document.getElementById("chat-input").value = "";
      _nextTurn();
    } catch (err) {
      alert("Error: " + err.message);
    }
  }

  function _nextTurn() {
    if (!current || turnIndex >= current.turns.length) {
      return _finish();
    }
    const turn = current.turns[turnIndex];
    if (turn.speaker === "NPC") {
      _renderNpcMessage(turn);
      // Auto-speak
      setTimeout(() => TTS.speak(turn.npc_text_en), 200);
      turnIndex++;
      // Si el siguiente es USER, mostrar input
      const nextTurn = current.turns[turnIndex];
      if (nextTurn && nextTurn.speaker === "USER") {
        _showUserInput(nextTurn);
      } else if (nextTurn && nextTurn.speaker === "NPC") {
        // Dos NPC seguidos: esperar un poco y mostrar
        setTimeout(() => _nextTurn(), 1800);
      } else {
        _finish();
      }
    } else if (turn.speaker === "USER") {
      _showUserInput(turn);
    }
  }

  function _escapeAttr(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /** Hace clickeable un elemento que tiene texto en inglés.
   * Al click, INSERTA un <span class="es-inline"> con la traducción debajo
   * SIN ocultar el inglés. Click otra vez → la quita.
   */
  function _wireTranslatable(el, esText) {
    if (!el || !esText) return;
    el.classList.add("translatable");
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      // Si ya está expandido, lo cerramos
      const next = el.nextElementSibling;
      if (next && next.classList.contains("es-inline")) {
        next.remove();
        return;
      }
      const span = document.createElement("div");
      span.className = "es-inline";
      span.textContent = esText;
      el.insertAdjacentElement("afterend", span);
    });
  }

  function _renderNpcMessage(turn) {
    const list = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "chat-msg npc";
    const npcName = Profile.personalize(current.npc_name);
    const textEn = Profile.personalize(turn.npc_text_en);
    const textEs = Profile.personalize(turn.npc_text_es);
    const hasTrans = !!(textEs && textEs.trim());

    // Inmersión total: SOLO inglés visible. La traducción aparece DEBAJO
    // (sin ocultar el inglés) al click del mensaje. Tooltip nativo en hover.
    div.innerHTML = `
      <span class="speaker">${npcName}</span>
      <div class="msg-en translatable"${hasTrans ? ` title="${_escapeAttr(textEs)} (click for translation)"` : ""}>${textEn}</div>
      <div class="msg-actions">
        <button class="listen-btn" title="Escuchar">🔊 Listen</button>
      </div>
    `;
    div.querySelector(".listen-btn").onclick = (e) => { e.stopPropagation(); TTS.speak(textEn); };
    if (hasTrans) {
      _wireTranslatable(div.querySelector(".msg-en"), textEs);
    }
    list.appendChild(div);
    _scrollChat();
  }

  function _renderUserMessage(text) {
    const list = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "chat-msg user";
    div.innerHTML = `<span class="speaker">Vos</span>${text}`;
    list.appendChild(div);
    _scrollChat();
  }

  function _showUserInput(turn) {
    document.getElementById("chat-input-zone").classList.remove("hidden");
    const hintText = Profile.personalize(turn.user_hint_es || "Respondé al personaje.");
    const hintEl = document.getElementById("user-hint");
    // Hint chip en inglés. Click → muestra el texto en español inline (sin ocultar).
    hintEl.innerHTML = `
      <button type="button" class="hint-toggle translatable" title="${_escapeAttr(hintText)} (click for hint in Spanish)">💡 Need a hint?</button>
    `;
    const hintBtn = hintEl.querySelector(".hint-toggle");
    _wireTranslatable(hintBtn, hintText);
    const chips = document.getElementById("helper-chips");
    chips.innerHTML = "";
    (turn.helper_phrases || []).forEach(p => {
      const personalizedPhrase = Profile.personalize(p);
      const b = document.createElement("button");
      b.className = "helper-chip";
      b.textContent = personalizedPhrase;
      b.onclick = () => {
        const inp = document.getElementById("chat-input");
        inp.value = inp.value ? inp.value + " " + personalizedPhrase : personalizedPhrase;
        inp.focus();
      };
      chips.appendChild(b);
    });
    document.getElementById("chat-input").value = "";
    document.getElementById("chat-turn-feedback").classList.add("hidden");

    // Preparar word bank desde la respuesta modelo (personalizada)
    _setupWordBank(Profile.personalize(turn.user_example_en || ""));
    _applyInputMode();

    if (inputMode === "type") document.getElementById("chat-input").focus();
    _scrollChat();
  }

  // ---- Word ordering (modo Duolingo) ----
  function _tokenize(text) {
    // Mantiene puntuación pegada a la palabra ("you?" / "tonight.")
    const tokens = text.match(/[\w'’\-]+[.,!?;:]?/g) || [];
    return tokens;
  }

  function _shuffleArray(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function _setupWordBank(exampleText) {
    const tokens = _tokenize(exampleText);
    // Asignar id único para que repetidos sean independientes
    bankWords = _shuffleArray(tokens.map((t, i) => ({ id: i, text: t })));
    outputWords = [];
    _renderWordZones();
  }

  function _renderWordZones() {
    const bankEl = document.getElementById("word-bank");
    const outEl = document.getElementById("word-output");
    if (!bankEl || !outEl) return;

    // Output
    if (outputWords.length === 0) {
      outEl.innerHTML = `<span class="word-output-empty">Tocá las palabras de abajo para armar la oración →</span>`;
    } else {
      outEl.innerHTML = "";
      outputWords.forEach(w => {
        const chip = document.createElement("button");
        chip.className = "word-chip selected";
        chip.textContent = w.text;
        chip.onclick = () => _moveFromOutput(w.id);
        outEl.appendChild(chip);
      });
    }

    // Bank
    bankEl.innerHTML = "";
    bankWords.forEach(w => {
      const chip = document.createElement("button");
      chip.className = "word-chip";
      chip.textContent = w.text;
      chip.onclick = () => _moveToOutput(w.id);
      bankEl.appendChild(chip);
    });

    // Vacío?
    if (bankWords.length === 0 && outputWords.length > 0) {
      bankEl.innerHTML = `<span class="word-bank-empty">Todas usadas. Tocá Enviar o limpiá para arrancar de cero.</span>`;
    }
  }

  function _moveToOutput(id) {
    const idx = bankWords.findIndex(w => w.id === id);
    if (idx < 0) return;
    const [word] = bankWords.splice(idx, 1);
    outputWords.push(word);
    _renderWordZones();
  }

  function _moveFromOutput(id) {
    const idx = outputWords.findIndex(w => w.id === id);
    if (idx < 0) return;
    const [word] = outputWords.splice(idx, 1);
    bankWords.push(word);
    _renderWordZones();
  }

  function _clearOutput() {
    bankWords = _shuffleArray([...bankWords, ...outputWords]);
    outputWords = [];
    _renderWordZones();
  }

  function _shuffleBank() {
    bankWords = _shuffleArray(bankWords);
    _renderWordZones();
  }

  function _getOrderedText() {
    return outputWords.map(w => w.text).join(" ");
  }

  function _applyInputMode() {
    document.querySelectorAll(".input-mode-btn").forEach(b => {
      b.classList.toggle("active", b.dataset.inputMode === inputMode);
    });
    document.getElementById("chat-toolbar-type").classList.toggle("hidden", inputMode !== "type");
    document.getElementById("chat-toolbar-order").classList.toggle("hidden", inputMode !== "order");
  }

  function _setInputMode(mode) {
    inputMode = mode;
    localStorage.setItem("duofeynman_input_mode", mode);
    _applyInputMode();
  }

  async function _submitUserTurn() {
    const turn = current.turns[turnIndex];
    if (!turn || turn.speaker !== "USER") return;
    const input = document.getElementById("chat-input");
    let text = "";
    if (inputMode === "order") {
      text = _getOrderedText().trim();
      if (!text) { alert("Tocá las palabras para armar la oración."); return; }
    } else {
      text = input.value.trim();
      if (!text) return;
    }

    try {
      const result = await API.dialogueCheck({ turn_id: turn.id, user_text: text });
      _renderUserMessage(text);
      _renderTurnFeedback(result);
      scores.push(result.score);
      input.value = "";

      if (result.passed) {
        turnIndex++;
        document.getElementById("chat-input-zone").classList.add("hidden");
        outputWords = []; bankWords = [];
        setTimeout(() => _nextTurn(), 1200);
      } else {
        // No avanzamos; le damos una segunda oportunidad
        // (puede reintentar o saltar)
      }
    } catch (err) {
      alert("Error: " + err.message);
    }
  }

  function _renderTurnFeedback(r) {
    const fb = document.getElementById("chat-turn-feedback");
    fb.classList.remove("hidden");
    fb.classList.toggle("pass", r.passed);
    fb.classList.toggle("fail", !r.passed);
    let html = `<strong>${Math.round(r.score * 100)}%</strong> · <span class="translatable" title="${_escapeAttr(r.feedback_es)}">${r.passed ? "Good!" : "Try again"}</span>`;
    if (!r.passed && r.example_en) {
      html += `<div style='margin-top:6px;font-size:13px'>💡 <em class="translatable" title="Ejemplo">${Profile.personalize(r.example_en)}</em></div>`;
    }
    fb.innerHTML = html;
  }

  function _finish() {
    document.getElementById("chat-input-zone").classList.add("hidden");
    document.getElementById("chat-complete").classList.remove("hidden");
    const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    document.getElementById("chat-final-score").innerHTML =
      `<span class="translatable" title="Tu score promedio">Your average score: <strong>${Math.round(avg * 100)}%</strong></span>`;
    _scrollChat();
  }

  function _scrollChat() {
    setTimeout(() => window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }), 50);
  }

  // ---- Mic en el chat ----
  function _initMic() {
    const btn = document.getElementById("btn-chat-mic");
    if (!btn) return;
    const input = document.getElementById("chat-input");

    async function start() {
      if (chatRecording) return;
      if (!Speech.supported) {
        UI.toast("Mic not supported. Type your answer instead.", { type: "warn" });
        return;
      }
      if (!Speech.canUseMic()) {
        UI.toast(
          "Mic unavailable in this browser. Use Chrome/Edge, or type your answer.",
          { type: "warn", duration: 4500 }
        );
        return;
      }
      chatRecording = true;
      btn.classList.add("recording");
      await Speech.start({
        onResult: ({ final, interim }) => {
          if (Speech.isLive()) input.value = (final + " " + interim).trim();
        },
        onEnd: ({ transcript }) => {
          chatRecording = false;
          btn.classList.remove("recording");
          if (transcript) input.value = transcript;
        },
      });
    }
    async function stop() {
      if (!chatRecording) return;
      await Speech.stop({ uploadFn: API.uploadAudio });
    }

    btn.addEventListener("touchstart", (e) => { e.preventDefault(); start(); });
    btn.addEventListener("touchend", (e) => { e.preventDefault(); stop(); });
    btn.addEventListener("mousedown", start);
    btn.addEventListener("mouseup", stop);
    btn.addEventListener("mouseleave", () => { if (chatRecording) stop(); });
  }

  function init() {
    document.getElementById("show-adult").addEventListener("change", _renderFiltered);
    document.getElementById("btn-chat-send").onclick = _submitUserTurn;
    document.getElementById("chat-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        _submitUserTurn();
      }
    });

    // Botones del modo word-order
    document.querySelectorAll(".input-mode-btn").forEach(b => {
      b.onclick = () => _setInputMode(b.dataset.inputMode);
    });
    document.getElementById("btn-order-send").onclick = _submitUserTurn;
    document.getElementById("btn-order-clear").onclick = _clearOutput;
    document.getElementById("btn-order-shuffle").onclick = _shuffleBank;
    _applyInputMode();
    const voiceSel = document.getElementById("chat-voice-select");
    if (voiceSel) {
      voiceSel.value = TTS.getVoice();
      voiceSel.onchange = () => { TTS.setVoice(voiceSel.value); };
    }
    _initMic();
  }

  return { renderList, start, init };
})();
