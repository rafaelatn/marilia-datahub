"""Expected values from the two synthetic fixtures used in the demo."""
from functools import lru_cache
import json
from pathlib import Path

from app import store
from app.quality import canonical, norm


def identity(row, keys):
    return tuple(norm(canonical(column, row.get(column))) for column in keys)


@lru_cache(maxsize=16)
def reference_index(source, dataset, keys):
    if isinstance(source,Path):
        reference = json.loads(source.read_text(encoding='utf-8'))
        entries = reference['datasets'][dataset]
    else:
        _,reference_id=source
        entries=store.read_reference(reference_id,dataset)
        if entries is None:
            from fastapi import HTTPException
            raise HTTPException(503,'A referência sintética vinculada à carga está ausente no Supabase.')
    index = {}
    for entry in entries:
        for key in {identity(entry['expected'],keys),tuple(entry['original_key'])}:
            if key in index and index[key] != entry['expected']:
                raise ValueError(f'Chave ambígua na referência sintética de {dataset}')
            index[key] = entry['expected']
    return index, len(entries)


def accuracy(source, dataset, keys, rows, dictionary):
    index, reference_records = reference_index(source, dataset, tuple(keys))
    fields = [
        column['nome_coluna'] for column in dictionary
        if column['tipo_dado'] in ('inteiro','decimal') and column['nome_coluna'] not in keys
    ]
    matched = checked = failures = 0
    for row in rows:
        expected = index.get(identity(row, keys))
        if expected is None:
            continue
        matched += 1
        for field in fields:
            if expected.get(field) is not None:
                checked += 1
                failures += row.get(field) != expected[field]
    return {
        'score':round(100*(checked-failures)/checked,2) if checked else None,
        'checked':checked,'failures':failures,'matched_records':matched,
        'total_records':len(rows),'reference_records':reference_records,
        'reference':'Referência sintética de demonstração',
    }
