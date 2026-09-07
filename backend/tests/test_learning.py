"""Regresiones de aprendizaje con SQLite en memoria y sin servicios externos."""
import asyncio
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, Module, Lesson, Topic, Attempt, UserProgress, SrsCard
from app.routers import attempts
from app.schemas.attempt import AttemptRoundIn
from app.services import analyzer, feynman_engine
from app.services.text_utils import matches_term
from app.services.dialogue_engine import _keyword_coverage, evaluate_turn
from app.routers import dictation
from app.models.dictation import DictationExercise
from fastapi import HTTPException
from pydantic import ValidationError
from datetime import datetime, date, timedelta
from app.services import gamification
from app.routers import progress as progress_router, curriculum
from app.services import whisper_stt


class DatabaseCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()
        self.user = User(email="test@example.com", username="test", password_hash="unused")
        module = Module(slug="test", title_es="Prueba", title_en="Test", description_es="Prueba")
        lesson = Lesson(slug="test", title_es="Prueba", title_en="Test", objective_es="Prueba", module=module)
        self.topic = Topic(slug="test", prompt_es="Prueba", prompt_en="Test", example_en="Hello, my name is Alex.", lesson=lesson)
        self.db.add_all([self.user, module, lesson, self.topic])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def new_attempt(self):
        attempt = Attempt(user_id=self.user.id, topic_id=self.topic.id)
        self.db.add(attempt)
        self.db.commit()
        return attempt

    def submit_mastered(self, attempt):
        result = dict(overall_score=.9, fluency_score=.9, code_switch_rate=0.,
                      error_density=0., word_count=20, encouragement_es="Bien",
                      next_action="MASTERED", errors=[], vocab_coverage=1.,
                      connector_coverage=1., socratic_questions=[])
        with patch.object(feynman_engine, "evaluate_round", return_value=result):
            return asyncio.run(attempts.submit_round(
                AttemptRoundIn(attempt_id=attempt.id, transcript="Hello, my name is Alex.", duration_seconds=20),
                db=self.db, user=self.user,
            ))


class ProgressTests(DatabaseCase):
    def test_today_is_included_in_streak_and_mastery_matches_path(self):
        for days in range(1, 7):
            self.db.add(Attempt(user_id=self.user.id, topic_id=self.topic.id,
                                mastered=True, stage="DONE", word_count=20,
                                completed_at=datetime.combine(date.today() - timedelta(days=days), datetime.min.time())))
        self.db.commit()
        self.submit_mastered(self.new_attempt())
        self.assertEqual(self.user.streak_days, 7)
        self.assertEqual(progress_router.summary(self.db, self.user)["mastered_topics"], 1)
        path = curriculum.learning_path(self.db, self.user)
        self.assertEqual(path["modules"][0]["lessons"][0]["topics"][0]["status"], "mastered")

    def test_abandoned_attempt_does_not_create_a_streak(self):
        self.db.add(Attempt(user_id=self.user.id, topic_id=self.topic.id, stage="ABANDONED", completed_at=datetime.now()))
        self.db.commit()
        self.assertEqual(gamification.calculate_streak(self.db, self.user), 0)

    def test_first_mastery_is_saved_and_can_be_reviewed(self):
        self.submit_mastered(self.new_attempt())
        progress = self.db.query(UserProgress).one()
        self.assertEqual((progress.attempts_count, progress.mastery_level), (1, 1))
        self.assertEqual(self.user.total_xp, 10)
        self.assertEqual(self.db.query(SrsCard).count(), 1)
        self.submit_mastered(self.new_attempt())
        self.db.refresh(progress)
        self.assertEqual((progress.attempts_count, progress.mastery_level), (2, 2))
        self.assertEqual(self.db.query(SrsCard).count(), 1)


class DictationTests(DatabaseCase):
    def test_server_target_and_one_reward_per_exercise(self):
        data = dictation.next_sentence(db=self.db, user=self.user)
        self.assertNotIn("tts_text", data)
        exercise = self.db.get(DictationExercise, data["dictation_id"])
        payload = dictation.DictationCheckIn(dictation_id=exercise.id, user_input=exercise.target)
        first = dictation.check(payload, db=self.db, user=self.user)
        second = dictation.check(payload, db=self.db, user=self.user)
        self.assertEqual((first["xp_awarded"], second["xp_awarded"], self.user.total_xp), (3, 0, 3))

    def test_cannot_choose_target_or_check_another_users_exercise(self):
        data = dictation.next_sentence(db=self.db, user=self.user)
        with self.assertRaises(ValidationError):
            dictation.DictationCheckIn(dictation_id=data["dictation_id"], user_input="fake", target_sentence="fake")
        payload = dictation.DictationCheckIn(dictation_id=data["dictation_id"], user_input="fake")
        with self.assertRaises(HTTPException) as exc:
            dictation.check(payload, db=self.db, user=SimpleNamespace(id=999))
        self.assertEqual(exc.exception.status_code, 404)
        self.assertEqual(dictation.check(payload, db=self.db, user=self.user)["xp_awarded"], 0)


