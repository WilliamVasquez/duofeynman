# Graph Report - ingles  (2026-09-07)

## Corpus Check
- 76 files · ~99,820 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 600 nodes · 1259 edges · 46 communities (30 shown, 16 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 122 edges (avg confidence: 0.9)
- Token cost: 277,488 input · 0 output

## Community Hubs (Navigation)
- App Core & Data Models
- Auth & User Records
- Audio Pipeline & STT Orchestration
- Feynman Attempts & SRS Cards
- TTS Synthesis & Audio Cache
- Config & Whisper Engine
- Linguistic Analyzer
- Feynman Scoring Engine
- Frontend Orchestrator
- Dialogue Engine & Text Matching
- Zero-Cost Voice Stack Decisions
- Pydantic Schemas
- User Profile Endpoints
- App Icon Visual Identity
- PWA Manifest
- Dialogue Regression Tests
- Frontend Regression Tests
- Product Stack Overview
- Feynman Cycle Stages
- Curriculum & Migration Rules
- Browser Smoke Test
- Error Handling Middleware
- Security Hardening
- Auth & Frontend Conventions
- Test Scaffolding
- Curriculum Assessment Tests
- Immersion UI & Input Modes
- Standalone Icon Asset
- Project Identity
- Production Deployment Rules
- API Client Module
- Curriculum Translations
- Progress Dashboard
- Dialogues UI Module
- Dictation UI Module
- i18n Module
- Profile State Module
- Profile Editor View
- Speech Capture Module
- SRS Review Panel
- LocalStorage Wrapper
- TTS Playback Module
- UI Rendering & Toasts
- Orphan Pydantic Base

## God Nodes (most connected - your core abstractions)
1. `User` - 48 edges
2. `Base` - 30 edges
3. `Topic` - 26 edges
4. `utcnow()` - 22 edges
5. `Attempt` - 17 edges
6. `submit_round()` - 17 edges
7. `evaluate_round()` - 17 edges
8. `DuoFeynman App` - 14 edges
9. `SrsCard` - 14 edges
10. `Lesson` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Rate Limiting por IP` --semantically_similar_to--> `language-tool-python (chequeo gramatical)`  [INFERRED] [semantically similar]
  SECURITY.md → backend/requirements.txt
- `DuoFeynman App` --implements--> `JWT Authentication (bcrypt rounds=12)`  [INFERRED]
  README.md → SECURITY.md
- `Estrategia de pruebas de regresion` --conceptually_related_to--> `Restriccion 100% gratis (sin APIs pagas)`  [INFERRED]
  README.md → CLAUDE.md
- `DuoFeynman App` --implements--> `Rate Limiting por IP`  [INFERRED]
  README.md → SECURITY.md
- `Ciclo Feynman 5 Etapas` --references--> `language-tool-python (chequeo gramatical)`  [EXTRACTED]
  README.md → backend/requirements.txt

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Stack de fallback de voz (STT + TTS) impuesto por la restriccion de costo cero** — claude_zero_cost_constraint, claude_stt_fallback_chain, claude_tts_fallback_chain, backend_requirements_faster_whisper_dep, backend_requirements_edge_tts_pin, readme_piper_windows_standalone, readme_browser_support_matrix [INFERRED 0.85]
- **Flujo del modo Choose en dialogos (datos, motor, migracion y UI)** — claude_dialogue_engine_guide_not_exam, claude_answer_options_requirement, claude_add_column_if_missing, claude_localstorage_key_bump, frontend_index_chat_input_modes, readme_dialogue_input_modes, claude_visible_feedback_rule [EXTRACTED 0.95]
- **Hardening de produccion (config, transporte, DB, auth, observabilidad)** — security_production_config_validation, security_https_reverse_proxy, security_least_privilege_db_user, security_rate_limiting, security_password_policy, security_jwt_bearer_architecture, security_audit_log, security_known_gaps [EXTRACTED 1.00]
- **DuoFeynman Icon Visual Identity System** — frontend_assets_icon_192_app_icon, frontend_assets_icon_192_brand_gradient, frontend_assets_icon_192_df_monogram, frontend_assets_icon_192_microphone_badge [EXTRACTED 1.00]
- **DuoFeynman Visual Identity System (gradient + monogram + mic badge)** — frontend_assets_icon_512_app_icon, frontend_assets_icon_192_brand_gradient, frontend_assets_icon_192_df_monogram, frontend_assets_icon_512_mic_badge [INFERRED 0.85]
- **App Icon Visual Identity System (gradient tile + DF monogram + mic badge)** — frontend_assets_icon_gradient_g, frontend_assets_icon_df_monogram, frontend_assets_icon_mic_badge, frontend_assets_icon_app_icon [EXTRACTED 1.00]

## Communities (46 total, 16 thin omitted)

### Community 0 - "App Core & Data Models"
Cohesion: 0.07
Nodes (69): Base, get_db(), Conexión a MySQL vía SQLAlchemy., on_startup(), DuoFeynman — backend principal., AttemptError, Errores específicos detectados (para análisis y SRS targeted)., Lesson (+61 more)

### Community 1 - "Auth & User Records"
Cohesion: 0.08
Nodes (40): Intentos del usuario explicando un Topic (ciclo Feynman)., DictationExercise, Ejercicios de dictado: respuesta y recompensa controladas por el servidor., Perfil del usuario para personalizar la experiencia. Es opcional — el usuario…, login(), limit, post, Request (+32 more)

### Community 2 - "Audio Pipeline & STT Orchestration"
Cohesion: 0.08
Nodes (42): health(), get, root(), get, stt_status(), AudioError, has_ffmpeg(), Exception (+34 more)

### Community 3 - "Feynman Attempts & SRS Cards"
Cohesion: 0.08
Nodes (32): Attempt, Un intento = una sesión de explicación de un Topic. El ciclo Feynman puede…, Una tarjeta SRS = algo que el usuario debe recordar/practicar. Puede ser: - Un…, SrsCard, limit, post, Request, Session (+24 more)

### Community 4 - "TTS Synthesis & Audio Cache"
Cohesion: 0.10
Nodes (39): get, limit, Request, status(), synthesize(), _cache_dir(), _cache_get(), _cache_key() (+31 more)

### Community 5 - "Config & Whisper Engine"
Cohesion: 0.09
Nodes (24): get_settings(), Configuración central de la app. Lee variables desde .env., Valida la config crítica al arranque. Falla rápido si algo es inseguro., Settings, _validate_settings(), available(), build_hotwords(), _clean() (+16 more)

### Community 6 - "Linguistic Analyzer"
Cohesion: 0.13
Nodes (21): analyze_transcript(), apply_custom_rules(), check_grammar(), compute_fluency(), count_fillers(), count_sentences(), detect_code_switching(), detect_self_corrections() (+13 more)

### Community 7 - "Feynman Scoring Engine"
Cohesion: 0.15
Nodes (20): Any, build_corrections(), build_socratic_questions(), check_objective(), compute_overall_score(), compute_subscores(), _coverage(), decide_next_action() (+12 more)

### Community 8 - "Frontend Orchestrator"
Cohesion: 0.18
Nodes (17): ensureAttempt(), enterApp(), _findAxisInList(), _loadPath(), openTopic(), openTopicFromPath(), _openView(), _pickN() (+9 more)

### Community 9 - "Dialogue Engine & Text Matching"
Cohesion: 0.18
Nodes (15): _best_similarity(), evaluate_turn(), _keyword_coverage(), Motor de validación de respuestas en diálogos guionados. Rule-based, sin IA.…, Devuelve (cobertura, grupos_no_cubiertos). `groups` es una lista de listas.…, Similitud contra la mejor respuesta aceptada. Devuelve (ratio, cual)., Evalúa una respuesta de usuario en un diálogo. `accepted_answers`: todas las…, _digits_to_words() (+7 more)

### Community 10 - "Zero-Cost Voice Stack Decisions"
Cohesion: 0.13
Nodes (18): edge-tts>=7.0.2 (pin obligatorio), faster-whisper (motor STT principal), piper-tts comentado en requirements, Colores por token CSS, nunca hex fijo, Sin IA generativa en runtime, STT y Piper sincronos -> run_in_threadpool, Cadena de fallback STT (Web Speech -> faster-whisper -> Vosk), text_utils.normalize() (numeros a palabras) (+10 more)

### Community 11 - "Pydantic Schemas"
Cohesion: 0.23
Nodes (13): Config, LessonOut, ModuleOut, BaseModel, TopicOut, Config, BaseModel, field_validator (+5 more)

### Community 12 - "User Profile Endpoints"
Cohesion: 0.20
Nodes (13): UserProfile, Config, get_profile(), ProfileIn, ProfileOut, put_profile(), BaseModel, field_validator (+5 more)

### Community 13 - "App Icon Visual Identity"
Cohesion: 0.26
Nodes (12): DuoFeynman App Icon (192px SVG), Brand Gradient (sky #0ea5e9 to indigo #6366f1), DF Monogram Wordmark, Microphone Badge (amber circle, speaking affordance), PWA / Android WebView Launcher Identity, Scalable Vector Asset (512 viewBox, no raster dependency), Speaking-First Product Positioning, System Font Stack (-apple-system, Segoe UI, sans-serif) (+4 more)

### Community 14 - "PWA Manifest"
Cohesion: 0.17
Nodes (11): background_color, description, display, icons, lang, name, orientation, scope (+3 more)

### Community 15 - "Dialogue Regression Tests"
Cohesion: 0.27
Nodes (4): DialogueAssessmentTests, La app no puede rechazar las respuestas que ella misma ofrece. Regresión…, Todo lo que la app le muestra al usuario como respuesta válida., El modo Choose es el default: un turno sin opciones deja al usuario sin guía,…

### Community 16 - "Frontend Regression Tests"
Cohesion: 0.18
Nodes (5): assert, fs, path, { test }, vm

### Community 17 - "Product Stack Overview"
Cohesion: 0.18
Nodes (11): Android WebView (migración futura), Backend Stack (Python/FastAPI/MySQL), Curriculum A1 Principiante, DuoFeynman App, Método Feynman + Output Hypothesis, Frontend Stack (HTML/CSS/JS vanilla), PWA (Progressive Web App), STT Vosk Offline (+3 more)

### Community 18 - "Feynman Cycle Stages"
Cohesion: 0.22
Nodes (10): Etapa CONSOLIDATE, Etapa DETECT, Etapa EXPLAIN, Etapa EXPOSE, Ciclo Feynman 5 Etapas, Motor Feynman Rule-Based, LanguageTool API (Gramática), Output Hypothesis (+2 more)

### Community 19 - "Curriculum & Migration Rules"
Cohesion: 0.22
Nodes (9): Migracion con _add_column_if_missing() en seed.py, answer_options obligatorio por turno USER, Techo en B1 (no agregar B2 todavia), Code-switch detector (ES->EN), Estructura del curriculum (modules -> lessons -> topics), El motor de dialogos es guia, no examen, MySQL TEXT/BLOB/JSON no admite DEFAULT, Estrategia de pruebas de regresion (+1 more)

### Community 20 - "Browser Smoke Test"
Cohesion: 0.22
Nodes (8): assert, {chromium}, data, fs, path, profile, topics, user

### Community 21 - "Error Handling Middleware"
Cohesion: 0.29
Nodes (8): global_exception_handler(), Exception, Request, rate_limit_handler(), security_headers(), exception_handler, middleware, RateLimitExceeded

### Community 22 - "Security Hardening"
Cohesion: 0.33
Nodes (7): language-tool-python (chequeo gramatical), Audit Log de intentos de login, DuoFeynman Security Guide, HTTPS Reverse Proxy (Caddy/Nginx), JWT Authentication (bcrypt rounds=12), Rate Limiting por IP, SQLAlchemy ORM (protección SQL injection)

### Community 23 - "Auth & Frontend Conventions"
Cohesion: 0.29
Nodes (7): bcrypt directo (no passlib), Convencion frontend: IIFE con objeto global, Orden de carga de scripts globales, Shell de vistas single-page (#app + section.view), Arquitectura JWT-bearer (sin cookies de sesion), Limitaciones de seguridad conscientes, Password policy + login error generico

### Community 26 - "Immersion UI & Input Modes"
Cohesion: 0.40
Nodes (6): Inmersion total en ingles en la UI, Bump de key en localStorage al cambiar defaults, Feedback visible, no en title=, Toolbars de los tres modos de input del chat, Traduccion inline con data-es, Tres modos de respuesta en dialogos (Choose / Write-Speak / Order words)

### Community 27 - "Standalone Icon Asset"
Cohesion: 0.47
Nodes (6): DuoFeynman App Icon (512x512 SVG), Dependency-Free Inline SVG Asset, DF Monogram Wordmark, Brand Linear Gradient (sky #0ea5e9 to indigo #6366f1), Microphone Badge (amber circle, bottom-right), Speech-First Product Branding

### Community 28 - "Project Identity"
Cohesion: 0.67
Nodes (4): DuoFeynman (project), Feynman Method (pedagogical core), Formulario de perfil (contexto Feynman), Superficie de endpoints REST

### Community 29 - "Production Deployment Rules"
Cohesion: 0.50
Nodes (4): Archivos sensibles que nunca se commitean, HTTPS via reverse proxy (Caddy/Nginx/Cloudflare), Usuario de DB dedicado con privilegios minimos, Validacion de config con APP_ENV=production

## Ambiguous Edges - Review These
- `Colores por token CSS, nunca hex fijo` → `Metadatos PWA e instalabilidad`  [AMBIGUOUS]
  frontend/index.html · relation: conceptually_related_to

## Knowledge Gaps
- **60 isolated node(s):** `Etapa EXPOSE`, `Etapa EXPLAIN`, `Etapa REFINE`, `Backend Stack (Python/FastAPI/MySQL)`, `Frontend Stack (HTML/CSS/JS vanilla)` (+55 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Colores por token CSS, nunca hex fijo` and `Metadatos PWA e instalabilidad`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `User` connect `App Core & Data Models` to `Auth & User Records`, `Audio Pipeline & STT Orchestration`, `Feynman Attempts & SRS Cards`, `TTS Synthesis & Audio Cache`, `User Profile Endpoints`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `Topic` connect `App Core & Data Models` to `Test Scaffolding`, `Auth & User Records`, `Feynman Attempts & SRS Cards`, `Feynman Scoring Engine`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `DialogueAssessmentTests` connect `Dialogue Regression Tests` to `Test Scaffolding`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `User` (e.g. with `start_attempt()` and `stt_status()`) actually correct?**
  _`User` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Base` (e.g. with `on_startup()` and `seed()`) actually correct?**
  _`Base` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `Topic` (e.g. with `start_attempt()` and `submit_round()`) actually correct?**
  _`Topic` has 10 INFERRED edges - model-reasoned connections that need verification._