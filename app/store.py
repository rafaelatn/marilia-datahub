"""Persistência: Supabase em produção; arquivo apenas no modo demo explícito."""
import json
import os
from pathlib import Path
import httpx
from fastapi import HTTPException
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')

def demo(): return not os.getenv('VERCEL') and os.getenv('DATAHUB_MODE','supabase')=='demo'

def database_url():
    return os.getenv('SUPABASE_DATABASE_URL','').strip()

def service_key():
    return os.getenv('SUPABASE_SECRET_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY')

def auth_api_key():
    return os.getenv('SUPABASE_PUBLISHABLE_KEY') or service_key()

def remote(method, path, **kwargs):
    url=os.getenv('SUPABASE_URL','').rstrip('/')
    key=service_key()
    if not url or not key: raise HTTPException(503,'Configure SUPABASE_URL e a chave de servidor no .env, ou execute o modo demo.')
    headers={'apikey':key}
    if not key.startswith('sb_secret_'):
        headers['Authorization']='Bearer '+key
    try:
        response=httpx.request(method,url+'/rest/v1/'+path,headers=headers,timeout=30,**kwargs)
        response.raise_for_status()
        return response.json() if response.content else None
    except httpx.HTTPError as exc:
        raise HTTPException(503,'Falha de comunicação com Supabase; verifique configuração e migração.') from exc

def read():
    if demo():
        path=ROOT/'data/state.json'
        if not path.exists(): raise HTTPException(503,'Carga local ausente. Use o Supabase configurado ou forneça a carga privada de demonstração.')
        return json.loads(path.read_text(encoding='utf-8'))
    if dsn:=database_url():
        from app import postgres
        document=postgres.read_state(dsn)
    else:
        result=remote('GET','datahub_state',params={'id':'eq.1','select':'document'})
        document=result[0]['document'] if result else None
    if not document: raise HTTPException(503,'Execute o SQL de carga do Marília DataHub no Supabase.')
    return document

def read_reference(reference_id,dataset_id):
    if dsn:=database_url():
        from app import postgres
        return postgres.read_reference(dsn,reference_id,dataset_id)
    rows=remote('GET','datahub_accuracy_reference',params={
        'reference_id':f'eq.{reference_id}','dataset_id':f'eq.{dataset_id}','select':'records',
    })
    return rows[0]['records'] if rows else None

def write(state, expected):
    if state.get('current_only'):
        for d in state['datasets']:
            latest=d['versions'][-1]
            d['versions']=[latest]
            if d.get('published_version') not in (None,latest['number']):
                d['published_version']=None
                d.pop('publication',None)
                d.pop('published_at',None)
    state['revision']=expected+1
    if demo():
        path=ROOT/'data/state.json';path.parent.mkdir(exist_ok=True)
        if path.exists() and json.loads(path.read_text(encoding='utf-8'))['revision']!=expected:
            raise HTTPException(409,'Estado alterado; atualize e tente novamente.')
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(state,ensure_ascii=False,allow_nan=False),encoding='utf-8');tmp.replace(path)
    else:
        if dsn:=database_url():
            from app import postgres
            ok=postgres.save_state(dsn,state,expected)
        else:
            ok=remote('POST','rpc/datahub_save',json={'payload':state,'expected_revision':expected})
        if not ok: raise HTTPException(409,'Estado alterado; atualize e tente novamente.')
