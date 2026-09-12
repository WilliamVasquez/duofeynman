# DuoFeynman 🦆🧠

**Aprendé inglés hablándolo y escribiéndolo, no memorizándolo.**

App estilo Duolingo basada en el **Método Feynman + Output Hypothesis**: en vez de tocar botones, *explicás* temas en inglés (hablando **o** escribiendo). Un motor rule-based detecta huecos, errores y code-switching, te muestra qué falta del vocabulario y conectores del tema, y te lanza preguntas socráticas para que reformules.

**100% gratis, sin APIs externas pagas, sin claves, sin cuotas.**

## Stack

| Capa | Tecnología | Costo |
|---|---|---|
| Backend | Python 3.11 + FastAPI + SQLAlchemy + MySQL | gratis |
| Frontend | HTML/CSS/JS vanilla, mobile-first responsive (listo para WebView Android) | gratis |
| STT (Chrome / Edge) | Web Speech API nativa del navegador | gratis |
| STT (Firefox + fallback) | **faster-whisper offline** (MIT) | gratis, 1× descarga ~150 MB |
| STT (fallback del fallback) | **Vosk offline** + ffmpeg | gratis, 1× descarga 40 MB |
| TTS primario | **Edge TTS** (voces Microsoft Neural: Aria, Jenny, Guy...) | gratis, sin clave |
| TTS fallback offline | **Piper TTS** (neural local) | gratis, 1× descarga 63 MB |
| TTS último recurso | `speechSynthesis` del navegador | gratis (robótico) |
| Gramática | LanguageTool API pública | gratis (20 req/min) |
| Feedback Feynman | Motor rule-based propio | gratis |
| Seguridad | JWT + bcrypt + rate limiting (slowapi) | gratis |

**Sin IA generativa = comportamiento determinístico, explicable, sin alucinaciones.**

> 🔒 Antes de exponer la app a internet, leé **[SECURITY.md](SECURITY.md)** — checklist completo de hardening (HTTPS, firewall, CORS, secretos, backups).

## Cómo aprende el usuario (motor Feynman)

Cada **Topic** del curriculum se ataca con un ciclo de 5 etapas:

1. **EXPOSE** — Mostramos el tema, vocabulario clave y un ejemplo modelo en audio
2. **EXPLAIN** — El usuario elige modo y produce inglés:
   - 🎤 **Hablar** — micrófono → texto (Web Speech en Chrome/Edge, Whisper en Firefox)
   - ✍️ **Escribir** — textarea (mejor para gramática, sin presión de pronunciación)
3. **DETECT** — Análisis rule-based:
   - Fluidez (palabras por minuto en modo Hablar; densidad en Escribir)
   - Code-switching ES→EN (palabras españolas detectadas con diccionario)
   - Gramática (LanguageTool)
   - Cobertura de vocabulario clave del topic
   - Cobertura de conectores sugeridos del topic
4. **REFINE** — Preguntas socráticas: combinación de `socratic_hints` fijas del curriculum + sugerencias generadas por templates (ej: *"Try saying it again using 'because'"*).
5. **CONSOLIDATE** — Si dominó (score ≥ 0.78), creamos una card SRS (algoritmo SM-2) que vuelve a aparecer en 1d, 3d, 7d, 21d...

Además del ciclo Feynman, hay **diálogos guionados** (51 escenarios): conversás por turnos con un
personaje (NPC rule-based). Cada turno tuyo se puede responder en tres modos:

- 💬 **Choose** (default) — 3 respuestas completas y **todas válidas**, con intenciones distintas
  (aceptar, rechazar, preguntar algo). Tocás una y la decis. Nunca te quedas sin saber qué responder.
- ✍️🎤 **Write / Speak** — escribis o hablas libre. Es el modo de producción real.
- 🧩 **Order words** — armas la oración tocando las palabras desordenadas.

El motor de validación es una **guía, no un examen**: acepta siempre cualquier respuesta que la app
haya ofrecido, mide la similitud contra la mejor de todas ellas (no contra una única respuesta modelo),
explica **en pantalla y en español** qué faltó, y si igual no reconoce tu respuesta te deja avanzar
con *Continue anyway* — nunca hay callejón sin salida.

