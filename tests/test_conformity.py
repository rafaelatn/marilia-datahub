
from io import BytesIO
import unittest
from unittest.mock import patch

from fastapi import UploadFile

from app.main import Decision, decide, import_file, state_view
from app.quality import evaluate
from app.schema import SCHEMAS, match_headers


class ConformityTests(unittest.TestCase):
    def test_import_and_treatment_use_same_schema(self):
        dataset_id = 'SMS_atendimentos_ubs'
        dataset = {
            'id': dataset_id, 'sec': 'saude', 'dictionary': SCHEMAS[dataset_id]['colunas'],
            'classification': 'publico', 'personal': False,
            'versions': [{'number': 1, 'rows': [], 'treated': False}],
        }
        state = {'revision': 0, 'datasets': [dataset], 'suggestions': [],
                 'secretarias': [{'id': 'saude'}], 'grants': []}
        actor = {'id': 'secretaria', 'name': 'Teste', 'role': 'saude'}
        source = ('Competência,unidade,bairro,tipo_atendiment,qtd_atendimentos\n'
                  '01/07/2026,UBS Exemplo Centro,centro,Enfermagem,12\n').encode()
        with patch('app.main.store.read', return_value=state), patch('app.main.store.write'):
            result = import_file(UploadFile(BytesIO(source), filename='teste.csv'), 'saude', '', actor)
            self.assertEqual(result['score'], 60)
            self.assertEqual(dataset['versions'][-1]['initial_diagnosis']['score'], 40)
            self.assertEqual(len(state['suggestions']), 2)
            for issue in state['suggestions']:
                result = decide(issue['id'], Decision(decision='approved'), actor)
                self.assertEqual(result['status'], 'approved')
            version = state_view(actor)['datasets'][0]['versions'][-1]
            self.assertEqual(version['initial_diagnosis']['fields']['valid'], 2)
            self.assertEqual(version['quality']['dimensions']['conformity']['valid'], 5)
            self.assertEqual(version['quality']['record_conformity']['score'], 100)
            self.assertEqual(version['initial_diagnosis']['schema_version'],
                             version['quality']['schema_version'])
            self.assertEqual(version['processing']['processed_count'], 1)

    def test_schema_constraints_and_header_collisions(self):
        columns = [
            {'nome_coluna': 'cnpj', 'aliases': ['CNPJ Fornecedor'], 'tipo_dado': 'texto',
             'formato': r'\d{14}', 'obrigatoria': True},
            {'nome_coluna': 'valor', 'tipo_dado': 'decimal', 'minimo': 0, 'obrigatoria': False},
        ]
        schema = {'colunas': columns, 'chave': ['cnpj']}
        self.assertIsNone(match_headers(['CNPJ', 'CNPJ Fornecedor'], schema))
        self.assertEqual(match_headers(['CNPJ Fornecedor', 'valor'], schema),
                         {'CNPJ Fornecedor': 'cnpj', 'valor': 'valor'})
        quality = evaluate([
            {'cnpj': '01234567890123', 'valor': None},
            {'cnpj': '01234567890123', 'valor': -1},
        ], columns, schema['chave'])
        self.assertEqual(quality['score'], 75)
        self.assertEqual(quality['record_conformity']['score'], 50)
        self.assertEqual(quality['dimensions']['consistency']['failures'], 1)
