// Cliente HTTP minimalista contra el backend FastAPI.
const API = (() => {
  const TOKEN_KEY = "duofeynman_token";
  const USER_KEY = "duofeynman_user";
  const base = ""; // mismo dominio

  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  function getUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }
  function clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
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

  async function uploadAudio(blob) {
    const fd = new FormData();
    fd.append("file", blob, "audio.webm");
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
    topic: (id) => request(`/api/curriculum/topics/${id}`),
    startAttempt: (topicId, mode = "speak") => request("/api/attempts/start", { method: "POST", body: { topic_id: topicId, mode } }),
    submitRound: (data) => request("/api/attempts/round", { method: "POST", body: data }),
    summary: () => request("/api/progress/summary"),
    sttStatus: () => request("/api/attempts/stt-status"),
    dashboard: () => request("/api/progress/dashboard"),
    insights: () => request("/api/progress/insights"),
    srsDue: () => request("/api/srs/due"),
    srsStats: () => request("/api/srs/stats"),
    dictationNext: () => request("/api/dictation/next"),
    dictationCheck: (data) => request("/api/dictation/check", { method: "POST", body: data }),
    dialoguesList: () => request("/api/dialogues"),
    dialogue: (id) => request(`/api/dialogues/${id}`),
    dialogueCheck: (data) => request("/api/dialogues/turn/check", { method: "POST", body: data }),
    getProfile: () => request("/api/me/profile"),
    putProfile: (data) => request("/api/me/profile", { method: "PUT", body: data }),
    uploadAudio,
    async tts(text, voice) {
      const t = getToken();
      const params = new URLSearchParams({ text });
      if (voice) params.set("voice", voice);
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
