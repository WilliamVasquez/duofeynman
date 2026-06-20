// Vista "Mi perfil": form + lista de items ocultos.
const ProfileView = (() => {
  const ALL_DIALOGUES_REF = { list: [] };  // cache simple

  function render() {
    _fillForm();
    _renderHidden();
  }

  function _fillForm() {
    const p = Profile.get();
    const form = document.getElementById("profile-form");
    if (!form) return;
    form.nickname.value = p.nickname || "";
    form.job.value = p.job || "";
    form.city.value = p.city || "";
    form.has_partner.checked = !!p.has_partner;
    form.partner_name.value = p.partner_name || "";
    form.has_kids.checked = !!p.has_kids;
    form.hobbies.value = p.hobbies || "";
    form.travels_often.checked = !!p.travels_often;
    form.daily_goal_minutes.value = p.daily_goal_minutes || 15;
    // Intereses
    Object.entries(p.interests || {}).forEach(([k, v]) => {
      const el = form.querySelector(`input[name="interests.${k}"]`);
      if (el) el.checked = !!v;
    });
  }

  async function _renderHidden() {
    const container = document.getElementById("hidden-items-list");
    if (!container) return;
    const hidden = Profile.getHidden();
    const items = [];

    // Buscar info de los diálogos ocultos
    if (hidden.dialogues.length) {
      try {
        const all = await API.dialoguesList();
        ALL_DIALOGUES_REF.list = all;
        hidden.dialogues.forEach(slug => {
          const d = all.find(x => x.slug === slug);
          if (d) items.push({ kind: "dialogues", slug, label: `${d.icon} ${d.title_es}` });
        });
      } catch {}
    }

    if (!items.length) {
      container.innerHTML = `<p style="color:var(--text-muted);font-size:13px;font-style:italic">No tenés items ocultos.</p>`;
      return;
    }

    container.innerHTML = "";
    items.forEach(it => {
      const row = document.createElement("div");
      row.className = "hidden-item-row";
      row.innerHTML = `<span>${it.label}</span><button class="btn-ghost">Mostrar</button>`;
      row.querySelector("button").onclick = async () => {
        await Profile.unhideItem(it.kind, it.slug);
        _renderHidden();
      };
      container.appendChild(row);
    });
  }

  let _inited = false;
  function init() {
    if (_inited) return;   // evitar listeners duplicados
    const form = document.getElementById("profile-form");
    if (!form) return;
    _inited = true;

    form.onsubmit = async (e) => {
      e.preventDefault();
      const data = {
        nickname: form.nickname.value.trim(),
        job: form.job.value.trim(),
        city: form.city.value.trim(),
        has_partner: form.has_partner.checked,
        partner_name: form.partner_name.value.trim(),
        has_kids: form.has_kids.checked,
        hobbies: form.hobbies.value.trim(),
        travels_often: form.travels_often.checked,
        daily_goal_minutes: parseInt(form.daily_goal_minutes.value, 10) || 15,
        interests: {
          work: form.querySelector('[name="interests.work"]').checked,
          relationship: form.querySelector('[name="interests.relationship"]').checked,
          family: form.querySelector('[name="interests.family"]').checked,
          health: form.querySelector('[name="interests.health"]').checked,
          travel: form.querySelector('[name="interests.travel"]').checked,
          social: form.querySelector('[name="interests.social"]').checked,
          shopping: form.querySelector('[name="interests.shopping"]').checked,
          adult: form.querySelector('[name="interests.adult"]').checked,
        },
      };
      const btn = form.querySelector('button[type="submit"]');
      const original = btn.textContent;
      btn.textContent = "Guardando…";
      btn.disabled = true;
      let okMessage = "Perfil guardado correctamente";
      let savedOk = true;
      try {
        await Profile.save(data);
      } catch {
        okMessage = "Guardado solo en este dispositivo (sin internet)";
        savedOk = false;
      }
      UI.toast(okMessage, { type: savedOk ? "success" : "warn", duration: 2200 });
      btn.textContent = original;
      btn.disabled = false;

      // Pequeña pausa para que el usuario vea el toast y redirigir al Home
      setTimeout(() => {
        const homeBtn = document.querySelector(".btn-back-home");
        if (homeBtn) homeBtn.click();
      }, 1100);
    };

    document.getElementById("btn-profile-reset").onclick = async () => {
      if (confirm("¿Borrar todos los datos de tu perfil? Esto NO borra tus progresos.")) {
        await Profile.reset();
        _fillForm();
        _renderHidden();
        UI.toast("Perfil borrado", { type: "info", duration: 1800 });
      }
    };
  }

  return { render, init };
})();
