from copy import deepcopy
from app.quality import evaluate
from app.schema import dataset_schema

PUBLICATION_MIN_SCORE=95

def department_quality(datasets, department):
    scores=[
        (d['id'], d['versions'][-1]['quality']['score'])
        for d in datasets
        if d['sec']==department and d['versions'][-1]['rows']
    ]
    return {
        'mean':round(sum(score for _,score in scores)/len(scores),2) if scores else None,
        'datasets':dict(scores),
    }

def dataset_quality(d, rows, version=None):
    schema=dataset_schema(d,version)
    result=evaluate(rows,schema['colunas'],schema['chave'])
    result['schema_version']=schema['versao']
    return result


def baseline(d,v,rows=None):
    rows=v['rows'] if rows is None else rows
    quality=dataset_quality(d,rows,v)
    return {'version':v['number'], 'records':len(rows), 'created_at':v['created_at'],
            'schema_version':quality['schema_version'], 'score':quality['dimensions']['conformity']['score'],
            'fields':quality['dimensions']['conformity'], 'record_conformity':quality['record_conformity']}


def stored_baseline(d,v):
    initial=v.get('initial_diagnosis')
    schema=dataset_schema(d,v)
    if initial and initial.get('schema_version')==schema['versao'] and 'fields' in initial:
        return initial
    return None


def publication_check(d,v,quality=None):
    indices=[i for i,s in enumerate(states(v)) if s=='processed']
    rows=[v['rows'][i] for i in indices]
    if quality is None: quality=dataset_quality(d,rows,v)
    dimensions=quality['dimensions']
    missing=dimensions['completeness']['failures']
    duplicates=dimensions['consistency']['failures']
    invalid=dimensions['conformity']['failures']-missing
    reasons=[]
    if not rows: reasons.append('Nenhum registro processado')
    if quality['score']<PUBLICATION_MIN_SCORE: reasons.append(f'Conformidade estrutural inferior a {PUBLICATION_MIN_SCORE}/100')
    if missing: reasons.append(f'Campo obrigatório vazio ({missing})')
    if duplicates: reasons.append(f'Duplicata na chave de identificação ({duplicates})')
    if invalid: reasons.append(f'Campo fora do esquema ({invalid})')
    if d['classification']!='publico': reasons.append('Classificação não pública')
    if d['personal']: reasons.append('Contém dados pessoais')
    return {'eligible':not reasons,'min_score':PUBLICATION_MIN_SCORE,'score':quality['score'],
            'processed_count':len(rows),'mandatory_missing':missing,'duplicate_keys':duplicates,
            'invalid_values':invalid,'reasons':reasons,'indices':indices}

def states(v):
    result=v.get('row_states')
    if result is not None:
        if len(result)!=len(v['rows']): raise ValueError('Estados de processamento incompatíveis com as linhas')
        return result
    return ['processed' if v['treated'] else 'raw']*len(v['rows'])

def summary(d,v):
    status=states(v)
    processed=[r for r,s in zip(v['rows'],status) if s=='processed']
    raw=[r for r,s in zip(v['rows'],status) if s=='raw']
    return {'processed_count':len(processed),'raw_count':len(raw),
            'processed_quality':dataset_quality(d,processed,v),
            'raw_quality':dataset_quality(d,raw,v)}

def published_projection(d,v):
    result=deepcopy(v)
    indices=d.get('publication',{}).get('indices')
    if indices is not None:
        result['rows']=[v['rows'][i] for i in indices]
    result['treated']=True
    result['row_states']=['processed']*len(result['rows'])
    result['quality']=dataset_quality(d,result['rows'],result)
    result['changes']=[]
    result['processing']=summary(d,result)
    return result