class SpeechTests(unittest.TestCase):
    def test_short_real_utterances_survive_and_silence_does_not(self):
        for text in ("Thank you.", "Bye.", "Okay."):
            self.assertEqual(whisper_stt._clean(text), text)
            self.assertEqual(whisper_stt._clean(text, silence_likely=True), "")
        segment = SimpleNamespace(text="Thank you.", no_speech_prob=.05, avg_logprob=-.2)
        model = SimpleNamespace(transcribe=lambda *a, **kw: (iter([segment]), SimpleNamespace(duration_after_vad=.8)))
        with patch.object(whisper_stt, "get_model", return_value=model):
            self.assertEqual(whisper_stt.transcribe(b"mock"), "Thank you.")
        model.transcribe = lambda *a, **kw: (iter([segment]), SimpleNamespace(duration_after_vad=0))
        with patch.object(whisper_stt, "get_model", return_value=model):
            self.assertEqual(whisper_stt.transcribe(b"mock"), "")


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).parents[1] / "app/data/curriculum/a1_curriculum.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.topics = [SimpleNamespace(**t) for m in data["modules"] for l in m["lessons"] for t in l["topics"]]

    def evaluate(self, topic, text, mode="write"):
        async def local_grammar(value):
            return analyzer.apply_custom_rules(value)
        with patch.object(analyzer, "check_grammar", side_effect=local_grammar):
            return asyncio.run(feynman_engine.evaluate_round(topic, text, max(1, round(len(text.split()) / 1.5)), mode=mode))

    def test_all_model_answers_pass_with_local_rules(self):
        for topic in self.topics:
            self.assertIn(topic.slug, feynman_engine.ASSESSMENT)
            for mode in ("write", "speak"):
                with self.subTest(topic=topic.slug, mode=mode):
                    self.assertEqual(self.evaluate(topic, topic.example_en, mode)["next_action"], "MASTERED")

    def test_unrelated_fluent_answer_does_not_pass(self):
        text = "I work in a quiet office. Yesterday I went to the park because the weather was nice. Tomorrow I will cook dinner and then watch a movie."
        for topic in self.topics[:4]:
            with self.subTest(topic=topic.slug):
                self.assertNotEqual(self.evaluate(topic, text)["next_action"], "MASTERED")

    def test_personalized_age_is_accepted(self):
        topic = next(t for t in self.topics if t.slug == "my-age")
        self.assertEqual(self.evaluate(topic, "I'm twenty seven years old. I feel young and happy.")["next_action"], "MASTERED")

    def test_word_boundaries_and_explicit_variants(self):
        self.assertFalse(matches_term("candy somewhere yesterday nothing", "and"))
        self.assertEqual(_keyword_coverage("yesterday nothing", [["yes"], ["no"]])[0], 0)
        self.assertTrue(matches_term("It costs two dollars.", "dollar"))
        self.assertTrue(matches_term("I haven't called my mom yet.", "I haven't ... yet"))
        self.assertTrue(matches_term("I kept going and it is paying off.", "keep going"))
        self.assertTrue(matches_term("I wake up at 6:30.", "at six thirty"))


class DialogueAssessmentTests(unittest.TestCase):
    """La app no puede rechazar las respuestas que ella misma ofrece.

    Regresión concreta: cuando `required_keywords` pesaba 0.50 del score,
    316 de 599 helper_phrases y 5 de 205 respuestas modelo NO pasaban su
    propio scoring. El usuario tocaba una sugerencia y la app le decía
    "Try again" sin explicar nada.
    """

    def setUp(self):
        path = Path(__file__).parents[1] / "app/data/curriculum/dialogues.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.user_turns = [
            t
            for d in data["dialogues"]
            for t in d["turns"]
            if t["speaker"] == "USER"
        ]

    def _offered(self, turn):
        """Todo lo que la app le muestra al usuario como respuesta válida."""
        return [o["en"] for o in turn.get("answer_options") or []] + (
            turn.get("helper_phrases") or []
        )

    def _evaluate(self, turn, text):
        return evaluate_turn(
            text,
            turn.get("required_keywords") or [],
            turn.get("user_example_en") or "",
            self._offered(turn),
        )

    def test_every_offered_answer_passes(self):
        self.assertTrue(self.user_turns, "no se cargaron turnos USER")
        for turn in self.user_turns:
            for text in [turn.get("user_example_en") or "", *self._offered(turn)]:
                with self.subTest(text=text):
                    self.assertTrue(self._evaluate(turn, text)["passed"])

    def test_every_user_turn_has_answer_options(self):
        """El modo Choose es el default: un turno sin opciones deja al
        usuario sin guía, que es justo el bug que esto arregla."""
        for turn in self.user_turns:
            with self.subTest(hint=turn.get("user_hint_es")):
                options = turn.get("answer_options") or []
                self.assertGreaterEqual(len(options), 2)
                for o in options:
                    self.assertTrue(o.get("en"))
                    self.assertTrue(o.get("es"), "falta la traducción al español")

    def test_garbage_and_spanish_do_not_pass(self):
        # "no se que decir" cubría el grupo ["yes","no","please"] con el "no":
        # sin el corte por code-switch, pasaba.
        for text in ("asdf", "banana tractor purple sleeps", "no se que decir", "yo quiero comer"):
            for turn in self.user_turns:
                with self.subTest(text=text, hint=turn.get("user_hint_es")):
                    self.assertFalse(self._evaluate(turn, text)["passed"])

    def test_can_continue_offers_a_way_out_when_it_fails(self):
        turn = self.user_turns[0]
        result = self._evaluate(turn, "banana tractor purple sleeps")
        self.assertFalse(result["passed"])
        self.assertTrue(result["can_continue"], "el usuario quedaría trabado en el turno")


if __name__ == "__main__":
    unittest.main()
