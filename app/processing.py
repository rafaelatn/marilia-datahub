from copy import deepcopy
import os
from app import store
from app.demo_reference import accuracy
from app.quality import evaluate

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

BUSINESS_KEYS={
    'SMS_atendimentos_ubs':['data_referencia','unidade','tipo_atendimento'],
    'SMS_vacinacao':['data_referencia','unidade','vacina'],
    'SME_matriculas_escolas':['ano_letivo','escola','etapa'],
    'SAS_familias_cras':['data_referencia','cras'],
    'SAS_chamados_ti':['data_referencia','secretaria','tipo_chamado'],
}

def dataset_quality(d, rows, version=None):
    keys=BUSINESS_KEYS.get(d['id'],sorted(c['nome_coluna'] for c in d['dictionary'] if c['obrigatoria']))
    quality=evaluate(rows,d['dictionary'],keys)
    source=None
    if d['id'] in BUSINESS_KEYS and (version or {}).get('accuracy_reference',True):
        if store.demo():
            source=store.ROOT/'source/accuracy_reference_demo.json'
        elif d.get('synthetic_reference_id'):
            source=(os.getenv('SUPABASE_URL'),d['synthetic_reference_id'])
    if source is not None:
        metric=accuracy(source,d['id'],keys,rows,d['dictionary'])
        quality['dimensions']['accuracy']=metric
        quality['metrics'][1]=metric['score']
        measured=[value for value in quality['metrics'] if value is not None]
        quality['measured_dimensions']=len(measured)
        quality['score']=round(sum(measured)/len(measured),2) if measured else 0
    return quality

def publication_check(d,v,quality=None):
    indices=[i for i,s in enumerate(states(v)) if s=='processed']
    rows=[v['rows'][i] for i in indices]
    if quality is None: quality=dataset_quality(d,rows,v)
    dimensions=quality['dimensions']
    missing=dimensions['completeness']['failures']
    duplicates=dimensions['consistency']['failures']
    invalid=dimensions['validity']['failures']
    reasons=[]
    if not rows: reasons.append('Nenhum registro processado')
    if quality['score']<PUBLICATION_MIN_SCORE: reasons.append(f'Score inferior a {PUBLICATION_MIN_SCORE}/100')
    if missing: reasons.append(f'Campo obrigatório vazio ({missing})')
    if duplicates: reasons.append(f'Duplicata na chave de identificação ({duplicates})')
    if invalid: reasons.append(f'Data, valor ou categoria inválida ({invalid})')
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
