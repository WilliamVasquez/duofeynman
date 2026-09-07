// Diccionario editorial local. Nunca traduce respuestas ni datos del usuario.
const I18n = (() => {
  const pairs = {
    "Iniciar conversación": "Start conversation", "Practicar": "Practice",
    "Ej: William": "Example: William", "Ej: San Salvador": "Example: San Salvador", "Ej: Sofia": "Example: Sofia",
    "Ej: desarrollador IT, dashboards y automatización": "Example: IT developer, dashboards and automation",
    "Ej: cine, motos, cocinar": "Example: movies, motorcycles, cooking",
    "Aprendé inglés": "Learn English", "hablándolo y escribiéndolo": "by speaking and writing",
    "Ingresar": "Sign in", "Crear cuenta": "Create account", "Entrar": "Sign in", "Salir": "Sign out",
    "Contraseña": "Password", "Usuario (letras, números, _, ., -)": "Username (letters, numbers, _, ., -)",
    "Contraseña (mín 8, letras + números)": "Password (8+ characters, letters and numbers)",
    "Hola,": "Hello,", "amigo": "friend", "Seguí tu camino — un tema a la vez.": "Follow your path — one topic at a time.",
    "Mi progreso": "My progress", "Repasar (": "Review (", "Dictado": "Dictation", "Conversaciones": "Conversations",
    "Mi perfil": "My profile", "🗺️ Tu camino": "🗺️ Your learning path", "← Volver": "← Back", "Volver": "Back",
    "Repaso del día": "Today's review", "🎧 Dictado": "🎧 Dictation",
    "Escuchá la frase y escribí": "Listen to the sentence and write", "exactamente": "exactly", "lo que oís.": "what you hear.",
    "Cargando...": "Loading...", "Cargando frase...": "Loading a sentence...", "🔊 Reproducir": "🔊 Play", "🐢 Más lento": "🐢 Slower",
    "Escribí lo que escuchaste...": "Type what you heard...", "palabras": "words", "Palabras": "Words",
    "Comprobar": "Check", "Otra frase →": "Next sentence →", "Cómo te llamamos": "Your name", "Tu trabajo": "Your job",
    "Ciudad": "City", "Tengo pareja": "I have a partner", "Nombre de tu pareja (opcional)": "Partner's name (optional)",
    "Tengo hijos": "I have children", "Hobbies / actividades fuera del trabajo": "Hobbies / activities outside work",
    "Viajo a menudo": "I travel often", "¿Qué áreas te interesan?": "What are you interested in?",
    "(desactivá lo que no te suma)": "(turn off what you don't need)", "💻 Laboral": "💻 Work", "❤️ Pareja": "❤️ Relationships",
    "👨‍👩‍👧 Familia": "👨‍👩‍👧 Family", "🏥 Salud / emergencias": "🏥 Health / emergencies", "✈️ Viajes": "✈️ Travel",
    "👥 Social": "👥 Social", "🛒 Consumidor": "🛒 Shopping", "🔞 Adulto": "🔞 Adult",
    "Tu meta diaria (minutos)": "Daily goal (minutes)", "Borrar perfil": "Reset profile", "Guardar": "Save",
    "🙈 Items ocultos": "🙈 Hidden items", "Lo que marcaste como \"no me sirve\" se acumula acá. Tocá para mostrar de nuevo.": "Your hidden conversations appear here. Select one to show it again.",
    "Elegí una escena. Vas a hablar (o escribir) con un personaje turno a turno.": "Choose a scene. Speak or write with a character, one turn at a time.",
    "Mostrar contenido adulto 🔞": "Show adult content 🔞", "Práctica": "Practice", "Elegí la voz": "Choose a voice",
    "Vocabulario clave 🔑": "Key vocabulary 🔑", "Conectores sugeridos 🔗": "Suggested connectors 🔗",
    "🔊 Escuchar ejemplo": "🔊 Listen to the example", "🎤 Hablar": "🎤 Speak", "✍️ Escribir": "✍️ Write",
    "Grabar": "Record", "Mantené presionado para hablar": "Hold to speak", "Hablá en inglés. Lo más simple que puedas.": "Speak in English. Keep it simple.",
    "Lo que dijiste:": "What you said:", "Escribí en inglés tu explicación.": "Write your explanation in English.", "Enviar": "Send",
    "Conectores": "Connectors", "Español": "Spanish", "Fluidez": "Fluency", "Correcciones 📝": "Corrections 📝",
    "Reformulá respondiendo esto 🧠": "Try again with these questions 🧠", "Cómo lo diría un nativo 💡": "Example answer 💡",
    "🔊 Escuchar": "🔊 Listen", "Escuchar": "Listen", "Intentar de nuevo": "Try again", "Siguiente tema →": "Next topic →",
    "Cambiar tema claro/oscuro": "Switch light/dark theme", "Cambiar tema": "Change theme", "¡Completaste todo el camino hasta B1!": "You completed the path through B1!",
    "Personalizá tu app": "Personalize your app", "Llená \"Mi perfil\" para que la app te muestre solo lo que te sirve y te haga recomendaciones de la semana.": "Fill in My profile to see relevant practice and weekly suggestions.",
    "Llenar mi perfil": "Complete my profile", "No hay conversaciones activas para vos. Activá áreas en Mi perfil.": "No conversations match your interests. Update My profile.",
    "📅 Tu semana en inglés": "📅 Your week in English", "Lun": "Mon", "Mié": "Wed", "Vie": "Fri",
    "🎤 Hablá en inglés. El texto aparece en vivo.": "🎤 Speak in English. Your words appear live.",
    "🎤 Transcripción offline en el server. El texto aparece al soltar.": "🎤 Speak, then release to see your words.",
    "⚠️ El micrófono no está configurado en este navegador.": "⚠️ The microphone is unavailable in this browser.",
    "Usá Chrome/Edge": "Use Chrome/Edge", ", o activá": ", or switch to", "el modo Escribir": "Write mode",
    "⚠️ Tu navegador no permite grabar. Usá el modo Escribir.": "⚠️ Recording is unavailable. Use Write mode.",
    "Escuchando... soltá para enviar": "Listening... release to send", "No te escuché. Probá de nuevo o usá Escribir.": "I couldn't hear you. Try again or use Write mode.",
    "Escribí al menos una oración.": "Write at least one sentence.", "No hay un intento activo. Reintentá en unos segundos.": "No active attempt. Please try again.",
    "Cambio de ritmo: entrená el oído 🎧": "Time for some listening practice 🎧", "Racha días": "Day streak", "XP total": "Total XP",
    "Temas dominados": "Mastered topics", "Score promedio": "Average score", "Fluidez últimos 7 días": "Fluency over 7 days",
    "Score últimos 7 días": "Score over 7 days", "🔒 Logros pendientes": "🔒 Locked achievements", "🔬 Insights de tu aprendizaje": "🔬 Learning insights",
    "Tus promedios globales": "Your overall averages", "Fluidez promedio": "Average fluency", "Code-switch promedio": "Average Spanish use",
    "Palabras por intento": "Words per attempt", "🇪🇸 Palabras que más se te escapan en español": "🇪🇸 Words you often use in Spanish",
    "Estas palabras las dijiste en español más de una vez. Aprendelas en inglés.": "Practice saying these words in English.",
    "📝 Errores gramaticales que repetís": "📝 Recurring grammar mistakes", "Estos errores los hiciste varias veces. Practicá la forma correcta.": "You have made these mistakes several times. Practice the correct form.",
    "🎯 Temas que más te cuestan": "🎯 Topics to practice", "Los 5 temas con score más bajo. Repetilos hasta dominarlos.": "Your five lowest-scoring topics. Practice them again.",
    "⚡ Temas que dominaste rápido": "⚡ Topics you mastered quickly", "Estos los sacaste en 1-2 intentos. ¡Buen trabajo!": "You mastered these in one or two attempts. Well done!",
    "Gramática": "Grammar", "Code-switching (español)": "Spanish use", "Correcciones automáticas": "Automatic corrections", "Pronunciación": "Pronunciation", "Vocabulario": "Vocabulary",
    "📊 Distribución de errores": "📊 Mistakes by category", "¡Los desbloqueaste todos!": "You unlocked them all!", "Aún ninguno. Practicá para desbloquear.": "None yet. Keep practicing!",
    "¡Nada para repasar hoy!": "Nothing to review today!", "Volvé mañana o seguí con lecciones nuevas.": "Come back tomorrow or try a new lesson.",
    "Tenés": "You have", "tema": "topic", "temas": "topics", "para repasar.": "to review.",
    "Tocá uno para practicarlo de nuevo — el algoritmo lo reagenda según cómo te salga.": "Choose a topic to practice. Your result sets the next review date.",
    "Frase correcta:": "Correct sentence:", "Tu respuesta:": "Your answer:", "Te faltaron:": "Missing:", "De más:": "Extra:",
    "No tenés items ocultos.": "No hidden items.", "Mostrar": "Show", "Guardando…": "Saving…", "Perfil guardado correctamente": "Profile saved",
    "Guardado solo en este dispositivo (sin internet)": "Saved on this device (offline)", "Perfil borrado": "Profile reset",
    "Mi día laboral": "My workday", "Mi carrera": "My career", "Con mi pareja": "With my partner", "Adulto (+18)": "Adult (18+)",
    "Saliendo de casa": "Out and about", "Cuando algo pasa": "When something happens", "Lo social": "Social life", "Familia y fechas": "Family and occasions",
    "Consumidor informado": "Shopping decisions", "Cuando viajés": "Travel", "📦 Otros": "📦 Other", "No hay nada para mostrar": "Nothing to show",
    "Activá más áreas de interés en": "Enable more interests in", "o quitá items ocultos.": "or show hidden items.", "No me sirve, ocultar": "Hide this conversation",
    "Vos": "You", "Tocá las palabras de abajo para armar la oración →": "Tap the words below to build your sentence →",
    "Todas usadas. Tocá Enviar o limpiá para arrancar de cero.": "All words used. Send your answer or clear it to start again.",
    "Tocá las palabras para armar la oración.": "Tap the words to build a sentence.", "¡Sin errores graves! 🎉": "No major mistakes found! 🎉",
    "Grave": "Major", "Medio": "Moderate", "Leve": "Minor", "Tocá para escuchar": "Tap to listen",
    "Estructura": "Structure", "Naturalidad": "Naturalness", "Cobertura + diversidad de palabras": "Vocabulary coverage and variety",
    "Conectores, tiempos verbales, oraciones": "Connectors, tenses and sentences", "Sin code-switching, gramática limpia": "English use and grammar",
    "Velocidad y longitud": "Pace and length", "Detalle del score": "Score details", "Tiempos verbales detectados:": "Tenses found:",
    "Primeros pasos": "First steps", "Completaste tu primer intento.": "You completed your first attempt.", "Primer dominio": "First mastery", "Dominaste tu primer tema.": "You mastered your first topic.",
    "Una semana": "One week", "Practicaste 7 días seguidos.": "You practiced for seven days in a row.", "Sin code-switching": "All in English",
    "Completaste un tema sin meter palabras en español.": "You completed a topic without using Spanish words.", "Un minuto fluido": "A fluent minute", "Hablaste 60 segundos sin pausa larga.": "You spoke for 60 seconds at a steady pace.",
    "¡Excelente oído! 🎧": "Excellent listening! 🎧", "Muy bien. Faltaron detalles.": "Well done. Check the details.", "Vas bien. Volvé a escucharlo y ajustá.": "Good start. Listen again and make corrections.", "Difícil. Bajá la velocidad y reintentá.": "Try slower audio and listen again.",
    "¡Excelente! Sonó natural y fluido. 🎉": "Excellent! That sounded clear and fluent. 🎉", "Buenísimo, lo explicaste con claridad. ¡Seguí así!": "You explained that clearly. Keep going!",
    "Muy bien, tu inglés se está soltando. 💪": "Well done. Your English is improving. 💪", "¡Eso es! Esa es la idea del método Feynman: simple y claro.": "That's it: explain things simply and clearly.",
    "Vas por buen camino. Probá conectar mejor tus ideas con 'because', 'so', 'then'.": "Good start. Connect your ideas with 'because', 'so' and 'then'.",
    "Bien, pero podés ser más simple. Como si se lo explicaras a un niño.": "Try a simpler explanation, as if you were explaining it to a child.",
    "Buen intento. Mirá las correcciones y volvé a intentar.": "Good try. Read the corrections and try again.", "Casi. Una vuelta más y lo dominás.": "Nearly there. Try one more time.",
    "Tranquilo, hablar es lo más difícil. Probá de nuevo, más despacio.": "Take your time. Try speaking again, more slowly.", "No pasa nada, leé el ejemplo, escuchalo, y reintentá.": "Read and listen to the example, then try again.",
    "Recordá: en inglés, no traduzcas en tu cabeza. Pensá en imágenes.": "Try thinking about the situation and describing it in English.", "Vas a poder. Probá usando solo 3-4 palabras clave del tema.": "You can do it. Start with three or four key words.",
    "Te trabaste y dijiste algunas palabras en español. Está OK — la próxima intentá decirlas en inglés aunque sea mal pronunciado.": "You used some Spanish words. Try using English words next time, even if pronunciation is difficult.",
    "Mezclaste un poco de español. Mirá el vocabulario clave arriba y reintentá.": "You used some Spanish. Review the key vocabulary and try again.",
    "Muy cortito. Intentá decir al menos 2-3 oraciones.": "Try adding a little more detail.", "Necesito escucharte más. Probá con la rutina completa, paso por paso.": "Add more detail, one step at a time.",
    "No autenticado": "Please sign in.", "Token inválido": "Your session has expired. Please sign in again.", "Credenciales inválidas": "Invalid email or password.",
    "Email o usuario ya registrado": "Email or username already registered.", "Usuario no encontrado": "User not found.", "Intento ya cerrado": "This attempt is complete. Start another one.",
    "Topic no encontrado": "Topic not found.", "Intento no encontrado": "Attempt not found.", "Lección no encontrada": "Lesson not found.",
    "Error interno del servidor.": "Internal server error.", "Demasiadas peticiones. Esperá un momento y volvé a intentar.": "Too many requests. Wait a moment and try again.",
    "La contraseña debe tener al menos 8 caracteres.": "Use at least eight characters in your password.", "La contraseña debe mezclar letras y al menos un número.": "Your password must include letters and a number.",
    "Esa contraseña es demasiado común. Elegí otra.": "That password is too common. Choose another one.", "Error transcribiendo": "Transcription failed",
    "Grabando... se transcribirá al soltar.": "Recording... release to transcribe.", "Transcribiendo... 🎧": "Transcribing... 🎧",
    "Tu navegador no permite grabar audio. Usá el modo Escribir.": "Recording is unavailable. Use Write mode.",
    "Escribiste 'U'. En inglés correcto se dice 'you'.": "Write 'you' instead of 'U'.", "Escribiste 'R'. En inglés correcto es 'are'.": "Write 'are' instead of 'R'.",
    "'ur' es text-speak. Lo correcto es 'your'.": "Write 'your' instead of 'ur'.", "'thx' es informal. Mejor 'thanks'.": "Use 'thanks' instead of 'thx'.",
    "Falta el verbo 'to be': 'I'm from' (= I am from).": "Add 'am': 'I'm from' means 'I am from'.", "Falta el verbo: 'I'm in'.": "Add the verb: 'I'm in'.",
    "Falta el verbo: 'I'm a' (= I am a).": "Add the verb: 'I'm a' means 'I am a'.", "Falta el verbo 'to be': 'I'm very'.": "Add 'am': 'I'm very'.",
    "Con adjetivos hace falta 'to be': 'I am happy'.": "Use 'to be' with adjectives: 'I am happy'.", "Con adjetivos hace falta 'to be': 'I am sad'.": "Use 'to be' with adjectives: 'I am sad'.",
    "Con adjetivos hace falta 'to be': 'I am tired'.": "Use 'to be' with adjectives: 'I am tired'.", "El pronombre 'I' siempre va en mayúscula.": "Always capitalize the pronoun 'I'.",
    "'gonna' es informal hablado. En escrito mejor 'going to'.": "'Gonna' is informal speech. Use 'going to' in writing.", "'wanna' es informal hablado. En escrito mejor 'want to'.": "'Wanna' is informal speech. Use 'want to' in writing.",
    "En inglés no se usa doble negación: 'I don't have any'.": "Avoid a double negative: 'I don't have any'.", "Negación correcta: 'I don't + verbo'.": "Use 'I don't' followed by the verb.",
    "En inglés la edad usa 'to be': 'I am X years old', no 'I have X years'.": "Use 'to be' for age: 'I am X years old'."
  };
  const reverse = new Map(Object.entries(pairs).map(([es,en]) => [en,es]));
  const escape = s => String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  function html(en, es) {
    return `<span data-es="${escape(es)}">${escape(en)}</span>`;
  }
  function translate(text) {
    const trimmed = String(text).trim().replace(/\s+/g,' ');
    if (pairs[trimmed]) return [pairs[trimmed], trimmed];
    if (reverse.has(trimmed)) return [trimmed, reverse.get(trimmed)];
    const extra = typeof CURRICULUM_TRANSLATIONS === 'undefined' ? {} : CURRICULUM_TRANSLATIONS;
    if (extra[trimmed]) return [extra[trimmed],trimmed];
    const decorated = trimmed.match(/^([^\p{L}\p{N}]+)([\s\S]+)$/u);
    if (decorated) {
      const [en, es] = translate(decorated[2]);
      if (es) return [decorated[1] + en, trimmed];
    }
    const patterns = [
      [/^Dijiste «(.+)» en español\. Intentá decirlo en inglés\.$/, m=>`You used «${m[1]}» in Spanish. Try saying it in English.`],
      [/^Visto (\d+) veces$/, m=>`Reviewed ${m[1]} times`], [/^Intervalo (\d+)d$/, m=>`Interval: ${m[1]}d`],
      [/^Oraciones: (\d+) · Diversidad léxica: (\d+)%$/,m=>`Sentences: ${m[1]} · Vocabulary variety: ${m[2]}%`],
      [/^🏆 Logros desbloqueados \((\d+)\)$/,m=>`🏆 Unlocked achievements (${m[1]})`],
      [/^🎉 ¡Logros? desbloqueados?!$/,()=> '🎉 Achievement unlocked!'],
      [/^(.+) · Dificultad (.+)$/,m=>`${m[1]} · Difficulty ${m[2]}`],
      [/^No se pudo abrir el tema: (.+)$/,m=>`Could not open the topic: ${translate(m[1])[0]}`],
      [/^No se pudo iniciar el intento: (.+)$/,m=>`Could not start the attempt: ${translate(m[1])[0]}`],
      [/^Error al enviar: (.+)$/,m=>`Could not send: ${translate(m[1])[0]}`],
      [/^Error: (.+)$/,m=>`Error: ${translate(m[1])[0]}`],
      [/^No pude acceder al micrófono: (.+)$/,m=>`Could not access the microphone: ${m[1]}`],
    ];
    for (const [pattern,replace] of patterns) { const m=trimmed.match(pattern); if(m) return [replace(m),trimmed]; }
    return [text,null];
  }
  function wire(el) {
    if (el.dataset.i18nReady) return;
    el.dataset.i18nReady = '1';
    const es = el.dataset.es;
    if (!es) return;
    el.title = es;
    // Los controles conservan su acción; la traducción tiene un botón hermano.
    const control = el.closest('button,a,label,summary');
    let trigger = el;
    if (control) {
      if (control.matches('.quick-btn,.topic-btn') && !control.parentElement.classList.contains('translated-action')) {
        const group = document.createElement('div');
        group.className = 'translated-action' + (control.matches('.quick-btn') ? ' translated-quick' : '');
        control.before(group); group.appendChild(control);
      }
      let button = control.nextElementSibling;
      if (!button?.classList.contains('translation-toggle')) {
        button=document.createElement('button'); button.type='button'; button.className='translation-toggle';
        button.textContent='ES'; button.setAttribute('aria-label','Show Spanish translation');
        control.after(button);
      }
      trigger=button;
      trigger.hidden = control.classList.contains('hidden');
    } else {
      trigger.tabIndex=0; trigger.setAttribute('role','button'); trigger.classList.add('translatable');
    }
    trigger.title=es;
    trigger.setAttribute('aria-expanded','false');
    const toggle = e => {
      if (e.type==='keydown' && !['Enter',' '].includes(e.key)) return;
      e.preventDefault(); e.stopPropagation();
      const next=trigger.nextElementSibling;
      if (next?.classList.contains('es-inline')) {next.remove();trigger.setAttribute('aria-expanded','false');return;}
      const translation=document.createElement('span'); translation.className='es-inline'; translation.lang='es';
      translation.textContent=es; trigger.after(translation); trigger.setAttribute('aria-expanded','true');
    };
    trigger.onclick=toggle;
    if (!control) trigger.onkeydown=toggle;
  }
  const excluded = 'script,style,textarea,option,.es-inline,[data-es],[data-i18n-ignore],.translation-toggle,#transcript,.chat-msg.user,#user-name,#profile-card,.drill-wrong,.drill-fix,.leak-chip,#model-answer';
  function enhance(root) {
    if (!root?.querySelectorAll) return;
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    const nodes=[]; while(walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      if (!node.parentElement || node.parentElement.closest(excluded)) continue;
      const raw=node.textContent; const [en,es]=translate(raw);
      if (!es || !raw.trim()) continue;
      const span=document.createElement('span'); span.dataset.es=es;
      span.textContent=raw.replace(raw.trim(),String(en).trim()); node.replaceWith(span);
    }
    for (const el of root.querySelectorAll('[placeholder]')) {
      const [en,es]=translate(el.placeholder); el.placeholder=en;
      if (!el.getAttribute('aria-label')) el.setAttribute('aria-label',en);
      if(es) el.title=es;
    }
    if(root.matches?.('[data-es]')) wire(root);
    root.querySelectorAll('[data-es]').forEach(wire);
  }
  function init() {
    enhance(document.body);
    const observer=new MutationObserver(records=>{
      observer.disconnect();
      const roots=new Set();
      for(const record of records) {
        if(record.type==='attributes') {
          const sibling=record.target.nextElementSibling;
          if(sibling?.classList.contains('translation-toggle')) sibling.hidden=record.target.classList.contains('hidden');
        } else roots.add(record.target.nodeType===3 ? record.target.parentElement : record.target);
      }
      roots.forEach(enhance);
      observer.observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['class']});
    });
    observer.observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['class']});
  }
  return {html,translate,enhance,init};
})();
