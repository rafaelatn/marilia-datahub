import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.quality import evaluate


class WebTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_login_and_assets(self):
        self.assertIn('Entrar no painel', self.client.get('/login').text)
        for name in ('dashboard.css', 'dashboard-shell.js', 'dashboard-api.js'):
            self.assertEqual(self.client.get('/assets/' + name).status_code, 200)

    def test_dashboard_and_state_require_session(self):
        with patch.dict('os.environ', {'DATAHUB_MODE': 'demo', 'VERCEL': '1'}):
            self.assertEqual(self.client.get('/health').json()['mode'], 'supabase')
            self.assertEqual(self.client.get('/', follow_redirects=False).headers['location'], '/login')
            self.assertEqual(self.client.get('/api/state').status_code, 401)

    def test_dashboard_template_and_authenticated_state(self):
        state = {'datasets': [], 'secretarias': [], 'suggestions': [], 'grants': []}
        identity = {'id': 'test', 'app_metadata': {'datahub_role': 'admin'}}
        with patch.dict('os.environ', {'DATAHUB_MODE': 'supabase', 'SUPABASE_URL': 'https://example.test'}),              patch('app.main.httpx.get', return_value=httpx.Response(200, json=identity)),              patch('app.main.store.read', return_value=state):
            self.client.cookies.set('datahub_token', 'test')
            page = self.client.get('/')
            self.assertIn('/assets/dashboard-api.js', page.text)
            self.assertEqual(self.client.get('/api/state').json()['user']['role'], 'admin')

    def test_quality_reports_missing_required_value(self):
        schema = [{'nome_coluna': 'valor', 'tipo_dado': 'inteiro', 'obrigatoria': True}]
        quality = evaluate([{'valor': None}], schema)
        self.assertEqual(quality['dimensions']['completeness']['failures'], 1)


if __name__ == '__main__':
    unittest.main()
