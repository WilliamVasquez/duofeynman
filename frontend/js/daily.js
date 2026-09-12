// Sesión diaria: composición del servidor, navegación libre y progreso verificado.
const Daily = (() => {
  let openTopic = null, version = 0;
  function init(callback) { openTopic = callback; }
  async function render() {
    UI.show('view-daily');
    const request = ++version;
    const root = document.getElementById('daily-content');
    root.textContent = 'Loading…';
    try {
      const plan = await API.daily();
      if (request !== version || !document.getElementById('view-daily').classList.contains('active')) return;
      root.innerHTML = `<div class="practice-panel"><h3>${I18n.html(`${plan.completed} of ${plan.total} activities complete · about ${plan.minutes} minutes`, `${plan.completed} de ${plan.total} actividades hechas · unos ${plan.minutes} minutos`)}</h3>
        <p>${I18n.html('Review, strengthen, explore. Choose any activity. Completion tracks practice, not mastery.', 'Repasá, reforzá, explorá. Elegí cualquier actividad. Completar registra práctica, no dominio.')}</p>
        ${plan.items.map((item, i) => `<article class="daily-item ${item.done ? 'done' : ''}"><h4>${item.done ? '✓ ' : ''}${I18n.html(item.title_en, item.title_es)}</h4>
        <p>${I18n.html(item.reason_en, item.reason_es)}</p><small>~${item.minutes} min</small><button class="btn-primary daily-start" data-index="${i}">${item.done ? 'Practice again' : 'Start'}</button></article>`).join('')}
        ${plan.completed === plan.total ? `<p>${I18n.html('Today’s practice is complete. Well done!', 'Terminaste la práctica de hoy. ¡Buen trabajo!')}</p>` : ''}</div>`;
      root.querySelectorAll('.daily-start').forEach(button => {
        button.onclick = async () => {
          const item = plan.items[Number(button.dataset.index)];
          button.disabled = true;
          try {
            if (item.kind === 'topic') await openTopic(await API.topic(item.id));
            else if (item.kind === 'drill') await SRS.openDrill(item.id);
            else if (item.kind === 'dialogue') await Dialogues.start(item.id);
            else await Listening.load(item.id);
          } catch (err) {UI.toast(err.message, {type: 'error'});}
          finally {button.disabled = false;}
        };
      });
    } catch (err) {if (request === version) root.textContent = err.message;}
  }
  return {init, render};
})();
