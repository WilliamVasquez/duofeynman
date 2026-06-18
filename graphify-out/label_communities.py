import sys, json
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from pathlib import Path

extraction = json.loads(Path(r'graphify-out\.graphify_extract.json').read_text(encoding='utf-8'))
detection  = json.loads(Path(r'graphify-out\.graphify_detect.json').read_text(encoding='utf-8-sig'))
analysis   = json.loads(Path(r'graphify-out\.graphify_analysis.json').read_text(encoding='utf-8'))

G = build_from_json(extraction)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
tokens = {'input': extraction.get('input_tokens', 0), 'output': extraction.get('output_tokens', 0)}

labels = {
    0: "DB + Seeds",
    1: "Attempt Schemas + Routing",
    2: "Progress + Auth Routing",
    3: "App Concepts + Docs",
    4: "Transcript Analyzer",
    5: "Config + Settings",
    6: "Pydantic Schemas",
    7: "Feynman Engine",
    8: "Frontend Orchestrator",
    9: "TTS Service",
    10: "Vosk STT Service",
    11: "Gamification + Progress Models",
    12: "Auth Router",
    13: "Dictation Router",
    14: "PWA Manifest",
    15: "SRS Router",
    16: "SRS Algorithm SM-2",
    17: "Frontend API Client",
    18: "Dashboard UI",
    19: "Dialogues UI",
    20: "Dictation UI",
    21: "Profile State",
    22: "Profile View",
    23: "Speech Recognition",
    24: "SRS UI",
    25: "TTS Frontend",
    26: "UI Utilities",
    27: "ORM Models Init",
    28: "Rate Limiting",
    29: "__init__ routers",
    30: "__init__ services",
    31: "__init__ schemas",
    32: "__init__ misc",
}

questions = suggest_questions(G, communities, labels)
report = generate(G, communities, cohesion, labels, analysis['gods'], analysis['surprises'], detection, tokens, '.', suggested_questions=questions)
Path(r'graphify-out\GRAPH_REPORT.md').write_text(report, encoding='utf-8')
Path(r'graphify-out\.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False), encoding='utf-8')
print('Report generado OK')
