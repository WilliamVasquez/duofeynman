# Graph Report - .  (2026-06-18)

## Corpus Check
- 61 files · ~59,476 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 354 nodes · 603 edges · 33 communities (21 shown, 12 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 156 edges (avg confidence: 0.55)
- Token cost: 4,200 input · 1,800 output

## Community Hubs (Navigation)
- [[_COMMUNITY_DB + Seeds|DB + Seeds]]
- [[_COMMUNITY_Attempt Schemas + Routing|Attempt Schemas + Routing]]
- [[_COMMUNITY_Progress + Auth Routing|Progress + Auth Routing]]
- [[_COMMUNITY_App Concepts + Docs|App Concepts + Docs]]
- [[_COMMUNITY_Transcript Analyzer|Transcript Analyzer]]
- [[_COMMUNITY_Config + Settings|Config + Settings]]
- [[_COMMUNITY_Pydantic Schemas|Pydantic Schemas]]
- [[_COMMUNITY_Feynman Engine|Feynman Engine]]
- [[_COMMUNITY_Frontend Orchestrator|Frontend Orchestrator]]
- [[_COMMUNITY_TTS Service|TTS Service]]
- [[_COMMUNITY_Vosk STT Service|Vosk STT Service]]
- [[_COMMUNITY_Gamification + Progress Models|Gamification + Progress Models]]
- [[_COMMUNITY_Auth Router|Auth Router]]
- [[_COMMUNITY_Dictation Router|Dictation Router]]
- [[_COMMUNITY_PWA Manifest|PWA Manifest]]
- [[_COMMUNITY_SRS Router|SRS Router]]
- [[_COMMUNITY_SRS Algorithm SM-2|SRS Algorithm SM-2]]
- [[_COMMUNITY_Frontend API Client|Frontend API Client]]
- [[_COMMUNITY_Dashboard UI|Dashboard UI]]
- [[_COMMUNITY_Dialogues UI|Dialogues UI]]
- [[_COMMUNITY_Dictation UI|Dictation UI]]
- [[_COMMUNITY_Profile State|Profile State]]
- [[_COMMUNITY_Profile View|Profile View]]
- [[_COMMUNITY_Speech Recognition|Speech Recognition]]
- [[_COMMUNITY_SRS UI|SRS UI]]
- [[_COMMUNITY_TTS Frontend|TTS Frontend]]
- [[_COMMUNITY_UI Utilities|UI Utilities]]
- [[_COMMUNITY_ORM Models Init|ORM Models Init]]
- [[_COMMUNITY_Rate Limiting|Rate Limiting]]

## God Nodes (most connected - your core abstractions)
1. `User` - 38 edges
2. `Topic` - 20 edges
3. `Base` - 18 edges
4. `DuoFeynman App` - 17 edges
5. `Attempt` - 14 edges
6. `SrsCard` - 14 edges
7. `AttemptError` - 12 edges
8. `UserProgress` - 12 edges
9. `evaluate_round()` - 12 edges
10. `Session` - 11 edges

## Surprising Connections (you probably didn't know these)
- `DuoFeynman App Icon 192px (SVG)` --brand_icon_for--> `DuoFeynman App`  [EXTRACTED]
  frontend/assets/icon-192.svg → README.md
- `DuoFeynman App Icon 512px (SVG)` --brand_icon_for--> `DuoFeynman App`  [EXTRACTED]
  frontend/assets/icon-512.svg → README.md
- `DuoFeynman App Icon (SVG)` --brand_icon_for--> `DuoFeynman App`  [EXTRACTED]
  frontend/assets/icon.svg → README.md
- `DuoFeynman App Icon 192px (SVG)` --used_by--> `PWA (Progressive Web App)`  [INFERRED]
  frontend/assets/icon-192.svg → README.md
- `DuoFeynman App Icon 512px (SVG)` --used_by--> `PWA (Progressive Web App)`  [INFERRED]
  frontend/assets/icon-512.svg → README.md

## Import Cycles
- None detected.

## Communities (33 total, 12 thin omitted)

### Community 0 - "DB + Seeds"
Cohesion: 0.11
Nodes (26): Base, Conexión a MySQL vía SQLAlchemy., Carga inicial del curriculum desde JSON.  Uso:     python -m app.seed, seed(), Session, User, Session, User (+18 more)

### Community 1 - "Attempt Schemas + Routing"
Cohesion: 0.16
Nodes (27): AttemptRoundIn, AttemptStartIn, Request, Session, User, Session, User, Attempt (+19 more)

### Community 2 - "Progress + Auth Routing"
Cohesion: 0.11
Nodes (25): Session, User, Session, User, Request, User, User, Perfil del usuario para personalizar la experiencia.  Es opcional — el usuario p (+17 more)

### Community 3 - "App Concepts + Docs"
Cohesion: 0.08
Nodes (29): DuoFeynman App Icon 192px (SVG), DuoFeynman App Icon 512px (SVG), DuoFeynman App Icon (SVG), Android WebView (migración futura), Backend Stack (Python/FastAPI/MySQL), Etapa CONSOLIDATE, Curriculum A1 Principiante, Etapa DETECT (+21 more)

### Community 4 - "Transcript Analyzer"
Cohesion: 0.11
Nodes (25): analyze_transcript(), apply_custom_rules(), check_grammar(), compute_fluency(), count_fillers(), count_sentences(), detect_code_switching(), has_question() (+17 more)

### Community 5 - "Config + Settings"
Cohesion: 0.11
Nodes (13): get_settings(), Configuración central de la app. Lee variables desde .env., Valida la config crítica al arranque. Falla rápido si algo es inseguro., Settings, _validate_settings(), global_exception_handler(), rate_limit_handler(), DuoFeynman — backend principal. (+5 more)

### Community 6 - "Pydantic Schemas"
Cohesion: 0.15
Nodes (16): BaseModel, AttemptOut, AttemptRoundIn, AttemptStartIn, Config, ErrorOut, FeedbackOut, Config (+8 more)

### Community 7 - "Feynman Engine"
Cohesion: 0.16
Nodes (18): Any, build_corrections(), build_socratic_questions(), compute_overall_score(), compute_subscores(), _coverage(), decide_next_action(), evaluate_round() (+10 more)

### Community 8 - "Frontend Orchestrator"
Cohesion: 0.18
Nodes (11): ensureAttempt(), enterApp(), openTopic(), _pickN(), refreshHeader(), _renderProfileCard(), _renderWeekPanel(), sendRound() (+3 more)

### Community 9 - "TTS Service"
Cohesion: 0.28
Nodes (15): Path, _pcm_to_wav(), _piper_binary_path(), _piper_model_path(), _piper_ready(), Text-to-Speech con dos backends en cascada.  1. Edge TTS — voces Microsoft Neura, Envuelve PCM s16le mono en un contenedor WAV., Genera MP3 con Microsoft Edge TTS (online, neural).      No hacemos pre-check de (+7 more)

### Community 10 - "Vosk STT Service"
Cohesion: 0.23
Nodes (14): Path, Model, available(), diagnose(), get_model(), _has_ffmpeg(), _model_dir(), Speech-to-Text offline con Vosk.  Descargá el modelo `vosk-model-small-en-us-0.1 (+6 more)

### Community 11 - "Gamification + Progress Models"
Cohesion: 0.23
Nodes (12): Attempt, Session, User, Achievement, Progreso del usuario y gamificación., Logros desbloqueables (gamificación)., UserAchievement, award_achievements() (+4 more)

### Community 12 - "Auth Router"
Cohesion: 0.23
Nodes (12): Request, Session, login(), register(), Token, create_access_token(), hash_password(), Hash de contraseñas (bcrypt directo) y JWT.  Usamos `bcrypt` directamente en vez (+4 more)

### Community 13 - "Dictation Router"
Cohesion: 0.23
Nodes (13): Session, User, check(), DictationCheckIn, func_random(), next_sentence(), _normalize(), Modo dictado: TTS lee una frase, usuario escribe lo que escuchó.  Es independien (+5 more)

### Community 14 - "PWA Manifest"
Cohesion: 0.17
Nodes (11): background_color, description, display, icons, lang, name, orientation, scope (+3 more)

### Community 15 - "SRS Router"
Cohesion: 0.38
Nodes (6): Session, User, due_cards(), Endpoints de Spaced Repetition System., Tarjetas SRS que vencen hoy o antes., stats()

### Community 16 - "SRS Algorithm SM-2"
Cohesion: 0.33
Nodes (5): Algoritmo de repetición espaciada (SM-2 simplificado).  Calidad de respuesta (q), Mapea score 0-1 a calidad SM-2 0-5., review_card(), score_to_quality(), SrsCard

## Knowledge Gaps
- **42 isolated node(s):** `Config`, `Config`, `Config`, `Path`, `Model` (+37 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `User` connect `Progress + Auth Routing` to `DB + Seeds`, `Attempt Schemas + Routing`, `Gamification + Progress Models`, `Auth Router`, `Dictation Router`, `SRS Router`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Why does `Base` connect `DB + Seeds` to `Attempt Schemas + Routing`, `Progress + Auth Routing`, `Gamification + Progress Models`, `Config + Settings`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `Topic` connect `DB + Seeds` to `Attempt Schemas + Routing`, `SRS Router`, `Dictation Router`, `Feynman Engine`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `User` (e.g. with `Attempt` and `AttemptRoundIn`) actually correct?**
  _`User` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `Topic` (e.g. with `Any` and `AttemptRoundIn`) actually correct?**
  _`Topic` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Base` (e.g. with `Exception` and `Request`) actually correct?**
  _`Base` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `DuoFeynman App` (e.g. with `JWT Authentication (bcrypt rounds=12)` and `Rate Limiting por IP`) actually correct?**
  _`DuoFeynman App` has 2 INFERRED edges - model-reasoned connections that need verification._