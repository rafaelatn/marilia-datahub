"""Load dataset rules and match spreadsheet headers to schema columns."""
import json
import re
from pathlib import Path

from rapidfuzz import fuzz

from app.quality import norm

SCHEMAS = json.loads(Path(__file__).with_name('schemas.json').read_text(encoding='utf-8'))
HEADER_THRESHOLD = 90
HEADER_MARGIN = 5


def dataset_schema(dataset, version=None):
    if version and 'structural_schema' in version:
        return version['structural_schema']
    return SCHEMAS.get(dataset['id'], {
        'versao': 1,
        'colunas': dataset['dictionary'],
        'chave': dataset.get('chave', []),
    })


def normalized_header(value):
    return re.sub(r'[\W_]+', ' ', norm(value)).strip()


def match_headers(headers, schema):
    """Reserve exact names and aliases before considering unambiguous fuzzy matches."""
    names = {
        col['nome_coluna']: [normalized_header(name) for name in
                            [col['nome_coluna'], *col.get('aliases', [])]]
        for col in schema['colunas']
    }
    mapping = {}
    pending = []
    for header in headers:
        normalized = normalized_header(header)
        exact = [name for name, labels in names.items() if normalized in labels]
        if header in names:
            exact = [header]
        if len(exact) > 1 or (exact and exact[0] in mapping.values()):
            return None
        if exact:
            mapping[header] = exact[0]
        else:
            pending.append(header)
    for header in pending:
        normalized = normalized_header(header)
        ranked = sorted(
            ((max(fuzz.ratio(normalized, label) for label in labels), name)
             for name, labels in names.items()), reverse=True,
        )
        if not ranked or ranked[0][0] < HEADER_THRESHOLD:
            return None
        score, name = ranked[0]
        if name in mapping.values() or (len(ranked) > 1 and score - ranked[1][0] < HEADER_MARGIN):
            return None
        mapping[header] = name
    return mapping or None


def project_rows(rows, mapping, schema):
    columns = [col['nome_coluna'] for col in schema['colunas']]
    projected = []
    for row in rows:
        values = {name: row[header] for header, name in mapping.items()}
        projected.append({column: values.get(column) for column in columns})
    return projected
