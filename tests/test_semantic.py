from io import BytesIO
import unittest
from unittest.mock import patch

import numpy as np
from fastapi import UploadFile

from app.main import Decision, decide, import_file, state_view
from app.schema import SCHEMAS
from app.semantic import enrich_issues


class SemanticTests(unittest.TestCase):
    def test_semantic_suggestion_requires_approval_and_preserves_metric(self):
        dataset_id = 'SME_matriculas_escolas'
        schema = SCHEMAS[dataset_id]
        dataset = {'id': dataset_id, 'sec': 'educacao', 'dictionary': schema['colunas'],
                   'classification': 'publico', 'personal': False,
                   'versions': [{'number': 1, 'rows': [], 'treated': False}]}
        state = {'revision': 0, 'datasets': [dataset], 'suggestions': [],
                 'secretarias': [{'id': 'educacao'}], 'grants': []}
        actor = {'id': 'edu', 'name': 'Teste', 'role': 'educacao'}
        source = ('ano_letivo,escola,bairro,etapa,qtd_matriculas,qtd_turmas\n'
                  '2026,Escola Exemplo Centro,Centro,Primeira infância,18,\n').encode()

        def fake_encode(texts):
            units = {'Primeira infância': (1, 0), 'Educação Infantil': (1, 0),
                     'Fundamental I': (0, 1), 'Fundamental II': (0, 1)}
            return np.asarray([units[text] for text in texts])

        with patch('app.main.store.read', return_value=state), patch('app.main.store.write'), \
                patch('app.semantic.encode', side_effect=fake_encode):
            imported = import_file(UploadFile(BytesIO(source), filename='dados.csv'), 'educacao', '', actor)
            self.assertEqual(imported['semantic_review']['sugestoes'], 1)
            self.assertEqual(imported['score'], 83.33)
            self.assertEqual(dataset['versions'][-1]['rows'][0]['etapa'], 'Primeira infância')
            suggestion = state_view(actor)['suggestions'][0]
            self.assertEqual(suggestion['method'], 'Sentence Transformers MiniLM')
            self.assertEqual(suggestion['similarity'], 100)
            decide(suggestion['id'], Decision(decision='approved'), actor)
            latest = dataset['versions'][-1]
            self.assertEqual(latest['rows'][0]['etapa'], 'Educação Infantil')
            self.assertEqual(latest['quality']['score'], 100)
            self.assertEqual(latest['initial_diagnosis']['score'], 83.33)

    def test_abstains_on_tie_and_reports_model_failure(self):
        schema = SCHEMAS['SME_matriculas_escolas']
        issues = [{'column': 'etapa', 'before': 'etapa incerta', 'after': None}]
        with patch('app.semantic.encode', return_value=np.ones((4, 1))):
            self.assertEqual(enrich_issues(issues, schema)['sugestoes'], 0)
        with patch('app.semantic.encode', side_effect=OSError):
            self.assertEqual(enrich_issues(issues, schema)['status'], 'indisponivel')
        self.assertIsNone(issues[0]['after'])
