# CLAUDE.md — DuoFeynman

Contexto del proyecto para Claude. Leé esto antes de tocar código.

## Qué es

App web para que **William** (dev en El Salvador, principiante A1 de inglés) aprenda a
**hablar y escribir** inglés con el **Método Feynman**: en vez de memorizar, *explica*
temas de su propia vida en inglés y un motor rule-based detecta errores, code-switching
y huecos de vocabulario.

**Objetivo del usuario:** de cero a B1, énfasis en hablar y enlazar ideas.

## Reglas duras (no negociables)

- **100% gratis, sin APIs pagas, sin claves, sin suscripciones.** Si una solución implica
  costo por uso, NO va. Esta es la restricción nº1 del proyecto.
- **Sin IA generativa** (no GPT, no Groq, no Claude API en runtime). Todo el feedback es
  **rule-based determinístico** — explicable, sin alucinaciones.
- **Español rioplatense/latino** para conversación con el usuario y comentarios en código.
- **NUNCA borrar/sobrescribir archivos del usuario sin confirmación explícita** (ver CLAUDE.md
  global). En Windows/Git Bash `rm` NO va a la papelera — es permanente.
- **Inmersión total en inglés en la UI**, con traducción al español al clic/hover (no oculta
  el inglés). El usuario fue enfático con esto.

## Stack

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy 2.0 + MySQL (pymysql). Pydantic v2.
- **Auth:** JWT (python-jose) + **bcrypt directo** (NO passlib — rompe con bcrypt 4.x).
  El hash trunca a 72 bytes: `_to_bytes(plain)[:72]`.
- **Frontend:** HTML/CSS/JS **vanilla** (sin framework). Mobile-first, listo para WebView Android.
- **STT:** Web Speech API (Chrome/Edge) → **faster-whisper offline** → **Vosk** (fallback).
  Orquestado en `services/stt.py`; `STT_ENGINE=auto|whisper|vosk` en `.env`.
- **TTS:** **Edge TTS** (online, gratis) → **Piper** (offline) → `speechSynthesis` (último recurso).
  Velocidad según nivel del usuario y caché de audio en disco (`services/tts.py`).
- **Gramática:** LanguageTool API pública (~20 req/min).
- **Rate limiting:** slowapi (por IP).
- **SRS:** algoritmo SM-2 simplificado.

## Gotchas conocidos (no repetir errores)

- **bcrypt:** usar el paquete `bcrypt` directo, NO passlib. Truncar a 72 bytes antes de hashear.
- **edge-tts:** requiere `>=7.0.2`. Versiones anteriores reciben **403** (Microsoft cambió la API).
- **piper-tts por pip en Windows:** FALLA (`piper-phonemize` no tiene wheels Windows).
  Usar el **binario standalone** en `backend/piper/piper.exe`.
- **MySQL TEXT/BLOB no admite DEFAULT:** para columnas TEXT usar `nullable=True`, no `default=""`.
  En ALTER: `ALTER TABLE ... ADD COLUMN x TEXT` + `UPDATE` aparte (no `DEFAULT ''`).
- **Vosk small (40MB)** confunde palabras ("yes that's right" → "yes that's why"). El usuario
  usa **vosk-model-en-us-0.22-lgraph** (128MB), renombrado a `vosk-en-small`. Ya es solo fallback:
  el motor principal es faster-whisper (`base.en`), más preciso Y más rápido (~0,8 s vs ~5,5 s).
- **Whisper alucina con silencio:** devuelve "Thank you.", "Thanks for watching!" y similares.
  Va con `vad_filter=True`, `condition_on_previous_text=False` y el filtro `_HALLUCINATIONS`.
- **Whisper devuelve dígitos** ("at 6", no "at six") y puntuación. Por eso `text_utils.normalize()`
  convierte números 0-100 a palabras: sin eso, hablar y escribir la misma respuesta no matchean.
- **Biasing de vocabulario:** el frontend manda los términos esperados (`hints`, separados por `|`)
  a `/api/attempts/transcribe` y Whisper los usa como `hotwords` — sesgo BLANDO.
  **NO usar la reconfiguración de vocabulario de Vosk:** es restricción DURA, lo que el usuario
  diga fuera de la lista vuelve como `[unk]` y se pierde justo lo que hay que analizar.
  Por el mismo motivo, nunca sesgar con la frase objetivo completa: el ejercicio se autoaprueba
  y le esconde al usuario sus propios errores.
- **El dictado NO usa micrófono:** es escuchar (TTS) y *escribir*. Cualquier idea de "sesgar el STT
  en dictado" no aplica.
- **STT y Piper son síncronos:** en endpoints async, llamarlos con `run_in_threadpool`
  (sino bloquean el loop). Cargar el modelo Whisper además va con lock: no es thread-safe.
- **edge-tts exige signo en el rate:** `"0%"` lanza `ValueError`, va `"+0%"`.
- **Code-switch detector:** cuidado con falsos positivos en nombres propios ("El Salvador").
  Hay PROPER_NOUNS_WHITELIST + chequeo de mayúsculas.
- **Detección de "passed":** los keywords requeridos NO deben ser demasiado estrictos. Se relajó
  a `score >= 0.75` o falta 1 grupo con `score >= 0.6`.

## Comandos clave

```powershell
# Backend (desde backend/)
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Recargar curriculum/diálogos (idempotente)
python -m app.seed

# Verificar sintaxis de un módulo editado
python -m py_compile app\services\gamification.py
```

```bash
# Validar JS (no hay build, es vanilla)
node --check frontend/js/app.js
```

La app se sirve en http://localhost:8000 (FastAPI sirve el frontend estático).

## Convenciones

- **Comentarios en español.** Código y nombres de símbolos en inglés cuando sea natural.
- **Frontend:** cada módulo JS es un IIFE que exporta un objeto global (`UI`, `TTS`, `API`,
  `Dialogues`, etc.). No hay imports/bundler.
- **Toasts, no alerts:** usar `UI.toast(msg, {type})` para feedback, nunca `alert()`.
- **Traducciones:** patrón "click para ver español" con `.es-inline` inyectado, sin ocultar el inglés.
- **Tema:** `data-theme="dark"` en `<html>`, persiste en `localStorage` (`duofeynman_theme`).
- **Seguridad en producción:** con `APP_ENV=production` la app aborta el arranque si SECRET_KEY,
  CORS o DB_PASSWORD son inseguros. Ver `config.py` y `SECURITY.md`.

## Curriculum

- `backend/app/data/curriculum/a1_curriculum.json` — 16 módulos A1→B1, 62 topics.
- `backend/app/data/curriculum/dialogues.json` — 51 diálogos guionados (con `setting_en`/`setting_es`).
- Estructura: `modules → lessons → topics`. Cada topic tiene `prompt_en/es`, `key_vocabulary`,
  `connectors`, `socratic_hints`, `difficulty`.

## Estado actual

Cubierto hasta **B1**. No agregar B2 todavía (decisión del usuario: "lleguemos hasta B1").
Features pendientes priorizadas: listening comprehension, dificultad adaptativa.

## Archivos sensibles (NUNCA commitear)

`.env`, `backend/models/vosk-en-small/`, `backend/piper/`, `backend/models/piper/`, `*.onnx`,
`*.wav`. Ya están en `.gitignore`. El `.env.example` SÍ se commitea (sin secretos reales).