La UI está en **inmersión total en inglés**, con la traducción al español disponible al hacer
clic/hover en cada línea (también en cada opción de respuesta, con su botón `ES`).

## Setup paso a paso

### 1. Crear la base de datos en tu MySQL local

```sql
CREATE DATABASE duofeynman CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Instalar ffmpeg (recomendado: limpia el audio antes de transcribir)

- Descargá desde https://ffmpeg.org/download.html (build de Windows)
- Descomprimí y agregá la carpeta `bin/` al PATH del sistema
- Verificar: `ffmpeg -version` en una nueva PowerShell

### 3a. Piper offline en Windows (opcional — voz neural sin internet)

> **No instales `piper-tts` con pip en Windows** — su dependencia `piper-phonemize` no tiene wheels para Windows y rompe el `pip install`. Usá el binario standalone:

1. Descargar el binario standalone para Windows desde la página de releases de Piper:
   https://github.com/rhasspy/piper/releases
   Buscar el ZIP `piper_windows_amd64.zip` (~30 MB).
2. Descomprimir y copiar **toda la carpeta** dentro de `backend/piper/`
   Te tiene que quedar: `backend/piper/piper.exe` (junto con sus DLLs).
3. Descargar la voz neural desde HuggingFace:
   https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/amy/medium
   Bajar **ambos** archivos:
   - `en_US-amy-medium.onnx` (~63 MB)
   - `en_US-amy-medium.onnx.json` (~5 KB)
4. Crear `backend/models/piper/` y poner los dos archivos ahí.

No importa si dejás el `piper.exe` en `backend/piper/` o junto a los modelos en
`backend/models/piper/`: la app busca en las dos rutas. Igual con los modelos —
si hay varios `.onnx`, elige el de mejor calidad (`high` > `medium` > `low`) y
lee el sample rate del `.json`, así que no hay que tocar el `.env` para cambiarlo.

**Voz más natural (opcional):** un modelo `high` suena bastante mejor que `medium`.
Bajá los dos archivos de
https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/high
(`en_US-lessac-high.onnx` ~110 MB + su `.json`) a `backend/models/piper/` y la app
lo empieza a usar sola. Esto solo afecta al fallback offline: con internet manda
Edge TTS, que es más natural que cualquier Piper.

**Verificación rápida** (opcional):
```powershell
echo "hello world" | .\backend\piper\piper.exe --model .\backend\models\piper\en_US-amy-medium.onnx --output_file test.wav
```
Si genera `test.wav`, Piper está listo.

Si saltás este paso, el TTS funciona igual con Edge TTS (online) y como último recurso usa el TTS del navegador.

### 3b. STT offline: faster-whisper (automático)

Es el motor principal de transcripción en el server y **no requiere ningún paso
manual**: viene en `requirements.txt` y baja el modelo solo la primera vez que
alguien usa el micrófono sin Web Speech API. Queda en `backend/models/whisper/`.

Configurable en `.env`:

| Variable | Default | Para qué |
|---|---|---|
| `STT_ENGINE` | `auto` | `auto` \| `whisper` \| `vosk`. `auto` usa Whisper si está instalado |
| `WHISPER_MODEL` | `base.en` | `base.en` (~150 MB) o `small.en` (~500 MB, más preciso y 2-3× más lento) |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8` para CPU; `float16` solo con GPU |
| `WHISPER_MODEL_DIR` | `models/whisper` | Dónde cachear el modelo |

Whisper entiende bastante mejor a hablantes no nativos que Vosk (que confundía
"yes that's right" con "yes that's why"), devuelve puntuación y mayúsculas, y en
esta máquina resultó además **más rápido**: ~0,8 s contra ~5,5 s de Vosk para un
audio de 4,5 s. Necesita internet **una sola vez** para bajar el modelo.

### 3c. Descargar modelo Vosk inglés (40 MB, opcional)

Solo como fallback del fallback — si Whisper no está instalado o falla.

1. Ir a https://alphacephei.com/vosk/models
2. Descargar **vosk-model-small-en-us-0.15** (~40 MB)
3. Descomprimir en `backend/models/vosk-en-small/` (que el `model.conf` quede en esa ruta)

