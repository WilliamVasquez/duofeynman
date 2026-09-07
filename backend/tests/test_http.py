"""Contratos HTTP reales con BD en memoria; no contactan MySQL ni servicios de voz."""
import unittest
from datetime import timedelta
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import get_db
from app.models import User, Module, Lesson, Topic
from app.models.dictation import DictationExercise
from app.services import security, stt, tts
from app.timeutils import utcnow


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        self.engine_patch = patch.object(main, 'engine', self.engine)
        self.engine_patch.start()
        self.client = TestClient(main.app)
        self.client.__enter__()  # Incluye la creación de tablas del arranque real.
        self.db = sessionmaker(bind=self.engine, autoflush=False)()
        self.user = User(email='http@example.com', username='http', password_hash='unused')
        module = Module(slug='http', title_en='Test', title_es='Prueba', description_es='Prueba')
        lesson = Lesson(slug='http', title_en='Test', title_es='Prueba', objective_es='Prueba', module=module)
        topic = Topic(slug='http', prompt_en='Introduce yourself', prompt_es='Presentate', example_en='Hello, my name is Alex.', lesson=lesson)
        self.db.add_all([self.user, module, lesson, topic])
        self.db.commit()
        main.app.dependency_overrides[get_db] = lambda: self.db
        self.headers = {'Authorization': 'Bearer ' + security.create_access_token(self.user.id)}

    def tearDown(self):
        main.app.dependency_overrides.clear()
        self.client.__exit__(None, None, None)
        self.db.close()
        self.engine_patch.stop()
        self.engine.dispose()

    def test_authentication_and_password_compatibility(self):
        self.assertEqual(self.client.get('/api/me').status_code, 401)
        self.assertEqual(self.client.get('/api/me', headers=self.headers).json()['id'], self.user.id)
        hashed = security.hash_password('Test-password-123')
        self.assertTrue(security.verify_password('Test-password-123', hashed))
        self.assertFalse(security.verify_password('wrong', hashed))
        token = security.create_access_token(self.user.id)
        self.assertEqual(security.decode_token(token), str(self.user.id))
        self.assertIsNone(security.decode_token('invalid.' + token))

    def test_multipart_transcription_contract_and_size_limit(self):
        with patch.object(stt, 'transcribe', return_value=('Thank you.', 'whisper')) as transcribe:
            result = self.client.post('/api/attempts/transcribe', headers=self.headers,
                files={'file': ('speech.wav', b'RIFF-test', 'audio/wav')}, data={'hints': 'hello|thanks'})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json(), {'transcript': 'Thank you.', 'engine': 'whisper'})
            transcribe.assert_called_once_with(b'RIFF-test', ['hello', 'thanks'])
            oversized = self.client.post('/api/attempts/transcribe', headers=self.headers,
                files={'file': ('large.wav', b'x' * (10 * 1024 * 1024 + 1), 'audio/wav')})
            self.assertEqual(oversized.status_code, 413)
            transcribe.assert_called_once()

    def test_dictation_audio_rewards_and_expiry(self):
        result = self.client.post('/api/dictation/next', headers=self.headers)
        self.assertEqual(result.status_code, 200, result.text)
        exercise_id = result.json()['dictation_id']
        self.assertNotIn('target', result.json())
        exercise = self.db.get(DictationExercise, exercise_id)
        with patch.object(tts, 'synthesize', new_callable=AsyncMock, return_value=(b'RIFF', 'audio/wav')) as synth:
            audio = self.client.get(f'/api/dictation/{exercise_id}/audio?slow=true', headers=self.headers)
            self.assertEqual(audio.status_code, 200, audio.text)
            self.assertEqual(audio.content, b'RIFF')
            self.assertIn('no-store', audio.headers['cache-control'])
            synth.assert_awaited_once_with(exercise.target, level=self.user.current_level, rate='-40%')
        payload = {'dictation_id': exercise_id, 'user_input': exercise.target}
        self.assertEqual(self.client.post('/api/dictation/check', headers=self.headers, json=payload).json()['xp_awarded'], 3)
        self.assertEqual(self.client.post('/api/dictation/check', headers=self.headers, json=payload).json()['xp_awarded'], 0)
        self.assertEqual(self.client.post('/api/dictation/check', headers=self.headers, json={**payload, 'target_sentence': 'fake'}).status_code, 422)
        exercise.created_at = utcnow() - timedelta(days=2)
        self.db.commit()
        self.assertEqual(self.client.post('/api/dictation/check', headers=self.headers, json=payload).status_code, 410)


if __name__ == '__main__':
    unittest.main()
