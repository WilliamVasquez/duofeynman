// Perfil del usuario: HÍBRIDO server + localStorage.
//
// Flujo:
//  - Al iniciar la app: pedimos el perfil al server. Si responde, lo cacheamos en localStorage.
//  - Si NO hay internet o falla: usamos lo de localStorage (resiliencia offline).
//  - Al guardar: actualizamos localStorage SIEMPRE (instantáneo) + intentamos PUT al server.
//    Si PUT falla, queda "dirty" para reintentar más tarde.
const Profile = (() => {
  const CACHE_KEY = "duofeynman_profile_cache";
  const DIRTY_KEY = "duofeynman_profile_dirty";
  const pushes = new Map();
  const owner = () => API.getUser()?.id ?? null;
  const key = (base, id) => `${base}:${id}`;
  const revision = id => Number(Store.get(key("duofeynman_profile_revision", id)) || 0);

  const DEFAULT = {
    nickname: "",
    job: "",
    city: "",
    has_partner: false,
    partner_name: "",
    has_kids: false,
    hobbies: "",
    travels_often: false,
    daily_goal_minutes: 15,
    interests: {
      work: true, relationship: true, family: true,
      health: true, travel: true, social: true,
      shopping: true, adult: false,
    },
    hidden_items: { dialogues: [], topics: [] },
  };

  function _readCache(id = owner()) {
    if (id == null) return JSON.parse(JSON.stringify(DEFAULT));
    let cached = Store.getJSON(key(CACHE_KEY, id), null);
    // Migrar solamente un caché antiguo cuyo dueño esté identificado.
    if (!cached) {
      const legacy = Store.getJSON(CACHE_KEY, null);
      if (legacy?.user_id === id) {
        cached = legacy;
        Store.setJSON(key(CACHE_KEY, id), cached);
        if (Store.get(DIRTY_KEY)) Store.set(key(DIRTY_KEY, id), "1");
      }
    }
    return { ...JSON.parse(JSON.stringify(DEFAULT)), ...cached };
  }

  function _writeCache(data, id = owner()) {
    if (id == null) return;
    const merged = { ...DEFAULT, ..._readCache(id), ...data, user_id: id };
    Store.setJSON(key(CACHE_KEY, id), merged);
  }

  function _markDirty(flag, id = owner()) {
    if (flag) Store.set(key(DIRTY_KEY, id), "1");
    else Store.remove(key(DIRTY_KEY, id));
  }

  function _isDirty(id = owner()) {
    return !!Store.get(key(DIRTY_KEY, id));
  }

  // === API pública ===

  /** Lee del caché (sincrónico, instantáneo). Lo que ve el resto del frontend. */
  function get() { return _readCache(); }

  /** Trae del server y refresca el caché. Llamar al entrar a la app. */
  async function loadFromServer() {
    const id = owner();
    if (id == null) return _readCache();
    _readCache(id); // migración segura si corresponde
    try {
      if (_isDirty(id)) return await pushToServer();
      const data = await API.getProfile();
      if (owner() !== id || data.user_id !== id) return _readCache();
      // También proteger cambios hechos mientras el GET estaba en vuelo.
      if (_isDirty(id)) return await pushToServer();
      _writeCache(data, id);
      return data;
    } catch (err) {
      console.warn("Profile: no se pudo leer del server, usando caché local.", err.message);
      return _readCache();
    }
  }

  /** Push del caché al server. */
  async function pushToServer() {
    const id = owner();
    if (id == null) throw new Error("Please sign in to save your profile.");
    if (pushes.has(id)) return pushes.get(id);
    const task = (async () => {
      while (owner() === id) {
        const rev = revision(id);
        const data = _readCache(id);
        try {
          const resp = await API.putProfile(data);
          if (owner() !== id) return _readCache();
          if (revision(id) !== rev) continue;
          _writeCache(resp, id);
          _markDirty(false, id);
          return resp;
        } catch (err) {
          _markDirty(true, id);
          return { ..._readCache(id), sync_pending: true };
        }
      }
      return _readCache();
    })();
    pushes.set(id, task);
    try { return await task; } finally { pushes.delete(id); }
  }

  /** Guarda cambios. Actualiza caché instantáneo + intenta sync server. */
  async function save(partial) {
    const id = owner();
    if (id == null) throw new Error("Please sign in to save your profile.");
    _writeCache(partial);
    Store.set(key("duofeynman_profile_revision", id), String(revision(id) + 1));
    _markDirty(true, id);
    return pushToServer();
  }

  function reset() {
    // Persistimos el reset también en server
    return save(JSON.parse(JSON.stringify(DEFAULT)));
  }

  function isFilled() {
    const p = _readCache();
    return !!(p.nickname || p.job || p.city);
  }

  // === Items ocultos ===
  function getHidden() {
    const p = _readCache();
    return p.hidden_items || { dialogues: [], topics: [] };
  }

  async function hideItem(kind, slug) {
    const h = getHidden();
    if (!h[kind]) h[kind] = [];
    if (!h[kind].includes(slug)) {
      h[kind].push(slug);
      await save({ hidden_items: h });
    }
  }

  async function unhideItem(kind, slug) {
    const h = getHidden();
    h[kind] = (h[kind] || []).filter(s => s !== slug);
    await save({ hidden_items: h });
  }

  function isHidden(kind, slug) {
    return (getHidden()[kind] || []).includes(slug);
  }

  // === UI helpers ===
  function summary() {
    const p = _readCache();
    const parts = [];
    if (p.nickname) parts.push(p.nickname);
    if (p.job) parts.push(p.job);
    if (p.city) parts.push(`📍 ${p.city}`);
    if (p.has_partner) parts.push(`💑 ${p.partner_name || "tu pareja"}`);
    return parts.length ? parts.join(" · ") : null;
  }

  /** Reemplaza nombres genéricos (Sofia, William) por los del perfil real.
   *
   * Lo aplicamos al renderizar diálogos y topics. Conserva la mayúscula inicial.
   * Si el usuario no llenó esos campos, devuelve el texto original.
   */
  function personalize(text) {
    if (!text) return text;
    const p = _readCache();
    let out = String(text);

    // Sofia → partner_name (si está definido)
    if (p.partner_name && p.partner_name.trim()) {
      const name = p.partner_name.trim();
      out = out.replace(/\bSofia\b/g, name);
      out = out.replace(/\bsofia\b/g, name.toLowerCase());
    }

    // William → nickname (si está definido)
    if (p.nickname && p.nickname.trim()) {
      const nick = p.nickname.trim();
      out = out.replace(/\bWilliam\b/g, nick);
      out = out.replace(/\bwilliam\b/g, nick.toLowerCase());
    }

    return out;
  }

  function practiceBanner(category) {
    const p = _readCache();
    if (!isFilled()) return null;
    const bitsEn = [];
    const bitsEs = [];
    if (p.nickname) {
      bitsEn.push(`You're ${p.nickname}`);
      bitsEs.push(`Sos ${p.nickname}`);
    }
    if (category === "work" && p.job) {
      bitsEn.push(`(${p.job})`);
      bitsEs.push(`(${p.job})`);
    }
    if (category === "relationship" && p.has_partner) {
      bitsEn.push(`with ${p.partner_name || "your partner"}`);
      bitsEs.push(`con ${p.partner_name || "tu pareja"}`);
    }
    if (p.city) {
      bitsEn.push(`in ${p.city}`);
      bitsEs.push(`en ${p.city}`);
    }
    if (bitsEn.length === 0) return null;
    return {
      en: `💡 ${bitsEn.join(" ")}. Adapt what you say to your real life.`,
      es: `💡 ${bitsEs.join(" ")}. Adaptá lo que decís a tu vida real.`,
    };
  }

  return {
    get, save, reset, isFilled, summary, practiceBanner, personalize,
    getHidden, hideItem, unhideItem, isHidden,
    loadFromServer, pushToServer,
  };
})();
