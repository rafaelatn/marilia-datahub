"""Normalize values read from CSV and Excel for JSON storage."""
import json
import math

from app.quality import plain


def records(frame):
    return [{str(key): plain(value) for key, value in row.items()}
            for row in frame.to_dict('records')]


def decode_csv_numbers(rows, mapping, schema):
    """Read numeric CSV fields without inferring types for identifiers or text."""
    numeric = {field['nome_coluna'] for field in schema['colunas']
               if field['tipo_dado'] in ('inteiro', 'decimal')}
    headers = [header for header, column in mapping.items() if column in numeric]
    for row in rows:
        for header in headers:
            try:
                value = json.loads(row[header])
            except (ValueError, TypeError):
                continue
            if type(value) is int or (type(value) is float and math.isfinite(value)):
                row[header] = value
