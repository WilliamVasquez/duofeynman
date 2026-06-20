// Orquestador principal de DuoFeynman.
(function () {
  let currentTopic = null;
  let currentAttemptId = null;
  let currentMode = "speak";

  // ---- Tema claro/oscuro ----
  function _applyTheme(dark) {
    if (dark) document.documentElement.setAttribute("data-theme", "dark");
    else document.documentElement.removeAttribute("data-theme");
    Store.set("duofeynman_theme", dark ? "dark" : "light");
    document.querySelectorAll(".theme-toggle").forEach(b => { b.textContent = dark ? "☀️" : "🌙"; });
  }
  // Inyectar botón 🌙 en cada topbar
  document.querySelectorAll(".topbar").forEach(tb => {
    const btn = document.createElement("button");
    btn.className = "theme-toggle";
    btn.title = "Cambiar tema claro/oscuro";
    btn.setAttribute("aria-label", "Cambiar tema");
    btn.textContent = document.documentElement.getAttribute("data-theme") === "dark" ? "☀️" : "🌙";
    btn.onclick = () => _applyTheme(document.documentElement.getAttribute("data-theme") !== "dark");
    (tb.querySelector(".user-info") || tb).appendChild(btn);
  });

  // ---- Auth ----
  document.querySelectorAll(".tab").forEach(t => {
    t.onclick = () => {
      document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
      document.querySelectorAll(".auth-form").forEach(f => f.classList.remove("active"));
      t.classList.add("active");
      document.getElementById(`form-${t.dataset.tab}`).classList.add("active");
      UI.authError("");
    };
  });

  document.getElementById("form-login").onsubmit = async (e) => {
    e.preventDefault();
    UI.authError("");
    const fd = new FormData(e.target);
    try {
      const data = await API.login({ email: fd.get("email"), password: fd.get("password") });
      API.setSession(data.access_token, data.user);
      await enterApp();
    } catch (err) { UI.authError(err.message); }
  };

  document.getElementById("form-register").onsubmit = async (e) => {
    e.preventDefault();
    UI.authError("");
    const fd = new FormData(e.target);
    try {
      const data = await API.register({
        username: fd.get("username"),
        email: fd.get("email"),
        password: fd.get("password"),
        target_level: "A1",
      });
      API.setSession(data.access_token, data.user);
      await enterApp();
    } catch (err) { UI.authError(err.message); }
  };

  document.getElementById("btn-logout").onclick = () => {
    API.clear();
    location.reload();
  };

  // ---- Botones "← Volver" generales ----
  document.querySelectorAll(".btn-back-home").forEach(b => {
    b.onclick = async () => {
      Speech.stop().catch(() => {});
      TTS.stop();
      await refreshHeader();
      UI.show("view-home");
    };
  });

  // ---- Home ----
  async function enterApp() {
    await refreshHeader();
    UI.show("view-home");
    // Cargar perfil del server (con fallback a localStorage si no hay internet)
    await Profile.loadFromServer();
    // Saber si el server tiene Vosk para guiar al usuario con el micrófono
    try {
      const stt = await API.sttStatus();
      Speech.setServerVoskAvailable(stt.vosk_available);
    } catch {
      Speech.setServerVoskAvailable(false);
    }
    _renderProfileCard();
    try {
      const [modules, dueCount, dialogues] = await Promise.all([
        API.modules(),
        SRS.dueCount(),
        API.dialoguesList().catch(() => []),
      ]);
      UI.renderModules(modules, openTopic);
      document.getElementById("srs-due-count").textContent = dueCount;
      _renderWeekPanel(dialogues);
    } catch (err) {
      console.error(err);
    }
  }

  function _renderProfileCard() {
    const el = document.getElementById("profile-card");
    if (!el) return;
    const summary = Profile.summary();
    if (!summary) {
      el.classList.add("hidden");
      return;
    }
    el.classList.remove("hidden");
    el.innerHTML = `<span class="profile-icon">👤</span><span>${summary}</span>`;
  }

  function _renderWeekPanel(dialogues) {
    const el = document.getElementById("week-panel");
    if (!el) return;

    const profile = Profile.get();
    const profileFilled = Profile.isFilled();

    // Si no hay perfil llenado, invitamos a llenarlo
    if (!profileFilled) {
      el.innerHTML = `
        <div class="week-cta">
          <div class="week-cta-icon">👤</div>
          <div>
            <h4>Personalizá tu app</h4>
            <p>Llená "Mi perfil" para que la app te muestre solo lo que te sirve y te haga recomendaciones de la semana.</p>
            <button class="btn-primary" data-action="profile">Llenar mi perfil</button>
          </div>
        </div>
      `;
      el.querySelector("button").onclick = () => _openView("profile");
      return;
    }

    // Filtrar por intereses + hidden + adult
    const hidden = Profile.getHidden().dialogues;
    const interests = profile.interests || {};
    const candidates = dialogues.filter(d => {
      if (hidden.includes(d.slug)) return false;
      if (d.is_adult && !interests.adult) return false;
      // Necesitamos identificar a qué categoría/interés pertenece
      const axis = _findAxisInList(d.slug);
      if (axis && interests[axis.interest] === false) return false;
      return true;
    });

    if (!candidates.length) {
      el.innerHTML = `<div class="empty-state"><p>No hay conversaciones activas para vos. Activá áreas en Mi perfil.</p></div>`;
      return;
    }

    // 3 picks deterministas para la semana (semilla = año + semana)
    const seed = _weekSeed();
    const picks = _pickN(candidates, 3, seed);

    const days = ["Lun", "Mié", "Vie"];
    el.innerHTML = `
      <h4 class="section-title">📅 Tu semana en inglés</h4>
      <div class="week-list">
        ${picks.map((d, i) => `
          <div class="week-item" data-id="${d.id}">
            <span class="week-day">${days[i]}</span>
            <span class="week-icon">${d.icon}</span>
            <div class="week-body">
              <div class="week-title">${d.title_es}</div>
              <div class="week-meta">${d.level} · Dificultad ${"●".repeat(d.difficulty)}</div>
            </div>
            <span class="week-go">→</span>
          </div>
        `).join("")}
      </div>
    `;
    el.querySelectorAll(".week-item").forEach(item => {
      item.onclick = async () => {
        const id = parseInt(item.dataset.id, 10);
        // Disparar Dialogues.start(id)
        UI.show("view-chat");
        await Dialogues.start(id);
      };
    });
  }

  function _findAxisInList(slug) {
    // Las LIFE_AXES están en dialogues.js — replicamos aquí mapping mínimo por simplicidad.
    // Para reducir duplicación, exponemos via Dialogues si más adelante hace falta.
    // Por ahora, todos los slugs sin mapeo pasan el filtro.
    const AXIS_OF_SLUG = {
      "daily-standup":"work","work-call-tech":"work","first-day-onboarding":"work",
      "team-meeting-propose":"work","tough-feedback":"work","explain-project":"work",
      "job-interview":"work","salary-raise":"work","client-negotiation":"work",
      "interview-experiences":"work","negotiate-salary-offer":"work","small-business-pitch":"work",
      "debugging-call":"work","detective-deduction":"work",
      "describe-someone-i-met":"relationship",
      "catching-up-coworker":"social",
      "spouse-after-work":"relationship","couple-hard-talk":"relationship",
      "couple-finances":"relationship","romantic-dinner-ask-out":"relationship","deep-talk":"relationship",
      "intimate-motel":"adult","spicy-couple-talk":"adult",
      "uber-ride":"shopping","restaurant-order":"shopping","supermarket":"shopping",
      "ask-directions":"shopping","food-allergies":"shopping","bank-open-account":"shopping",
      "complain-service":"shopping",
      "doctor-visit":"health","vet-visit":"health","emergency-911":"health","serious-apology":"health",
      "party-meet":"social","phone-call-simple":"social","reconnect-old-friend":"social","give-condolences":"social",
      "tell-life-story":"social","hypothetical-life":"social","deep-life-reflection":"social",
      "gossip-friend":"social","talk-about-news":"social",
      "christmas-in-laws":"family",
      "tech-store-camera":"shopping","used-car-buy":"shopping","rent-apartment":"shopping",
      "airport-checkin":"travel","hotel-checkin":"travel","immigration-airport":"travel","missed-flight":"travel",
    };
    const interest = AXIS_OF_SLUG[slug];
    return interest ? { interest } : null;
  }

  // Determinista por semana del año (para que "Tu semana" no cambie cada vez que entrás)
  function _weekSeed() {
    const now = new Date();
    const start = new Date(now.getFullYear(), 0, 1);
    const diff = (now - start) / (1000 * 60 * 60 * 24 * 7);
    return now.getFullYear() * 100 + Math.floor(diff);
  }

  function _pickN(arr, n, seed) {
    // RNG simple basado en seed
    let s = seed >>> 0;
    function rand() { s = (s * 1664525 + 1013904223) >>> 0; return s / 0x100000000; }
    const copy = [...arr];
    const out = [];
    for (let i = 0; i < n && copy.length; i++) {
      const idx = Math.floor(rand() * copy.length);
      out.push(copy.splice(idx, 1)[0]);
    }
    return out;
  }

  function _openView(action) {
    const btn = document.querySelector(`.quick-btn[data-action="${action}"]`);
    if (btn) btn.click();
  }

  async function refreshHeader() {
    try {
      const me = await API.me();
      UI.setUserHeader(me);
    } catch {
      UI.setUserHeader(API.getUser());
    }
  }

  // ---- Quick actions ----
  document.querySelectorAll(".quick-btn").forEach(b => {
    b.onclick = async () => {
      const a = b.dataset.action;
      if (a === "dashboard") {
        UI.show("view-dashboard");
        await Dashboard.render();
      } else if (a === "srs") {
        UI.show("view-srs");
        await SRS.render(openTopic);
      } else if (a === "dictation") {
        UI.show("view-dictation");
        await Dictation.load();
      } else if (a === "dialogues") {
        UI.show("view-dialogues");
        await Dialogues.renderList();
      } else if (a === "profile") {
        UI.show("view-profile");
        ProfileView.render();
      }
    };
  });

  // Botones de volver a la lista de diálogos
  document.querySelectorAll(".btn-back-dialogues").forEach(b => {
    b.onclick = async () => {
      Speech.stop().catch(() => {});
      TTS.stop();
      UI.show("view-dialogues");
      await Dialogues.renderList();
    };
  });

  // ---- Práctica ----
  async function openTopic(topic) {
    currentTopic = topic;
    currentMode = "speak";
    setMode("speak");
    UI.renderTopic(topic);
    UI.show("view-practice");
    await ensureAttempt();
  }

  async function ensureAttempt() {
    try {
      const att = await API.startAttempt(currentTopic.id, currentMode);
      currentAttemptId = att.id;
    } catch (err) {
      UI.toast("No se pudo iniciar el intento: " + err.message, { type: "error", duration: 4000 });
    }
  }

  document.getElementById("btn-listen-example").onclick = () => {
    if (currentTopic) TTS.speak(currentTopic.example_en);
  };

  document.getElementById("btn-listen-model").onclick = () => {
    const t = document.getElementById("model-answer").textContent;
    if (t) TTS.speak(t);
  };

  // ---- Toggle modo Hablar/Escribir ----
  document.querySelectorAll(".mode-btn").forEach(b => {
    b.onclick = () => setMode(b.dataset.mode);
  });

  function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll(".mode-btn").forEach(b => {
      b.classList.toggle("active", b.dataset.mode === mode);
    });
    document.querySelectorAll("#mode-speak, #mode-write").forEach(z => z.classList.remove("active"));
    document.getElementById(`mode-${mode}`).classList.add("active");
    document.getElementById("feedback").classList.add("hidden");

    if (mode === "speak") {
      const hint = document.getElementById("record-hint");
      if (Speech.mode === "webspeech") {
        hint.textContent = "🎤 Hablá en inglés. El texto aparece en vivo.";
      } else if (Speech.mode === "recorder" && Speech.getServerVoskAvailable()) {
        hint.textContent = "🎤 Transcripción offline (Vosk). El texto aparece al soltar.";
      } else if (Speech.mode === "recorder") {
        hint.innerHTML = "⚠️ El micrófono no está configurado en este navegador. <strong>Usá Chrome/Edge</strong>, o activá <strong>el modo Escribir</strong>.";
      } else {
        hint.textContent = "⚠️ Tu navegador no permite grabar. Usá el modo Escribir.";
      }
    }
  }

  // ---- Modo Hablar ----
  const btnRec = document.getElementById("btn-record");
  let recActive = false;

  async function startRec() {
    if (recActive) return;
    if (!Speech.supported) {
      UI.toast("Mic not supported in this browser. Use the Write mode.", { type: "warn", duration: 3500 });
      return;
    }
    if (!Speech.canUseMic()) {
      UI.toast(
        "Mic unavailable: Firefox needs server-side Vosk (not configured). Use Chrome/Edge, or switch to Write mode.",
        { type: "warn", duration: 5000 }
      );
      return;
    }
    document.getElementById("transcript").textContent = "";
    document.getElementById("feedback").classList.add("hidden");
    btnRec.classList.add("recording");
    btnRec.querySelector(".record-label").textContent = "Escuchando... soltá para enviar";
    recActive = true;
    const ok = await Speech.start({
      onResult: ({ final, interim }) => {
        if (Speech.isLive()) {
          document.getElementById("transcript").textContent = (final + " " + interim).trim();
        }
      },
      onEnd: async ({ transcript, duration }) => {
        btnRec.classList.remove("recording");
        btnRec.querySelector(".record-label").textContent = "Mantené presionado para hablar";
        recActive = false;
        if (!transcript) {
          document.getElementById("record-hint").textContent = "No te escuché. Probá de nuevo o usá Escribir.";
          return;
        }
        document.getElementById("transcript").textContent = transcript;
        await sendRound(transcript, duration, "speak");
      },
      onStatus: (msg) => { document.getElementById("record-hint").textContent = msg; },
    });
    if (!ok) {
      btnRec.classList.remove("recording");
      btnRec.querySelector(".record-label").textContent = "Mantené presionado para hablar";
      recActive = false;
    }
  }

  async function stopRec() {
    if (!recActive) return;
    await Speech.stop({
      uploadFn: API.uploadAudio,
      onStatus: (msg) => { document.getElementById("record-hint").textContent = msg; },
    });
  }

  btnRec.addEventListener("touchstart", (e) => { e.preventDefault(); startRec(); });
  btnRec.addEventListener("touchend", (e) => { e.preventDefault(); stopRec(); });
  btnRec.addEventListener("touchcancel", () => stopRec());
  btnRec.addEventListener("mousedown", () => startRec());
  btnRec.addEventListener("mouseup", () => stopRec());
  btnRec.addEventListener("mouseleave", () => { if (recActive) stopRec(); });

  // ---- Modo Escribir ----
  const writeArea = document.getElementById("write-area");
  const writeWords = document.getElementById("write-words");
  writeArea.addEventListener("input", () => {
    const count = (writeArea.value.trim().match(/\S+/g) || []).length;
    writeWords.textContent = count;
  });

  document.getElementById("btn-submit-write").onclick = async () => {
    const text = writeArea.value.trim();
    if (text.length < 3) { UI.toast("Escribí al menos una oración.", { type: "warn" }); return; }
    document.getElementById("feedback").classList.add("hidden");
    await sendRound(text, 0, "write");
  };

  async function sendRound(transcript, duration, mode) {
    // Si el intento no se pudo crear antes (error de red), reintentar acá.
    if (!currentAttemptId) {
      await ensureAttempt();
      if (!currentAttemptId) {
        UI.toast("No hay un intento activo. Reintentá en unos segundos.", { type: "error", duration: 4000 });
        return;
      }
    }
    const sendBtn = mode === "write"
      ? document.getElementById("btn-submit-write")
      : null;
    if (sendBtn) { sendBtn.disabled = true; sendBtn.classList.add("btn-busy"); }
    try {
      const fb = await API.submitRound({
        attempt_id: currentAttemptId, transcript, duration_seconds: duration || 0, mode,
      });
      UI.renderFeedback(fb);
      _showAchievementsToast(fb.unlocked_achievements);
      await refreshHeader();
      window.scrollTo({ top: document.getElementById("feedback").offsetTop - 20, behavior: "smooth" });
    } catch (err) {
      UI.toast("Error al enviar: " + err.message, { type: "error", duration: 4000 });
    } finally {
      if (sendBtn) { sendBtn.disabled = false; sendBtn.classList.remove("btn-busy"); }
    }
  }

  function _showAchievementsToast(achs) {
    const t = document.getElementById("achievements-toast");
    if (!achs || !achs.length) { t.classList.add("hidden"); return; }
    UI.confetti();
    t.classList.remove("hidden");
    t.innerHTML = `
      <div class="toast-title">🎉 ¡Logro${achs.length > 1 ? "s" : ""} desbloqueado${achs.length > 1 ? "s" : ""}!</div>
      <div class="toast-list">${achs.map(a => `<strong>${UI.escape(a.title_es)}</strong> (+${UI.escape(a.xp)} XP)`).join(" · ")}</div>
    `;
  }

  document.getElementById("btn-try-again").onclick = async () => {
    document.getElementById("feedback").classList.add("hidden");
    document.getElementById("transcript").textContent = "";
    writeArea.value = "";
    writeWords.textContent = "0";
    await ensureAttempt();
  };

  document.getElementById("btn-next").onclick = async () => {
    Speech.stop().catch(() => {});
    TTS.stop();
    await refreshHeader();
    UI.show("view-home");
    const [modules, dueCount] = await Promise.all([API.modules(), SRS.dueCount()]);
    UI.renderModules(modules, openTopic);
    document.getElementById("srs-due-count").textContent = dueCount;
  };

  // ---- Voice selector ----
  const voiceSelect = document.getElementById("voice-select");
  if (voiceSelect) {
    voiceSelect.value = TTS.getVoice();
    voiceSelect.onchange = () => {
      TTS.setVoice(voiceSelect.value);
      TTS.speak("Hi! This is my voice.");
    };
  }

  // ---- Dictation + Dialogues + Profile init ----
  Dictation.init();
  Dialogues.init();
  ProfileView.init();

  // ---- Boot ----
  if (API.getToken() && API.getUser()) {
    enterApp().catch(() => {
      API.clear();
      UI.show("view-auth");
    });
  } else {
    UI.show("view-auth");
  }
})();
