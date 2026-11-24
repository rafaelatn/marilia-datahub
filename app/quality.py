"""Validate data and propose corrections using the dataset schema."""
import json
import math
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from rapidfuzz import fuzz, process


def plain(value):
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10]
    if hasattr(value, 'item'):
        return plain(value.item())
    return value


def norm(value):
    return ''.join(
        char for char in unicodedata.normalize('NFD', str(value).strip().lower())
        if unicodedata.category(char) != 'Mn'
    )


def suggestion_similarity(issue):
    before, after = issue.get('before'), issue.get('after')
    if not all(isinstance(value, str) and value.strip() for value in (before, after)):
        return None
    return round(fuzz.ratio(before, after), 1)


def missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def number(value, rule):
    if isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite():
        return None
    if rule['tipo_dado'] == 'inteiro' and parsed != parsed.to_integral_value():
        return None
    if 'minimo' in rule and parsed < Decimal(str(rule['minimo'])):
        return None
    try:
        converted = int(parsed) if rule['tipo_dado'] == 'inteiro' else float(parsed)
        return converted if rule['tipo_dado'] == 'inteiro' or math.isfinite(converted) else None
    except (OverflowError, ValueError):
        return None


def parse_date(value, rule):
    text = str(value).strip()
    output = rule.get('formato', '%Y-%m-%d')
    parsed = None
    for fmt in (output, *rule.get('formatos_entrada', [])):
        try:
            parsed = datetime.strptime(text, fmt).date()
            break
        except ValueError:
            continue
    months = rule.get('meses_abreviados', [])
    match = re.fullmatch(r'([a-z]{3})/(\d{2}|\d{4})', norm(text))
    if parsed is None and match and match[1] in months:
        year = int(match[2])
        try:
            parsed = date(year+2000 if len(match[2]) == 2 else year, months.index(match[1])+1, 1)
        except ValueError:
            return None
    if parsed is None:
        return None
    return parsed.replace(day=rule.get('dia_do_mes', parsed.day)).strftime(output)


def cell_check(value, rule):
    kind = rule['tipo_dado']
    if kind in ('inteiro', 'decimal'):
        corrected = number(value, rule)
        if corrected is None:
            return 'Número inválido ou fora do intervalo', None
        if isinstance(value, str):
            return 'Tipo numérico fora do padrão', corrected
        return None, None
    if kind == 'data':
        corrected = parse_date(value, rule)
        return ('Data fora do padrão', corrected) if corrected is None or corrected != value else (None, None)
    if not isinstance(value, str):
        return 'Texto inválido', None
    text = value.strip()
    aliases = {norm(alias): target for alias, target in rule.get('aliases_valores', {}).items()}
    corrected = aliases.get(norm(text), text)
    allowed = rule.get('valores_permitidos')
    if allowed is not None and corrected not in allowed:
        corrected = next((label for label in allowed if norm(label) == norm(corrected)), None)
        threshold = rule.get('similaridade_minima')
        if corrected is None and threshold is not None:
            match = process.extractOne(text, allowed, scorer=fuzz.WRatio, score_cutoff=threshold)
            corrected = match[0] if match else None
    pattern = rule.get('formato')
    if corrected is None or (pattern and not re.fullmatch(pattern, corrected)):
        return 'Texto fora do formato ou domínio permitido', None
    if corrected != value:
        return 'Padronização conforme esquema do dataset', corrected
    return None, None


def dimension(checked, failures):
    valid = checked - failures
    return {'score': round(100 * valid / checked, 2) if checked else None,
            'checked': checked, 'valid': valid, 'failures': failures}


def evaluate(rows, dictionary, keys=None):
    required = {column['nome_coluna'] for column in dictionary if column['obrigatoria']}
    issues = []
    absent = checked_values = invalid = duplicates = failed_fields = failed_rows = 0
    seen_keys = {}
    for index, row in enumerate(rows):
        signature = json.dumps(row, sort_keys=True, ensure_ascii=False)
        key_values = [row.get(column) for column in keys or ()]
        key = (json.dumps(key_values, ensure_ascii=False)
               if key_values and not any(missing(value) for value in key_values) else signature)
        duplicate = key in seen_keys
        if duplicate:
            duplicates += 1
            reason = ('Registro duplicado' if signature == seen_keys[key]
                      else 'Chave duplicada com valores diferentes')
            issues.append({'row': index, 'column': '*', 'before': row, 'after': None, 'reason': reason})
        else:
            seen_keys[key] = signature
        row_failures = 0
        for rule in dictionary:
            column = rule['nome_coluna']
            value = row.get(column)
            if missing(value):
                if column in required:
                    absent += 1
                    reason = 'Valor obrigatório ausente; exige confirmação da fonte'
                elif column not in row:
                    reason = 'Coluna ausente no arquivo'
                else:
                    continue
                corrected = None
            else:
                checked_values += 1
                reason, corrected = cell_check(value, rule)
                invalid += reason is not None
            if reason:
                row_failures += 1
                issues.append({'row': index, 'column': column, 'before': value,
                               'after': corrected, 'reason': reason})
        failed_fields += row_failures
        failed_rows += bool(row_failures or duplicate)
    dimensions = {
        'completeness': dimension(len(rows) * len(required), absent),
        'conformity': dimension(len(rows) * len(dictionary), failed_fields),
        'consistency': dimension(len(rows), duplicates),
        'validity': dimension(checked_values, invalid),
    }
    return {'metrics': [metric['score'] for metric in dimensions.values()],
            'dimensions': dimensions, 'record_conformity': dimension(len(rows), failed_rows),
            'score': dimensions['conformity']['score'] or 0, 'issues': issues}
