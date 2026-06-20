// Acceso seguro a localStorage.
//
// En modo privado de Firefox/Safari y en algunos WebView Android, localStorage
// lanza excepción y rompía la app entera. Este wrapper detecta eso una vez y,
// si no está disponible, cae a un Map en memoria: los datos no persisten entre
// sesiones, pero la app NO crashea.
const Store = (() => {
  const mem = new Map();
  let backend = null;
  try {
    const probe = "__df_probe__";
    window.localStorage.setItem(probe, "1");
    window.localStorage.removeItem(probe);
    backend = window.localStorage;
  } catch {
    backend = null; // usamos memoria como fallback
  }

  function get(key) {
    try {
      return backend ? backend.getItem(key) : (mem.has(key) ? mem.get(key) : null);
    } catch {
      return mem.has(key) ? mem.get(key) : null;
    }
  }

  function set(key, value) {
    try {
      if (backend) backend.setItem(key, value);
      else mem.set(key, value);
    } catch {
      mem.set(key, value); // cuota llena o bloqueado → memoria
    }
  }

  function remove(key) {
    try {
      if (backend) backend.removeItem(key);
      else mem.delete(key);
    } catch {
      mem.delete(key);
    }
  }

  /** Lee y parsea JSON. Devuelve `fallback` si no existe o está corrupto. */
  function getJSON(key, fallback = null) {
    const raw = get(key);
    if (raw == null) return fallback;
    try { return JSON.parse(raw); } catch { return fallback; }
  }

  function setJSON(key, obj) {
    set(key, JSON.stringify(obj));
  }

  return {
    get, set, remove, getJSON, setJSON,
    get available() { return backend !== null; },
  };
})();