> Si solo usás Chrome/Edge, este paso es opcional — Web Speech API alcanza.

### 4. Backend Python

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Editá .env con tu password MySQL
```

### 5. Cargar curriculum inicial

```powershell
python -m app.seed
```

### 6. Levantar el servidor

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Abrir la app

http://localhost:8000 en **Chrome, Edge o Firefox**.

Crear cuenta → elegir un tema → elegir 🎤 Hablar o ✍️ Escribir → producir inglés.

## Soporte por navegador

| Navegador | Modo Hablar | Modo Escribir |
|---|---|---|
| **Chrome / Edge** | Web Speech API (transcripción en vivo) | ✅ |
| **Firefox** | MediaRecorder → Whisper en el server (al soltar) | ✅ |
| **Android WebView** (futuro) | Web Speech API (Chrome WebView) | ✅ |

## Estructura del proyecto

```
duofeynman/
├── backend/
│   ├── app/
│   │   ├── main.py                 ← FastAPI + middlewares de seguridad
│   │   ├── config.py               ← Settings, valida config crítica al arranque
│   │   ├── database.py
│   │   ├── seed.py                 ← carga curriculum + diálogos (idempotente)
│   │   ├── models/                 ← user, curriculum, attempt, progress, srs, dialogue, profile
│   │   ├── schemas/                ← Pydantic v2
│   │   ├── routers/                ← auth, users, curriculum, attempts, progress,
│   │   │                              srs, dictation, dialogues, tts, profile
│   │   ├── services/
│   │   │   ├── feynman_engine.py   ← núcleo pedagógico rule-based
│   │   │   ├── dialogue_engine.py  ← motor de diálogos guionados (NPC)
│   │   │   ├── analyzer.py         ← métricas + code-switching + LanguageTool
│   │   │   ├── gamification.py     ← racha + logros desbloqueables
│   │   │   ├── srs.py              ← repetición espaciada SM-2
│   │   │   ├── stt.py               ← orquestador STT (whisper → vosk)
│   │   │   ├── whisper_stt.py       ← STT offline con faster-whisper
│   │   │   ├── vosk_stt.py          ← STT offline con Vosk (fallback)
│   │   │   ├── audio_utils.py       ← ffmpeg: conversion + limpieza de audio
│   │   │   ├── tts.py               ← Edge TTS → Piper → navegador (+ cache en disco)
│   │   │   ├── rate_limit.py       ← slowapi (límites por IP)
│   │   │   └── security.py         ← JWT + bcrypt
│   │   └── data/curriculum/        ← a1_curriculum.json + dialogues.json
│   ├── models/whisper/             ← (se descarga solo, ver paso 3b)
│   ├── models/vosk-en-small/       ← (descargar manualmente, ver paso 3c)
│   ├── piper/ + models/piper/      ← (opcional, ver paso 3a)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── index.html                  ← responsive, mobile-first, inmersión EN
    ├── css/styles.css              ← variables CSS, dark mode, animaciones
    └── js/
        ├── app.js                  ← orquestador + toggle de tema
        ├── api.js                  ← cliente HTTP
        ├── speech.js               ← WebSpeech / MediaRecorder → server
        ├── tts.js                  ← reproducción de audio con caché
        ├── dialogues.js            ← UI de diálogos guionados
        ├── dashboard.js            ← stats + gráficos + insights
        ├── srs.js                  ← panel de repaso SRS
        ├── dictation.js            ← modo dictado
        ├── profile.js              ← estado de perfil (localStorage + server)
        ├── profile-view.js         ← vista de edición de perfil
        └── ui.js                   ← rendering, toasts, confetti
```

## Curriculum incluido (A1 → B1)

**16 módulos · 32 lecciones · 62 topics · 51 diálogos guionados (205 turnos, 615 respuestas escritas)**

| Nivel | Módulos |
|---|---|
| **A1** (5) | Survival English · Numbers & time · Daily life · Feelings & places · **Connecting ideas** ← tu zona clave (`because`, `so`, `that's why`, `when`...) |
| **A2** (4) | Past simple · Can/could/should/must · Comparing things · Past habits & ongoing actions |
| **B1** (7) | Present Perfect · Conditionals · Reported speech · Narrative skills · Phrasal verbs · Relative clauses · Modals of deduction |

