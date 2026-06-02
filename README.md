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
| STT (Firefox + fallback) | **Vosk offline** + ffmpeg | gratis, 1× descarga 40 MB |
| TTS primario | **Edge TTS** (voces Microsoft Neural: Aria, Jenny, Guy...) | gratis, sin clave |
| TTS fallback offline | **Piper TTS** (neural local) | gratis, 1× descarga 63 MB |
| TTS último recurso | `speechSynthesis` del navegador | gratis (robótico) |
| Gramática | LanguageTool API pública | gratis (20 req/min) |
| Feedback Feynman | Motor rule-based propio | gratis |

**Sin IA generativa = comportamiento determinístico, explicable, sin alucinaciones.**

## Cómo aprende el usuario (motor Feynman)

Cada **Topic** del curriculum se ataca con un ciclo de 5 etapas:

1. **EXPOSE** — Mostramos el tema, vocabulario clave y un ejemplo modelo en audio
2. **EXPLAIN** — El usuario elige modo y produce inglés:
   - 🎤 **Hablar** — micrófono → texto (Web Speech en Chrome/Edge, Vosk en Firefox)
   - ✍️ **Escribir** — textarea (mejor para gramática, sin presión de pronunciación)
3. **DETECT** — Análisis rule-based:
   - Fluidez (palabras por minuto en modo Hablar; densidad en Escribir)
   - Code-switching ES→EN (palabras españolas detectadas con diccionario)
   - Gramática (LanguageTool)
   - Cobertura de vocabulario clave del topic
   - Cobertura de conectores sugeridos del topic
4. **REFINE** — Preguntas socráticas: combinación de `socratic_hints` fijas del curriculum + sugerencias generadas por templates (ej: *"Try saying it again using 'because'"*).
5. **CONSOLIDATE** — Si dominó (score ≥ 0.78), creamos una card SRS (algoritmo SM-2) que vuelve a aparecer en 1d, 3d, 7d, 21d...

## Setup paso a paso

### 1. Crear la base de datos en tu MySQL local

```sql
CREATE DATABASE duofeynman CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Instalar ffmpeg (necesario para Vosk con audio de navegador)

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

**Verificación rápida** (opcional):
```powershell
echo "hello world" | .\backend\piper\piper.exe --model .\backend\models\piper\en_US-amy-medium.onnx --output_file test.wav
```
Si genera `test.wav`, Piper está listo.

Si saltás este paso, el TTS funciona igual con Edge TTS (online) y como último recurso usa el TTS del navegador.

### 3b. Descargar modelo Vosk inglés (40 MB, una sola vez)

1. Ir a https://alphacephei.com/vosk/models
2. Descargar **vosk-model-small-en-us-0.15** (~40 MB)
3. Descomprimir en `backend/models/vosk-en-small/` (que el `model.conf` quede en esa ruta)

> Si solo usás Chrome/Edge, este paso es opcional — Web Speech API alcanza.
> Pero recomendado para que Firefox también funcione.

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
| **Firefox** | MediaRecorder → Vosk en el server (al soltar) | ✅ |
| **Android WebView** (futuro) | Web Speech API (Chrome WebView) | ✅ |

## Estructura del proyecto

```
duofeynman/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── seed.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   │   ├── feynman_engine.py   ← núcleo pedagógico rule-based
│   │   │   ├── vosk_stt.py         ← STT offline con Vosk
│   │   │   ├── analyzer.py         ← métricas + LanguageTool
│   │   │   ├── srs.py              ← repetición espaciada SM-2
│   │   │   └── security.py         ← JWT + bcrypt
│   │   └── data/curriculum/        ← lecciones en JSON
│   ├── models/vosk-en-small/       ← (descargar manualmente, ver paso 3)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── index.html                  ← responsive, mobile-first
    ├── css/styles.css
    └── js/
        ├── app.js                  ← orquestador
        ├── api.js                  ← cliente HTTP
        ├── speech.js               ← WebSpeech / MediaRecorder
        └── ui.js                   ← rendering
```

## Curriculum incluido (A1 principiante)

- **Survival** — saludos, presentación, sobre mí
- **Daily life** — rutina diaria (mañana/tarde), comida
- **Connecting ideas** ← tu zona clave: enlazar pensamientos con `because`, `so`, `that's why`, `when`...

Agregar más temas: editar `app/data/curriculum/a1_curriculum.json` y correr `python -m app.seed` (es idempotente).

## Migración a Android (WebView)

El frontend está pensado para vivir dentro de un `WebView` de Android sin cambios:
- 100% responsive mobile-first (`viewport-fit=cover`, safe-area-insets)
- Touch events para hold-to-talk
- En Android Chrome WebView (≥33) funciona Web Speech API

## Roadmap

- [x] Backend rule-based sin IA externa
- [x] Modo Hablar (Chrome/Edge + Firefox vía Vosk)
- [x] Modo Escribir
- [x] Curriculum A1 (5 módulos, 20+ topics)
- [x] TTS neural (Edge TTS + Piper offline + fallback navegador)
- [x] Selector de voz (7 voces US/UK/AU)
- [x] **Dashboard de progreso con gráficos de 7 días**
- [x] **Cálculo correcto de racha**
- [x] **Logros desbloqueables automáticos**
- [x] **Panel SRS de repaso diario (SM-2)**
- [x] **Modo Dictado para entrenar el oído**
- [x] **PWA: instalable en celu como app**
- [ ] Modo Conversación / Diálogos guionados (próximo)
- [ ] Más curriculum (A2, B1)
- [ ] Build de Android (WebView wrapper)

## Endpoints REST disponibles

| Endpoint | Para qué |
|---|---|
| `POST /api/auth/register` `/login` | Registro / login |
| `GET /api/me` | Perfil del usuario |
| `GET /api/curriculum/modules` | Lista de módulos + lecciones + topics |
| `POST /api/attempts/start` `/round` | Ciclo Feynman: iniciar + enviar respuesta |
| `POST /api/attempts/transcribe` | Sube audio → Vosk transcribe (Firefox) |
| `GET /api/progress/summary` `/dashboard` | Stats + gráficos + logros |
| `GET /api/srs/due` `/stats` | Cards SRS que vencen hoy |
| `GET /api/dictation/next` `POST /check` | Modo escucha-y-escribí |
| `GET /api/tts?text=...&voice=aria` | TTS neural (MP3 o WAV) |
| `GET /api/tts/status` | Qué backends TTS están disponibles |

---

Hecho con ❤️ para William, que quiere por fin **hablar y escribir inglés** sin pagar suscripciones.
