// Antes del primer render, compatible con la CSP de producción.
(() => {
  let saved = null;
  try { saved = localStorage.getItem("duofeynman_theme"); } catch {}
  if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
})();
