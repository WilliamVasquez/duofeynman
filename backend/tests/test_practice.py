"""Regresiones de las cinco mejoras: HTTP real, BD efímera, audio simulado."""
import unittest
from uuid import uuid4
from datetime import timedelta, datetime
from unittest.mock import patch, AsyncMock
import test_http
from app.models import Dialogue, DialogueTurn, DialogueResponse, DialogueSession, User, SrsCard, Topic, Attempt, DailyPlan, UserProfile, ListeningAttempt, Module, Lesson, UserProgress
from app.services import security, analyzer, error_drills, tts
from app.routers.listening import EXERCISES
from app.timeutils import utcnow, learning_day, learning_day_start


class PracticeTests(unittest.TestCase):
    tearDown = test_http.HttpTests.tearDown

    def setUp(self):
        test_http.HttpTests.setUp(self)
        self.dialogue = Dialogue(slug='practice', title_en='After work', title_es='Después del trabajo', description_es='Prueba',
            setting_en='You arrive home.', setting_es='Llegás a casa.', npc_name='Alex', npc_role_es='Amigo', level='A1')
        self.db.add(self.dialogue); self.db.flush()
        self.turns = []
        for i in range(2):
            self.db.add(DialogueTurn(dialogue_id=self.dialogue.id, order_index=i*2, speaker='NPC', npc_text_en='How are you?', npc_text_es='¿Cómo estás?'))
            turn = DialogueTurn(dialogue_id=self.dialogue.id, order_index=i*2+1, speaker='USER', user_hint_es='Contá cómo estás',
                user_example_en='I am tired.', required_keywords=[['tired', 'happy']], helper_phrases=['I am happy.'],
                answer_options=[{'en': 'I am tired.', 'es': 'Estoy cansado.'}, {'en': 'I am happy.', 'es': 'Estoy feliz.'}])
            self.db.add(turn); self.turns.append(turn)
        self.db.commit()

    def start(self):
        response = self.client.post(f'/api/dialogues/{self.dialogue.id}/session', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def answer(self, saved, text='I am tired.', mode='choose', used_help=False, response_id=None):
        session = saved['session']
        turn = saved['dialogue']['turns'][session['cursor']]
        payload = {'session_id': session['id'], 'run_number': session['run_number'], 'turn_id': turn['id'],
            'response_id': response_id or str(uuid4()), 'mode': mode, 'used_help': used_help, 'user_text': text}
        response = self.client.post('/api/dialogues/turn/check', headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json(), payload

    def test_resume_duplicate_submit_and_script_snapshot(self):
        saved = self.start()
        self.assertNotIn('required_keywords', saved['dialogue']['turns'][1])
        first, payload = self.answer(saved)
        replay = self.client.post('/api/dialogues/turn/check', headers=self.headers, json=payload).json()
        self.assertEqual(first['session']['cursor'], replay['session']['cursor'])
        self.assertEqual(self.db.query(DialogueResponse).count(), 1)
        resumed = self.start()
        self.assertEqual(resumed['session']['cursor'], 3)
        self.assertEqual(resumed['session']['responses'][0]['text'], 'I am tired.')
        # Un seed puede recrear turnos: la sesión en curso conserva su guion.
        self.db.query(DialogueTurn).filter_by(dialogue_id=self.dialogue.id).delete(synchronize_session=False)
        self.db.commit()
        result, _ = self.answer(resumed)
        self.assertTrue(result['session']['completed'])

    def test_scaffolding_after_two_clean_runs_per_stage_and_manual_override(self):
        for mode, expected in [('choose','choose'), ('choose','order'), ('order','order'), ('order','type')]:
            saved = self.start()
            while not saved['session']['completed']:
                result, _ = self.answer(saved, mode=mode)
                saved['session'] = result['session']
            self.assertEqual(saved['session']['recommended_mode'], expected)
        # Volver voluntariamente a Choose no bloquea ni sube dominio independiente.
        saved = self.start()
        result, _ = self.answer(saved, mode='choose')
        self.assertTrue(result['passed'])
        self.assertEqual(result['session']['recommended_mode'], 'type')

    def test_continue_is_saved_without_mastery_and_resume_keeps_errors(self):
        saved = self.start()
        result, _ = self.answer(saved, 'no sé qué decir', mode='type')
        self.assertFalse(result['passed']); self.assertTrue(result['can_continue'])
        resumed = self.start()
        self.assertEqual(len(resumed['session']['responses']), 1)
        path = f"/api/dialogues/session/{saved['session']['id']}/continue"
        continued = self.client.post(path, headers=self.headers, json={'response_id': result['response_id']}).json()
        again = self.client.post(path, headers=self.headers, json={'response_id': result['response_id']}).json()
        self.assertEqual(continued['cursor'], again['cursor'])
        saved['session'] = continued
        final, _ = self.answer(saved)
        self.assertEqual(final['session']['completed_runs'], 1)
        self.assertEqual(final['session']['stage_successes'], 0)

    def test_other_user_cannot_read_or_continue_session(self):
        saved = self.start()
        other = User(email='other@example.com', username='other', password_hash='unused')
        self.db.add(other); self.db.commit()
        headers = {'Authorization': 'Bearer ' + security.create_access_token(other.id)}
        result = self.client.post('/api/dialogues/turn/check', headers=headers, json={
            'session_id': saved['session']['id'], 'response_id': str(uuid4()), 'turn_id': self.turns[0].id, 'user_text': 'I am tired.'})
        self.assertEqual(result.status_code, 404)

    def test_listening_answer_hidden_until_check_and_first_answer_is_final(self):
        result = self.client.post('/api/listening/next', headers=self.headers, json={'slug':'a1-meeting'})
        exercise = result.json()
        self.assertNotIn('correct', exercise); self.assertNotIn('audio_en', exercise)
        path = f"/api/listening/{exercise['id']}"
        self.assertEqual(self.client.post(path+'/check', headers=self.headers, json={'choice':0}).status_code, 409)
        with patch.object(tts, 'synthesize', new_callable=AsyncMock, return_value=(b'RIFF','audio/wav')):
            self.assertEqual(self.client.get(path+'/audio', headers=self.headers).status_code, 200)
        first = self.client.post(path+'/check', headers=self.headers, json={'choice':1}).json()
        retry = self.client.post(path+'/check', headers=self.headers, json={'choice':0}).json()
        self.assertEqual(first, retry); self.assertEqual(first['score'], 0)
        self.assertIn('explanation_en', first)

    def test_revealed_listening_is_guided_and_bank_has_all_three_levels(self):
        self.assertEqual({e['level'] for e in EXERCISES}, {'A1','A2','B1'})
        for e in EXERCISES:
            self.assertEqual(len(e['options']), 3)
            self.assertIn(e['correct'], range(3))
            self.assertTrue(all(o['en'] and o['es'] for o in e['options']))
        exercise = self.client.post('/api/listening/next', headers=self.headers, json={'slug':'a1-meeting'}).json()
        path = f"/api/listening/{exercise['id']}"
        self.client.post(path+'/reveal', headers=self.headers)
        result = self.client.post(path+'/check', headers=self.headers, json={'choice':0}).json()
        self.assertTrue(result['assisted']); self.assertEqual(result['score'], 1)

    def test_error_drills_deduplicate_and_schedule_once_per_day(self):
        errors = analyzer.apply_custom_rules('I tired.')
        error_drills.capture(self.db, self.user.id, errors + errors)
        self.db.commit()
        card = self.db.query(SrsCard).filter_by(card_type='ERROR_DRILL').one()
        self.assertEqual(card.payload['occurrences'], 2)
        path = f'/api/srs/drills/{card.id}'
        self.assertNotIn('back', self.client.get(path, headers=self.headers).json())
        first = self.client.post(path+'/check', headers=self.headers, json={'answer':'I tired'}).json()
        self.assertFalse(first['correct']); self.assertTrue(first['scheduled'])
        retry = self.client.post(path+'/check', headers=self.headers, json={'answer':'I am tired'}).json()
        self.assertTrue(retry['correct']); self.assertFalse(retry['scheduled'])
        self.db.refresh(card)
        self.assertEqual(card.repetitions, 0)
        self.assertEqual(card.due_date, learning_day() + timedelta(days=1))

    def test_daily_prioritizes_due_weak_new_and_stays_stable(self):
        original = self.db.query(Topic).one()
        weak = Topic(slug='weak', lesson_id=original.lesson_id, prompt_en='Weak', prompt_es='Difícil', example_en='I am tired.', order_index=1)
        fresh = Topic(slug='new', lesson_id=original.lesson_id, prompt_en='New', prompt_es='Nuevo', example_en='I am happy.', order_index=2)
        self.db.add_all([weak,fresh]); self.db.flush()
        self.db.add(SrsCard(user_id=self.user.id, topic_id=original.id, front='Review', back='Hi', due_date=learning_day()-timedelta(days=1)))
        self.db.add(Attempt(user_id=self.user.id, topic_id=weak.id, word_count=8, overall_score=.3))
        self.db.commit()
        plan = self.client.post('/api/daily/today', headers=self.headers).json()
        self.assertEqual([i['id'] for i in plan['items'][:3]], [original.id,weak.id,fresh.id])
        self.assertEqual(plan['completed'], 0)
        self.db.add(Attempt(user_id=self.user.id, topic_id=fresh.id, word_count=10, overall_score=.9))
        self.db.commit()
        refreshed = self.client.post('/api/daily/today', headers=self.headers).json()
        self.assertEqual([i['id'] for i in refreshed['items']], [i['id'] for i in plan['items']])
        self.assertEqual(refreshed['completed'], 1)
        self.assertEqual(self.db.query(DailyPlan).count(), 1)

    def test_daily_excludes_hidden_topics_and_uses_profile_goal(self):
        topic = self.db.query(Topic).one()
        self.db.add(UserProfile(user_id=self.user.id, hidden_items={'topics':[topic.slug]}, daily_goal_minutes=5))
        self.db.commit()
        plan = self.client.post('/api/daily/today', headers=self.headers).json()
        self.assertEqual(plan['minutes'], 5)
        self.assertTrue(all(item['kind'] != 'topic' for item in plan['items']))

    def test_learning_day_changes_at_six_utc(self):
        self.assertEqual(str(learning_day(datetime(2026,9,12,5,59))), '2026-09-11')
        self.assertEqual(str(learning_day(datetime(2026,9,12,6))), '2026-09-12')
        self.assertEqual(learning_day_start(learning_day(datetime(2026,9,12,5))), datetime(2026,9,11,6))

    def test_listening_adapts_only_after_independent_successes(self):
        for e in EXERCISES[:3]:
            self.db.add(ListeningAttempt(user_id=self.user.id, exercise_slug=e['slug'], score=1, revealed=True, completed_at=utcnow()))
        self.db.commit()
        self.assertEqual(self.client.post('/api/listening/next', headers=self.headers, json={}).json()['level'], 'A1')
        self.db.query(ListeningAttempt).update({'revealed': False}, synchronize_session=False)
        self.db.commit()
        self.assertEqual(self.client.post('/api/listening/next', headers=self.headers, json={}).json()['level'], 'A2')

    def test_daily_moves_to_a2_when_a1_is_mastered(self):
        topic = self.db.query(Topic).one()
        self.db.add(UserProgress(user_id=self.user.id, topic_id=topic.id, mastery_level=1))
        module = Module(slug='a2', title_en='A2', title_es='A2', description_es='A2', level='A2', order_index=1)
        lesson = Lesson(slug='a2', title_en='A2', title_es='A2', objective_es='A2', module=module)
        new_topic = Topic(slug='a2', prompt_en='Yesterday', prompt_es='Ayer', example_en='Yesterday I worked.', lesson=lesson)
        self.db.add_all([module,lesson,new_topic]); self.db.commit()
        plan = self.client.post('/api/daily/today', headers=self.headers).json()
        self.assertIn(new_topic.id, [i['id'] for i in plan['items'] if i['kind']=='topic'])

    def test_listening_and_drills_belong_to_the_current_user(self):
        exercise = self.client.post('/api/listening/next', headers=self.headers, json={}).json()
        error_drills.capture(self.db, self.user.id, analyzer.apply_custom_rules('I tired.'))
        other = User(email='other@example.com', username='other', password_hash='unused')
        self.db.add(other); self.db.commit()
        card = self.db.query(SrsCard).one()
        headers = {'Authorization': 'Bearer ' + security.create_access_token(other.id)}
        self.assertEqual(self.client.post(f"/api/listening/{exercise['id']}/reveal", headers=headers).status_code, 404)
        self.assertEqual(self.client.get(f'/api/srs/drills/{card.id}', headers=headers).status_code, 404)

    def test_help_does_not_reduce_support_stage(self):
        for _ in range(2):
            saved = self.start()
            while not saved['session']['completed']:
                result, _ = self.answer(saved, used_help=True)
                saved['session'] = result['session']
            self.assertEqual(saved['session']['recommended_mode'], 'choose')
            self.assertEqual(saved['session']['stage_successes'], 0)

    def test_personalized_offered_answer_is_accepted(self):
        self.turns[0].user_example_en = 'I am William.'
        self.turns[0].answer_options = [{'en':'I am William.', 'es':'Soy William.'}]
        self.db.add(UserProfile(user_id=self.user.id, nickname='Christopher Alexander'))
        self.db.commit()
        result, _ = self.answer(self.start(), 'I am Christopher Alexander.')
        self.assertTrue(result['passed']); self.assertEqual(result['score'], 1)

    def test_daily_review_counts_practice_without_claiming_mastery(self):
        topic = self.db.query(Topic).one()
        card = SrsCard(user_id=self.user.id, topic_id=topic.id, front='Review', back='Hello', due_date=learning_day())
        self.db.add(card); self.db.commit()
        self.client.post('/api/daily/today', headers=self.headers)
        self.db.add(Attempt(user_id=self.user.id, topic_id=topic.id, word_count=8, overall_score=.3, mastered=False))
        self.db.commit()
        plan = self.client.post('/api/daily/today', headers=self.headers).json()
        self.assertTrue(next(i for i in plan['items'] if i.get('card_id') == card.id)['done'])
        self.assertEqual(card.due_date, learning_day())


if __name__ == '__main__':
    unittest.main()