Agregar más temas: editar `app/data/curriculum/a1_curriculum.json` (o `dialogues.json`) y correr `python -m app.seed` (es idempotente).

## Migración a Android (WebView)

El frontend está pensado para vivir dentro de un `WebView` de Android sin cambios:
- 100% responsive mobile-first (`viewport-fit=cover`, safe-area-insets)
- Touch events para hold-to-talk
- En Android Chrome WebView (≥33) funciona Web Speech API

## Roadmap

- [x] Backend rule-based sin IA externa
- [x] Modo Hablar (Chrome/Edge + Firefox vía faster-whisper)
- [x] Modo Escribir
- [x] Curriculum completo **A1 → B1** (16 módulos, 62 topics)
- [x] TTS neural (Edge TTS + Piper offline + fallback navegador)
- [x] Selector de voz (7 voces US/UK/AU)
- [x] Dashboard de progreso con gráficos de 7 días + insights
- [x] Cálculo correcto de racha
- [x] Logros desbloqueables automáticos + confetti
- [x] Panel SRS de repaso diario (SM-2)
- [x] Modo Dictado para entrenar el oído
- [x] **Diálogos guionados (51 escenarios; elegir / hablar / escribir / ordenar palabras)**
- [x] **Modo Choose: 3 respuestas válidas por turno, con feedback visible y salida sin trabarse**
- [x] **Inmersión total en inglés con traducción al clic/hover**
- [x] **Dark mode + animaciones + skeleton loaders + mascota**
- [x] **Hardening de seguridad (ver SECURITY.md)**
- [x] PWA: instalable en celu como app
- [x] Comprensión auditiva: 12 situaciones A1–B1, explicación bilingüe y práctica con/sin texto
- [x] Diálogos guardados: reanudar turno, conservar respuestas, errores y modo
- [x] Ayudas graduales: Choose → Order → Write / Speak, siempre con cambio libre
- [x] Mini ejercicios SRS de errores concretos, además del repaso de temas
- [x] Sesión diaria adaptativa: repaso vencido, respuesta débil, siguiente tema y escucha
- [ ] Curriculum B2
- [ ] Build de Android (WebView wrapper)

## Endpoints REST disponibles

| Endpoint | Para qué |
|---|---|
| `POST /api/auth/register` `/login` | Registro / login |
| `GET /api/me` | Perfil del usuario |
| `GET /api/curriculum/modules` | Lista de módulos + lecciones + topics |
| `POST /api/attempts/start` `/round` | Ciclo Feynman: iniciar + enviar respuesta |
| `POST /api/attempts/transcribe` | Sube audio → Whisper/Vosk transcribe (Firefox) |
| `GET /api/progress/summary` `/dashboard` | Stats + gráficos + logros |
| `GET /api/srs/due` `/stats` | Cards SRS que vencen hoy |
| `POST /api/dictation/next` `POST /api/dictation/check` | Crear y corregir un dictado por ID; recompensa única |
| `GET /api/dictation/{id}/audio` | Audio del dictado autenticado (`?slow=true` para más lento) |
| `GET /api/dialogues` `/{id}` | Diálogos guionados; cada turno USER trae `answer_options` (nunca `required_keywords`) |
| `POST /api/dialogues/turn/check` | Corrige un turno: score, motivo en español, `passed` y `can_continue` |
| `POST /api/dialogues/{id}/session` | Inicia/reanuda; devuelve guion guardado y progreso |
| `POST /api/dialogues/session/{id}/continue` | Guarda “Continue anyway” sin contar como dominio |
| `POST /api/listening/next` | Crea ejercicio de comprensión, sin revelar audio escrito ni respuesta |
| `GET /api/listening/{id}/audio` | Audio autenticado; admite `?slow=true` |
| `POST /api/listening/{id}/check` `/reveal` | Corrige una elección o revela texto como ayuda |
| `GET /api/srs/drills/{id}` `POST /api/srs/drills/{id}/check` | Mini ejercicio de corrección y reprogramación |
| `POST /api/daily/today` | Crea/reanuda un plan estable del día con progreso verificado |
| `GET/PUT /api/me/profile` | Perfil personalizado (contexto Feynman) |
| `GET /api/tts?text=...&voice=aria` | TTS neural (MP3 o WAV) |
| `GET /api/tts/status` | Qué backends TTS están disponibles |

