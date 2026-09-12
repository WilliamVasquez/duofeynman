// Lista de diálogos + chat de role-play.
const Dialogues = (() => {
  let allDialogues = [];
  let current = null;          // dialogue cargado completo
  let turnIndex = 0;           // turno actual
  let scores = [];             // scores de cada turno user
  let chatRecording = false;
  let sessionVersion = 0;
  let submitting = false;
  let savedSession = null;
  let pendingResponse = null;
  let usedHelp = false;
  let typedWithMic = false;

  function responseId() {
    if (crypto.randomUUID) return crypto.randomUUID();
    // randomUUID exige HTTPS; getRandomValues también sirve en la LAN local.
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
    const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
  }

  function stop() {
    sessionVersion++;
    current = null;
    savedSession = null;
    pendingResponse = null;
    submitting = false;
  }

  function _later(callback, delay) {
    const version = sessionVersion;
    setTimeout(() => { if (version === sessionVersion) callback(); }, delay);
  }

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
  // Modo de input: "choose" | "type" | "order"
  // Default "choose": el usuario siempre ve qué puede responder. Antes
  // arrancaba en "type" con la pantalla en blanco y sin guía.
  // Key con sufijo _v2 a propósito: la vieja guardaba "type" y hacía que
  // quien ya usó la app nunca viera el modo nuevo. Con el bump, todos
  // vuelven al default una vez y después se respeta lo que elijan.
  const INPUT_MODE_KEY = "duofeynman_input_mode_v2";
  let inputMode = Store.get(INPUT_MODE_KEY) || "choose";
  // Estado del modo choose
  let answerOptions = [];      // [{en, es}]
  let chosenIndex = -1;
  // Estado del word-order
  let bankWords = [];      // palabras disponibles {id, text}
  let outputWords = [];    // palabras seleccionadas en orden

  async function renderList() {
    const root = document.getElementById("dialogues-list");
    root.innerHTML = `
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
    `;
    try {
      allDialogues = await API.dialoguesList();
      _renderFiltered();
    } catch (err) {
      root.innerHTML = `<p style='color:red'>${_escapeHtml(err.message)}</p>`;
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
          ${I18n.html(Profile.personalize(d.title_en), Profile.personalize(d.title_es))}
          ${d.is_adult ? '<span class="adult-badge">+18</span>' : ''}
        </div>
        <div class="dlg-desc">${I18n.html(Profile.personalize(d.setting_en), Profile.personalize(d.setting_es))}</div>
        <div class="dlg-meta">${d.level} · Difficulty ${"●".repeat(d.difficulty)} · ${_escapeHtml(Profile.personalize(d.npc_name))}</div>
        <div class="dlg-progress">${d.progress ? `${d.progress.completed_runs} completed · ${d.progress.recommended_mode === 'type' ? 'Write / Speak' : d.progress.recommended_mode}` : ''}</div>
        <button type="button" class="btn btn-small dlg-start">${d.progress?.resumable ? 'Resume conversation' : 'Start conversation'}</button>
      </div>
      <button class="dlg-hide-btn" title="No me sirve, ocultar">✕</button>
    `;
    card.querySelector(".dlg-body").onclick = () => start(d.id);
    card.querySelector(".dlg-start").onclick = e => { e.stopPropagation(); start(d.id); };
    card.querySelector(".dlg-icon").onclick = () => start(d.id);
    card.querySelector(".dlg-hide-btn").onclick = async (e) => {
      e.stopPropagation();
      if (confirm(`Hide "${d.title_en}"? You can restore it from My profile.`)) {
        await Profile.hideItem("dialogues", d.slug);
        _renderFiltered();
      }
    };
    return card;
  }

  async function start(dialogueId) {
    const version = ++sessionVersion;
    submitting = false;
    try {
      const saved = await API.dialogueStart(dialogueId);
      if (version !== sessionVersion) return;
      current = saved.dialogue;
      savedSession = saved.session;
      pendingResponse = null;
      turnIndex = savedSession.cursor;
      usedHelp = false; typedWithMic = false;
      scores = savedSession.responses.map(r => r.score);
      inputMode = savedSession.recommended_mode;
      _applyInputMode();
      UI.show("view-chat");
      const oldBanner = document.getElementById("profile-banner");
      if (oldBanner) oldBanner.remove();

      // Título: EN como protagonista, ES como tooltip + click para expandir
      const titleEn = Profile.personalize(current.title_en);
      const titleEs = Profile.personalize(current.title_es);
      const titleEl = document.getElementById("chat-title");
      titleEl.innerHTML = I18n.html(titleEn, titleEs);

      // Scene context: SIEMPRE VISIBLE en inglés. Click sobre el texto inglés
      // → muestra la traducción ES inline debajo (sin ocultar el inglés).
      const setting = document.getElementById("chat-setting");
      const settingEs = Profile.personalize(current.setting_es);
      const settingEn = Profile.personalize(current.setting_en || current.setting_es);
      setting.innerHTML = `
        <div class="setting-label">📍 Scene context</div>
        <div class="setting-text">${I18n.html(settingEn, settingEs)}</div>
      `;

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
            <div class="profile-banner-text hidden translatable" title="${_escapeAttr(banner.es)} (click for Spanish)">${_escapeHtml(banner.en)}</div>
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
      const advice = document.createElement('p');
      advice.className = 'practice-advice';
      advice.innerHTML = I18n.html(`Suggested: ${inputMode === 'type' ? 'Write / Speak' : inputMode}. Two clean conversations unlock less support. You can change modes anytime.`, 'Sugerencia según tu progreso. Dos conversaciones sin errores permiten reducir ayudas. Podés cambiar de modo cuando quieras.');
      document.getElementById('chat-messages').appendChild(advice);
      // El guion guardado no depende de IDs de turnos que el seed recree.
      for (let i = 0; i < turnIndex; i++) {
        const previous = current.turns[i];
        if (previous.speaker === 'NPC') _renderNpcMessage(previous);
        else savedSession.responses.filter(r => r.turn_index === i).forEach(r => _renderUserMessage(r.text));
      }
      if (turnIndex > 0 && current.turns[turnIndex - 1]?.speaker === 'NPC') {
        _later(() => TTS.speak(Profile.personalize(current.turns[turnIndex - 1].npc_text_en)), 200);
      }
      _nextTurn();
      const unfinished = savedSession.responses.filter(r => r.turn_index === turnIndex);
      unfinished.forEach(r => _renderUserMessage(r.text));
      if (unfinished.length) {
        const last = unfinished[unfinished.length - 1];
        usedHelp = unfinished.some(r => r.used_help);
        _renderTurnFeedback({...last.result, response_id: last.id});
      }
    } catch (err) {
      UI.toast("Error: " + err.message, { type: "error" });
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
      _later(() => TTS.speak(Profile.personalize(turn.npc_text_en)), 200);
      turnIndex++;
      // Si el siguiente es USER, mostrar input
      const nextTurn = current.turns[turnIndex];
      if (nextTurn && nextTurn.speaker === "USER") {
        _showUserInput(nextTurn);
      } else if (nextTurn && nextTurn.speaker === "NPC") {
        // Dos NPC seguidos: esperar un poco y mostrar
        _later(() => _nextTurn(), 1800);
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

  // Escapa texto que se inyecta como contenido HTML (no atributo).
  function _escapeHtml(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /** Hace clickeable un elemento que tiene texto en inglés.
   * Al click, INSERTA un <span class="es-inline"> con la traducción debajo
   * SIN ocultar el inglés. Click otra vez → la quita.
   */
  function _wireTranslatable(el, esText) {
    if (!el || !esText) return;
    el.tabIndex = 0;
    if (el.tagName !== "BUTTON") el.setAttribute("role", "button");
    el.setAttribute("aria-expanded", "false");
    el.addEventListener("keydown", e => {
      if (el.tagName !== "BUTTON" && ["Enter", " "].includes(e.key)) { e.preventDefault(); el.click(); }
    });
    el.classList.add("translatable");
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      // Si ya está expandido, lo cerramos
      const next = el.nextElementSibling;
      if (next && next.classList.contains("es-inline")) {
        next.remove();
        el.setAttribute("aria-expanded", "false");
        return;
      }
      const span = document.createElement("div");
      span.className = "es-inline";
      span.lang = "es";
      span.textContent = esText;
      el.insertAdjacentElement("afterend", span);
      el.setAttribute("aria-expanded", "true");
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
      <span class="speaker">${_escapeHtml(npcName)}</span>
      <div class="msg-en translatable"${hasTrans ? ` title="${_escapeAttr(textEs)} (click for translation)"` : ""}>${_escapeHtml(textEn)}</div>
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
    // Escapar input del usuario: sin esto, HTML tipeado se inyecta (XSS)
    div.innerHTML = `<span class="speaker">Vos</span>${_escapeHtml(text)}`;
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
    hintBtn.addEventListener('click', () => { usedHelp = true; _applyInputMode(); });
    _wireTranslatable(hintBtn, hintText);
    const chips = document.getElementById("helper-chips");
    chips.innerHTML = "";
    (turn.helper_phrases || []).forEach(p => {
      const personalizedPhrase = Profile.personalize(p);
      const b = document.createElement("button");
      b.className = "helper-chip";
      b.textContent = personalizedPhrase;
      b.onclick = () => {
        usedHelp = true;
        const inp = document.getElementById("chat-input");
        inp.value = inp.value ? inp.value + " " + personalizedPhrase : personalizedPhrase;
        inp.focus();
      };
      chips.appendChild(b);
    });
    document.getElementById("chat-input").value = "";
    document.getElementById("chat-turn-feedback").classList.add("hidden");

    // Preparar word bank desde la respuesta modelo (personalizada)
    const exampleEn = Profile.personalize(turn.user_example_en || "");
    _setupWordBank(exampleEn);
    _setupChoices(turn);

    // Sesgar el STT hacia lo que esperamos en este turno: frases de ayuda +
    // PALABRAS (no frases completas) de la respuesta modelo y de las opciones.
    // Sesgar con la oración objetivo entera hace que Whisper la "escuche"
    // igual: el ejercicio se autoaprueba y le esconde al usuario sus errores.
    Speech.setExpectedVocab([
      ...(turn.helper_phrases || []).map(p => Profile.personalize(p)),
      ...answerOptions.flatMap(o => o.en.split(/\s+/)).filter(w => w.length > 2),
      ...exampleEn.split(/\s+/).filter(w => w.length > 2),
    ]);
    _applyInputMode();

    if (inputMode === "type") document.getElementById("chat-input").focus();
    _scrollChat();
  }

  // ---- Modo Choose: elegir una respuesta completa ----

  /** Arma las opciones del turno.
   * Fuente principal: `answer_options` del curriculum ([{en, es}]), todas
   * válidas y todas aceptadas por el motor.
   * Fallback (turnos que todavía no tienen opciones escritas): la respuesta
   * modelo + las helper_phrases, sin traducción.
   */
  function _setupChoices(turn) {
    const opts = (turn.answer_options || [])
      .filter(o => o && o.en)
      .map(o => ({ en: Profile.personalize(o.en), es: Profile.personalize(o.es || "") }));

    if (opts.length) {
      answerOptions = opts;
    } else {
      const seen = new Set();
      answerOptions = [
        turn.user_example_en || "",
        ...(turn.helper_phrases || []),
      ]
        .map(t => Profile.personalize(t))
        .filter(t => {
          const key = t.trim().toLowerCase();
          if (!key || seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .map(t => ({ en: t, es: "" }));
    }
    chosenIndex = -1;
    _renderChoices();
  }

  function _renderChoices() {
    const box = document.getElementById("choose-options");
    if (!box) return;
    box.innerHTML = "";
    if (!answerOptions.length) {
      box.innerHTML = `<span class="choose-empty">No options for this turn. Use ✍️ Write / Speak.</span>`;
      return;
    }
    answerOptions.forEach((opt, i) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "choose-option" + (i === chosenIndex ? " chosen" : "");
      card.setAttribute("role", "option");
      card.setAttribute("aria-selected", i === chosenIndex ? "true" : "false");
      // Inmersión: solo inglés visible. El español se agrega debajo con el
      // botón ES, sin ocultar el inglés (convención del proyecto).
      card.innerHTML = `<span class="choose-option-en">${_escapeHtml(opt.en)}</span>`;
      card.onclick = () => {
        chosenIndex = (chosenIndex === i) ? -1 : i;
        _renderChoices();
      };

      const row = document.createElement("div");
      row.className = "choose-option-row";
      row.appendChild(card);

      if (opt.es) {
        const esBtn = document.createElement("button");
        esBtn.type = "button";
        esBtn.className = "choose-es-btn";
        esBtn.textContent = "ES";
        esBtn.title = `${opt.es} (click para ver en español)`;
        esBtn.onclick = (e) => {
          e.stopPropagation();
          const existing = row.nextElementSibling;
          if (existing && existing.classList.contains("es-inline")) {
            existing.remove();
            return;
          }
          const span = document.createElement("div");
          span.className = "es-inline";
          span.lang = "es";
          span.textContent = opt.es;
          row.insertAdjacentElement("afterend", span);
        };
        row.appendChild(esBtn);
      }
      box.appendChild(row);
    });
  }

  function _getChosenText() {
    return chosenIndex >= 0 ? (answerOptions[chosenIndex].en || "").trim() : "";
  }

  function _listenChosen() {
    const text = _getChosenText();
    if (!text) { UI.toast("Pick an answer first.", { type: "warn" }); return; }
    TTS.speak(text);
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
    document.getElementById("chat-toolbar-choose").classList.toggle("hidden", inputMode !== "choose");
    document.getElementById("chat-toolbar-type").classList.toggle("hidden", inputMode !== "type");
    document.getElementById("chat-toolbar-order").classList.toggle("hidden", inputMode !== "order");
    // Las helper_phrases son atajos para escribir; en modo choose estorban
    // (ya tenés respuestas completas) y en order no aplican.
    const chips = document.getElementById("helper-chips");
    if (chips) chips.classList.toggle("hidden", inputMode !== "type" || !usedHelp);
  }

  function _setInputMode(mode) {
    inputMode = mode;
    Store.set(INPUT_MODE_KEY, mode);
    _applyInputMode();
  }

  async function _submitUserTurn() {
    if (!current || submitting) return;
    const version = sessionVersion;
    const turn = current.turns[turnIndex];
    if (!turn || turn.speaker !== "USER") return;
    const input = document.getElementById("chat-input");
    let text = "";
    if (inputMode === "choose") {
      text = _getChosenText();
      if (!text) { UI.toast("Pick one of the answers first.", { type: "warn" }); return; }
    } else if (inputMode === "order") {
      text = _getOrderedText().trim();
      if (!text) { UI.toast("Tap the words to build a sentence.", { type: "warn" }); return; }
    } else {
      text = input.value.trim();
      if (!text) return;
    }

    submitting = true;
    try {
      const mode = inputMode === 'type' && typedWithMic ? 'speak' : inputMode;
      if (!pendingResponse || pendingResponse.user_text !== text || pendingResponse.mode !== mode) {
        pendingResponse = {turn_id: turn.id, user_text: text, mode, used_help: usedHelp,
          session_id: savedSession.id, run_number: savedSession.run_number, response_id: responseId()};
      }
      const result = await API.dialogueCheck(pendingResponse);
      if (version !== sessionVersion) return;
      savedSession = result.session;
      pendingResponse = null;
      _renderUserMessage(text);
      _renderTurnFeedback(result);
      scores.push(result.score);
      input.value = "";

      if (result.passed) {
        _advanceTurn();
      } else {
        submitting = false;
        // No avanzamos automáticamente, pero el feedback muestra un botón
        // "Continue" (ver _renderTurnFeedback): nunca queda trabado.
      }
    } catch (err) {
      if (version !== sessionVersion) return;
      submitting = false;
      UI.toast("Error: " + err.message, { type: "error" });
    }
  }

  /** Avanza al turno siguiente y limpia el estado de todos los modos de input. */
  function _advanceTurn() {
    turnIndex++;
    document.getElementById("chat-input-zone").classList.add("hidden");
    outputWords = []; bankWords = [];
    answerOptions = []; chosenIndex = -1;
    usedHelp = false; typedWithMic = false;
    _later(() => { submitting = false; _nextTurn(); }, 1200);
  }

  function _renderTurnFeedback(r) {
    const fb = document.getElementById("chat-turn-feedback");
    fb.classList.remove("hidden");
    fb.classList.toggle("pass", r.passed);
    fb.classList.toggle("fail", !r.passed);
    fb.innerHTML = "";

    const head = document.createElement("div");
    head.className = "fb-head";
    head.innerHTML = `<strong>${Math.round(r.score * 100)}%</strong> · <span>${r.passed ? "Good!" : "Hmm, not quite"}</span>`;
    fb.appendChild(head);

    // El motivo VA VISIBLE. Antes vivía en un title= y en móvil no se veía:
    // el usuario veía "Try again" sin saber qué arreglar.
    if (r.feedback_es) {
      const why = document.createElement("div");
      why.className = "fb-why";
      why.innerHTML = I18n.html(r.feedback_en || 'Review this answer and try again.', r.feedback_es);
      fb.appendChild(why);
    }

    if (!r.passed && r.example_en) {
      const ex = document.createElement("div");
      ex.className = "fb-example";
      ex.innerHTML = `💡 <em>${_escapeHtml(Profile.personalize(r.example_en))}</em>`;
      const listen = document.createElement("button");
      listen.type = "button";
      listen.className = "fb-listen";
      listen.textContent = "🔊";
      listen.title = "Escuchar el ejemplo";
      listen.onclick = () => TTS.speak(Profile.personalize(r.example_en));
      ex.appendChild(listen);
      fb.appendChild(ex);
    }

    // Salida de emergencia: si el motor rule-based no reconoce una respuesta
    // igualmente válida, el usuario puede seguir. Nunca callejón sin salida.
    if (!r.passed && r.can_continue) {
      const actions = document.createElement("div");
      actions.className = "fb-actions";
      const cont = document.createElement("button");
      cont.type = "button";
      cont.className = "btn-ghost fb-continue";
      cont.textContent = "Continue anyway →";
      cont.title = "Seguir igual: tu respuesta puede estar bien aunque no la reconozca";
      cont.onclick = async () => {
        if (submitting) return;
        const version = sessionVersion;
        submitting = true;
        try {
          const state = await API.dialogueContinue(savedSession.id, r.response_id);
          if (version !== sessionVersion) return;
          savedSession = state; _advanceTurn();
        } catch (err) { if (version !== sessionVersion) return; submitting = false; UI.toast(err.message, {type: 'error'}); }
      };
      actions.appendChild(cont);
      fb.appendChild(actions);
    }
  }

  function _finish() {
    document.getElementById("chat-input-zone").classList.add("hidden");
    document.getElementById("chat-complete").classList.remove("hidden");
    const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    document.getElementById("chat-final-score").innerHTML =
      `<span class="translatable" title="Tu score promedio">Your average score: <strong>${Math.round(avg * 100)}%</strong></span>`;
    if (savedSession) document.getElementById('chat-final-score').insertAdjacentHTML('beforeend',
      `<p>${I18n.html(`Saved · ${savedSession.completed_runs} conversations completed. Next suggestion: ${savedSession.recommended_mode === 'type' ? 'Write / Speak' : savedSession.recommended_mode}.`, 'Progreso guardado. Las ayudas sugeridas cambian según tus recorridos sin errores.')}</p>`);
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
          if (transcript) { input.value = transcript; typedWithMic = true; }
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

  let _inited = false;
  function init() {
    if (_inited) return;   // evitar listeners duplicados si se llama de nuevo
    _inited = true;
    document.getElementById('chat-input-zone').addEventListener('click', e => {
      if (e.target.closest('#helper-chips,.user-hint,.hint-chip')) usedHelp = true;
    });
    document.getElementById('chat-input').addEventListener('input', () => { typedWithMic = false; });
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
    document.getElementById("btn-choose-send").onclick = _submitUserTurn;
    document.getElementById("btn-choose-listen").onclick = _listenChosen;
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

  return { renderList, start, init, stop };
})();
