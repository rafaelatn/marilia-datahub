"""Regras explicáveis derivadas do notebook de limpeza fornecido."""
import json
import math
import re
import unicodedata
from datetime import date, datetime
from rapidfuzz import process, fuzz

BAIRROS = ['Centro', 'Fragata', 'Palmital', 'Cascata']
ALIASES = {'ubs ex. cascata': 'UBS Exemplo Cascata', 'escola exemplo fragata 2': 'Escola Exemplo Fragata II', 'cras cascata': 'CRAS Exemplo Cascata'}
DICTIONARY_DOMAINS = {
    'tipo_atendimento': ('Consulta médica', 'Enfermagem', 'Odontológico'),
    'etapa': ('Educação Infantil', 'Fundamental I', 'Fundamental II'),
    'tipo_chamado': ('Hardware', 'Rede', 'Sistema'),
}

def plain(v):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    if isinstance(v, (datetime, date)):
        return v.isoformat()[:10]
    if hasattr(v, 'item'):
        return plain(v.item())
    return v

def norm(v):
    return ''.join(c for c in unicodedata.normalize('NFD', str(v).strip().lower()) if unicodedata.category(c) != 'Mn')

def suggestion_similarity(issue):
    """Compare text labels on the same scale, including older suggestions."""
    before, after = issue.get('before'), issue.get('after')
    if issue.get('column') not in {'bairro', 'secretaria', 'unidade', 'escola', 'cras'}:
        return None
    if not all(isinstance(value, str) and value.strip() for value in (before, after)):
        return None
    return round(fuzz.ratio(before, after), 1)

def canonical(column, value):
    if value is None:
        return None
    text = str(value).strip()
    if column == 'bairro':
        return next((b for b in BAIRROS if norm(b) == norm(text)), text)
    if column == 'secretaria':
        return {'saude':'SMS','sms':'SMS','sme':'SME','sas':'SAS','seti':'SETI'}.get(norm(text), text)
    if column in ('unidade','escola','cras'):
        return ALIASES.get(text.lower(), text)
    if column == 'data_referencia':
        months = dict(zip('jan fev mar abr mai jun jul ago set out nov dez'.split(), range(1,13)))
        match = re.fullmatch(r'([a-z]{3})/(\d{2}|\d{4})', text.lower())
        try:
            if match:
                y = int(match[2]); return date(y + 2000 if y < 100 else y, months[match[1]], 1).isoformat()
            if re.fullmatch(r'\d{4}-\d{2}(?:-\d{2})?', text):
                return date.fromisoformat(text if len(text)==10 else text+'-01').replace(day=1).isoformat()
            for fmt in ('%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
                try: return datetime.strptime(text, fmt).replace(day=1).date().isoformat()
                except ValueError: pass
        except (ValueError, KeyError):
            pass
    return text if isinstance(value, str) else value

def evaluate(rows, dictionary, keys=None):
    required = {d['nome_coluna'] for d in dictionary if d['obrigatoria']}
    missing = lambda v: v is None or (isinstance(v,str) and not v.strip())
    issues=[]
    absent=checked_values=invalid=duplicates=0
    seen_rows=set()
    seen_keys=set()
    for i,row in enumerate(rows):
        signature=json.dumps(row,sort_keys=True,ensure_ascii=False)
        exact_duplicate=signature in seen_rows
        if exact_duplicate:
            issues.append({'row':i,'column':'*','before':row,'after':None,'reason':'Registro duplicado'})
        seen_rows.add(signature)
        key=json.dumps([row.get(c) for c in keys],ensure_ascii=False) if keys else signature
        if key in seen_keys:
            duplicates+=1
            if not exact_duplicate:
                issues.append({'row':i,'column':'*','before':row,'after':None,
                               'reason':'Chave duplicada com valores diferentes'})
        seen_keys.add(key)
        for d in dictionary:
            c=d['nome_coluna']; v=row.get(c)
            if missing(v):
                absent+=c in required
                issues.append({'row':i,'column':c,'before':v,'after':None,'reason':'Valor ausente; exige confirmação da fonte'})
                continue
            checked_values+=1
            corrected=canonical(c,v); reason=None
            if corrected != v: reason='Padronização conforme notebook'
            allowed=d.get('valores_permitidos',DICTIONARY_DOMAINS.get(c))
            if allowed and v not in allowed: reason='Categoria fora do dicionário'; corrected=None
            if d['tipo_dado']=='texto' and not isinstance(v,str): reason='Texto inválido'; corrected=None
            if c=='bairro' and v not in BAIRROS: reason='Bairro fora do padrão'
            if c=='secretaria' and v not in ('SMS','SME','SAS','SETI'): reason='Sigla fora do padrão'
            refs = None
            if c=='unidade': refs=['UBS Exemplo '+b for b in BAIRROS]
            if c=='cras': refs=['CRAS Exemplo '+b for b in BAIRROS]
            if c=='escola': refs=['Escola Exemplo '+b+suffix for b in BAIRROS for suffix in ('',' II')]
            if refs and v not in refs:
                reason='Nome de unidade fora do padrão'
                match=process.extractOne(str(v),refs,scorer=fuzz.WRatio)
                corrected=match[0] if match and match[1]>=80 else None
            if d['tipo_dado'] in ('inteiro','decimal'):
                try:
                    number=float(v)
                    if not math.isfinite(number) or number < 0 or (d['tipo_dado']=='inteiro' and not number.is_integer()): reason='Número inválido'; corrected=None
                except (ValueError,TypeError): reason='Número inválido'; corrected=None
            if d['tipo_dado']=='data':
                try:
                    if not isinstance(v,str) or date.fromisoformat(v).day!=1: reason='Formato de data fora do padrão'
                except (ValueError,TypeError): reason='Formato de data fora do padrão'
            if reason:
                invalid+=1
                issues.append({'row':i,'column':c,'before':v,'after':corrected if corrected!=v else None,'reason':reason})
    def dimension(checked, failures):
        score=round(100*(checked-failures)/checked,2) if checked else None
        return {'score':score,'checked':checked,'failures':failures}
    dimensions={
        'completeness':dimension(len(rows)*len(required),absent),
        'accuracy':dimension(0,0),
        'consistency':dimension(len(rows),duplicates),
        'validity':dimension(checked_values,invalid),
    }
    metrics=[metric['score'] for metric in dimensions.values()]
    measured=[value for value in metrics if value is not None]
    return {'metrics':metrics,'dimensions':dimensions,'measured_dimensions':len(measured),
            'score':round(sum(measured)/len(measured),2) if measured else 0,'issues':issues}