---

## Actualización y pruebas de regresión

Las cinco mejoras nuevas requieren **reiniciar el backend y recargar la página**.
El arranque crea `dialogue_sessions`, `dialogue_responses`, `listening_attempts` y
`daily_plans`. No agregan columnas a tablas existentes ni requieren volver a sembrar
un curriculum que ya tiene las opciones de Choose. Las sesiones guardan una copia
del guion: un seed posterior no invalida los turnos pendientes.

Dos conversaciones completas, sin errores, omisiones ni ayudas adicionales, permiten
pasar a la siguiente sugerencia: Choose → Order → Write / Speak. Elegir otro modo
sigue permitido. “Continue anyway” guarda la respuesta y avanza, pero no aumenta
dominio. Las respuestas se guardan por cuenta; un reenvío del mismo ID es idempotente.

Escucha propone situaciones del nivel actual y sube hasta B1 después de tres audios
distintos correctos sin texto. Revelar el texto registra práctica guiada. La primera
respuesta corregida queda fija; se puede iniciar otro ejercicio para seguir practicando.
El banco y las explicaciones son editoriales, sin generación ni servicios pagos.

Los mini ejercicios se crean desde errores nuevos con una corrección explícita.
Repetir el mismo error reutiliza su tarjeta. La reprogramación ocurre una vez por día;
reintentar después de ver la solución no multiplica el intervalo ni da XP.

El plan diario conserva sus actividades durante el día, respeta temas ocultos y usa
la meta de minutos del perfil como estimación. Completar significa practicar, no
necesariamente dominar. Al dominar A1, el siguiente tema puede ser A2, hasta B1.
Rachas, repasos y planes usan el día de El Salvador (UTC−6); los timestamps siguen en UTC.

Desde `backend/`, actualizá el entorno con `python -m pip install -r requirements.txt`
y reiniciá el backend. El arranque existente crea la nueva tabla `dictation_exercises`
si falta; conserva las tablas y datos actuales.

**Sólo si todavía falta el modo Choose**, corré el seed (`python -m app.seed`): agrega la columna
`dialogue_turns.answer_options` a las bases que ya existían y carga las 615 respuestas
del modo Choose. Es idempotente y no borra progreso. Sin eso, los diálogos caen al
fallback (respuesta modelo + helper_phrases) en vez de mostrar las opciones escritas.

Las pruebas usan SQLite en memoria y servicios de voz/gramática simulados:

```powershell
# Desde backend/
python -B -m unittest discover -s tests -v
python -m pip check
```

```powershell
# Desde la raíz
node --test frontend/tests/regressions.test.cjs
```

La prueba opcional `frontend/tests/browser-smoke.cjs` usa Playwright y Chrome,
una API simulada y un servidor estático en `PREVIEW_URL` (por defecto
`http://127.0.0.1:8765`). El servidor debe mapear `/static/` a `frontend/`.
La captura se guarda en la carpeta temporal del sistema.

Prueba E2E de las cinco mejoras, con API real y SQLite en memoria (no toca MySQL):

```powershell
# Terminal 1, desde backend/
python -B -m uvicorn tests.preview_app:app --host 127.0.0.1 --port 8766
# Terminal 2, desde la raíz, con Playwright instalado y Chrome disponible
node frontend/tests/practice-browser.cjs
```

Reiniciá ese servidor de prueba entre ejecuciones para recrear sus datos ficticios.
La voz se simula: estas pruebas no validan precisión del micrófono ni disponibilidad
de Edge TTS. No se debe publicar `tests.preview_app`.

Hecho con ❤️ para William, que quiere por fin **hablar y escribir inglés** sin pagar suscripciones.
