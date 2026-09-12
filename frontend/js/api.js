// Cliente HTTP minimalista contra el backend FastAPI.
const API = (() => {
  const TOKEN_KEY = "duofeynman_token";
  const USER_KEY = "duofeynman_user";
  const base = ""; // mismo dominio

  function getToken() { return Store.get(TOKEN_KEY); }
  function setSession(token, user) {
    Store.set(TOKEN_KEY, token);
    Store.setJSON(USER_KEY, user);
  }
  function getUser() {
    return Store.getJSON(USER_KEY, null);
  }
  function clear() {
    Store.remove(TOKEN_KEY);
    Store.remove(USER_KEY);
  }

  async function request(path, { method = "GET", body, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth) {
      const t = getToken();
      if (t) headers["Authorization"] = `Bearer ${t}`;
    }
    const res = await fetch(base + path, {
      method, headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      let msg = `Error ${res.status}`;
      try {
        const data = await res.json();
        if (typeof data.detail === "string") msg = data.detail;
        else if (Array.isArray(data.detail)) msg = data.detail.map(d => d.msg || JSON.stringify(d)).join(" · ");
        else if (data.detail) msg = JSON.stringify(data.detail);
      } catch {}
      throw new Error(msg);
    }
    return res.json();
  }

  async function uploadAudio(blob, hints) {
    const fd = new FormData();
    fd.append("file", blob, "audio.webm");
    // Vocabulario esperado del ejercicio: sesga el STT del server hacia esos
    // términos. Separador "|" porque las frases llevan espacios.
    if (hints && hints.length) fd.append("hints", hints.join("|"));
    const t = getToken();
    const res = await fetch(base + "/api/attempts/transcribe", {
      method: "POST",
      headers: t ? { "Authorization": `Bearer ${t}` } : {},
      body: fd,
    });
    if (!res.ok) {
      let msg = "Error transcribiendo";
      try { msg = (await res.json()).detail || msg; } catch {}
      throw new Error(msg);
    }
    return (await res.json()).transcript;
  }

  return {
    getToken, getUser, setSession, clear,
    register: (data) => request("/api/auth/register", { method: "POST", body: data, auth: false }),
    login: (data) => request("/api/auth/login", { method: "POST", body: data, auth: false }),
    me: () => request("/api/me"),
    modules: () => request("/api/curriculum/modules"),
    path: () => request("/api/curriculum/path"),
    topic: (id) => request(`/api/curriculum/topics/${id}`),
    startAttempt: (topicId, mode = "speak") => request("/api/attempts/start", { method: "POST", body: { topic_id: topicId, mode } }),
    submitRound: (data) => request("/api/attempts/round", { method: "POST", body: data }),
    summary: () => request("/api/progress/summary"),
    sttStatus: () => request("/api/attempts/stt-status"),
    dashboard: () => request("/api/progress/dashboard"),
    insights: () => request("/api/progress/insights"),
    srsDue: () => request("/api/srs/due"),
    srsStats: () => request("/api/srs/stats"),
    daily: () => request('/api/daily/today', {method: 'POST'}),
    drill: (id) => request(`/api/srs/drills/${id}`),
    drillCheck: (id, answer) => request(`/api/srs/drills/${id}/check`, {method: 'POST', body: {answer}}),
    listeningNext: (slug) => request('/api/listening/next', {method: 'POST', body: {slug}}),
    listeningReveal: (id) => request(`/api/listening/${id}/reveal`, {method: 'POST'}),
    listeningCheck: (id, choice) => request(`/api/listening/${id}/check`, {method: 'POST', body: {choice}}),
    async listeningAudio(id, slow = false) {
      const res = await fetch(`/api/listening/${id}/audio?slow=${slow}`, {headers: {Authorization: `Bearer ${getToken()}`}});
      if (!res.ok) throw new Error('Audio unavailable. Try again or reveal the text.');
      return res.blob();
    },
    dictationNext: () => request("/api/dictation/next", { method: "POST" }),
    async dictationAudio(id, slow = false) {
      const res = await fetch(`/api/dictation/${encodeURIComponent(id)}/audio?slow=${slow}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error("Audio unavailable. Please try again.");
      return res.blob();
    },
    dictationCheck: (data) => request("/api/dictation/check", { method: "POST", body: data }),
    dialoguesList: () => request("/api/dialogues"),
    dialogue: (id) => request(`/api/dialogues/${id}`),
    dialogueStart: (id) => request(`/api/dialogues/${id}/session`, { method: "POST" }),
    dialogueContinue: (id, responseId) => request(`/api/dialogues/session/${id}/continue`, { method: "POST", body: { response_id: responseId } }),
    dialogueCheck: (data) => request("/api/dialogues/turn/check", { method: "POST", body: data }),
    getProfile: () => request("/api/me/profile"),
    putProfile: (data) => request("/api/me/profile", { method: "PUT", body: data }),
    uploadAudio,
    async tts(text, voice, level) {
      const t = getToken();
      const params = new URLSearchParams({ text });
      if (voice) params.set("voice", voice);
      // El nivel va en la URL solo para diferenciar el cache del navegador: la
      // velocidad real la decide el backend con el nivel del usuario logueado.
      if (level) params.set("lvl", level);
      const res = await fetch(`/api/tts?${params.toString()}`, {
        headers: t ? { "Authorization": `Bearer ${t}` } : {},
      });
      if (!res.ok) {
        let msg = `Error ${res.status}`;
        try { msg = (await res.json()).detail || msg; } catch {}
        throw new Error(msg);
      }
      return res.blob();
    },
    ttsStatus: () => request("/api/tts/status"),
  };
})();
