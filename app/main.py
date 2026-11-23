import csv
import hashlib
import io
import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from string import Template
from typing import Literal
import httpx
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel
from app import store
from app.quality import evaluate, suggestion_similarity
from app.processing import states, summary, published_projection, publication_check, department_quality, dataset_quality, PUBLICATION_MIN_SCORE
from app.imports import records

app=FastAPI(title='Marília DataHub',version='1.0.0')
WEB=store.ROOT/'app/web'
app.mount('/assets',StaticFiles(directory=WEB/'assets'),name='assets')
LOCK=threading.RLock()
DEPARTMENT_ROLES=('saude','educacao','assistencia','ti')
def now(): return datetime.now(timezone.utc).isoformat()

def user(request: Request):
    if store.demo():
        role=request.headers.get('X-Demo-Role','admin')
        if role not in ('admin',*DEPARTMENT_ROLES): raise HTTPException(403,'Perfil inválido')
        return {'role':role,'name':'Demonstração local','id':'demo'}
    token=request.cookies.get('datahub_token') or request.headers.get('Authorization','').removeprefix('Bearer ')
    if not token: raise HTTPException(401,'Faça login em /login')
    try:
        response=httpx.get(os.environ['SUPABASE_URL'].rstrip('/')+'/auth/v1/user',headers={'apikey':store.auth_api_key() or '', 'Authorization':'Bearer '+token},timeout=15)
        if response.status_code!=200: raise HTTPException(401,'Sessão inválida ou expirada')
        data=response.json();meta=data.get('app_metadata',{});role=meta.get('datahub_role')
        if role not in ('admin',*DEPARTMENT_ROLES): raise HTTPException(403,'Usuário sem perfil DataHub')
        preview=request.headers.get('X-DataHub-Preview')
        if preview is not None:
            if role!='admin': raise HTTPException(403,'Somente administradores podem trocar a visualização')
            if preview not in DEPARTMENT_ROLES: raise HTTPException(400,'Secretaria inválida')
            if request.method not in ('GET','HEAD','OPTIONS'):
                raise HTTPException(403,'A visualização de secretaria é somente leitura')
        return {'role':preview or role,'name':data.get('email','Usuário'),'id':data['id'],
                'can_preview':role=='admin','preview':preview is not None}
    except (KeyError,httpx.HTTPError) as exc: raise HTTPException(503,'Autenticação indisponível') from exc

def own(u,d): return u['role']=='admin' or u['role']==d['sec']
def accessible(u,d,state):
    return own(u,d) or (d['classification']!='sigiloso' and any(g['f']==d['sec'] and g['t']==u['role'] for g in state['grants']))
def find(state,id):
    d=next((d for d in state['datasets'] if d['id']==id),None)
    if d is None: raise HTTPException(404,'Dataset não encontrado')
    return d
def writable(u,d):
    if not own(u,d): raise HTTPException(403,'Sem permissão de escrita')
def version(d,rows,author,treated=False,changes=None,row_states=None,accuracy_reference=None):
    previous=d['versions'][-1]
    reference=previous.get('accuracy_reference',True) if accuracy_reference is None else accuracy_reference
    result={'number':previous['number']+1,'rows':rows,'accuracy_reference':reference,'treated':treated,'changes':changes or [],'author':author,'created_at':now(),'hash':hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
    result['quality']=dataset_quality(d,rows,result)
    if row_states is not None: result['row_states']=row_states
    return result

@app.get('/',include_in_schema=False)
def index(request:Request):
    if not store.demo() and not request.cookies.get('datahub_token'): return RedirectResponse('/login',303)
    return FileResponse(WEB/'templates/dashboard.html')

@app.get('/health')
def health(): return {'status':'ok','mode':'demo' if store.demo() else 'supabase'}

def render_login(error='',email='',status=200):
    html=(WEB/'templates/login.html').read_text(encoding='utf-8')
    page=Template(html).substitute(LOGIN_ERROR=escape(error),LOGIN_EMAIL=escape(email,quote=True))
    return HTMLResponse(page,status_code=status,headers={'Cache-Control':'no-store'})

@app.get('/login',response_class=HTMLResponse,include_in_schema=False)
def login_page():
    return render_login()

@app.post('/login',include_in_schema=False)
def login(email:str=Form(),password:str=Form()):
    try:
        r=httpx.post(os.environ['SUPABASE_URL'].rstrip('/')+'/auth/v1/token?grant_type=password',headers={'apikey':store.auth_api_key() or ''},json={'email':email,'password':password},timeout=15)
        if r.status_code>=500: return render_login('Autenticação indisponível. Tente novamente em instantes.',email,503)
        if r.status_code==429: return render_login('Muitas tentativas. Aguarde um momento e tente novamente.',email,429)
        if r.status_code!=200: return render_login('E-mail ou senha inválidos.',email,401)
        result=RedirectResponse('/',303)
        session=r.json()
        result.set_cookie('datahub_token',session['access_token'],httponly=True,secure=os.getenv('COOKIE_SECURE','true').lower()=='true',samesite='strict',max_age=session.get('expires_in',3600))
        return result
    except (KeyError,ValueError,httpx.HTTPError):
        return render_login('Autenticação indisponível. Tente novamente em instantes.',email,503)

@app.post('/logout')
def logout():
    r=RedirectResponse('/login',303);r.delete_cookie('datahub_token');return r

@app.middleware('http')
async def origin_check(request,call_next):
    if request.method in ('POST','DELETE','PUT','PATCH') and request.headers.get('origin'):
        from urllib.parse import urlsplit
        if urlsplit(request.headers['origin']).netloc!=request.headers.get('host'): return Response('Origem não permitida',403)
    return await call_next(request)

@app.get('/api/state')
def state_view(u=Depends(user)):
    state=store.read(); ds=[]
    for d in state['datasets']:
        if accessible(u,d,state):
            copy=deepcopy(d)
            for v in copy['versions']:
                if not own(u,d): v['changes']=[]
                v['quality']=dataset_quality(copy,v['rows'],v)
                if not own(u,d): v['quality']['issues']=[]
                v['processing']=summary(copy,v)
                if not own(u,d):
                    v['processing']['processed_quality']['issues']=[]
                    v['processing']['raw_quality']['issues']=[]
            latest=copy['versions'][-1]
            copy['publication_check']=publication_check(copy,latest,latest['processing']['processed_quality'])
            copy['can_publish']=own(u,d) and not u.get('preview',False)
            ds.append(copy)
    suggestions=[dict(s,similarity=suggestion_similarity(s)) for s in state['suggestions'] if u['role']=='admin' or s['sec']==u['role']]
    # A concessão de leitura pode incluir só parte das bases de outra secretaria.
    # Exibir a média oficial apenas para quem pode consultar todas as bases dela.
    departments=[
        dict(s,quality=department_quality(ds,s['id']) if u['role'] in ('admin',s['id']) else None)
        for s in state['secretarias']
    ]
    grants=state['grants'] if u['role']=='admin' else [g for g in state['grants'] if g['t']==u['role']]
    return {'mode':'demo' if store.demo() else 'supabase','publication_min_score':PUBLICATION_MIN_SCORE,'user':u,'secretarias':departments,'datasets':ds,'suggestions':suggestions,'grants':grants}

class Decision(BaseModel):
    decision:Literal['approved','rejected']

@app.post('/api/suggestions/{id}/decision')
def decide(id:int,body:Decision,u=Depends(user)):
    with LOCK:
        state=store.read();revision=state['revision'];s=next((s for s in state['suggestions'] if s['id']==id),None)
        if s is None: raise HTTPException(404,'Sugestão não encontrada')
        d=find(state,s['dataset']);writable(u,d)
        if s['status']!='pending': raise HTTPException(409,'Sugestão já decidida')
        if body.decision=='approved':
            if s['reason']=='Chave duplicada com valores diferentes':
                raise HTTPException(422,'Valores divergentes na mesma chave. Confirme a linha correta na fonte e importe a correção.')
            if s['after'] is None and s['column']!='*': raise HTTPException(422,'Sem correção confiável; confirme o valor na fonte antes de importar nova versão.')
            previous=d['versions'][-1]
            rows=deepcopy(previous['rows'])
            if s['row']>=len(rows) or (s['column']!='*' and rows[s['row']].get(s['column'])!=s['before']): raise HTTPException(409,'Sugestão desatualizada')
            status=states(d['versions'][-1])[:]
            if s['column']=='*': rows.pop(s['row']);status.pop(s['row'])
            else: rows[s['row']][s['column']]=s['after']
            if s['column']!='*' and not evaluate([rows[s['row']]],d['dictionary'])['issues']: status[s['row']]='processed'
            v=version(d,rows,u['name'],changes=[deepcopy(s)],row_states=status)
            v['initial_diagnosis']=previous.get('initial_diagnosis') or initial_diagnosis(d,previous)
            # Tratado somente após resolução de todas as pendências da base.
            v['treated']=all(x=='processed' for x in status) and not v['quality']['issues'];d['versions'].append(v)
        s['status']=body.decision;s['decided_by']=u['id'];s['decided_at']=now()
        store.write(state,revision)
    return {'status':body.decision}

def initial_diagnosis(d,v):
    quality=dataset_quality(d,v['rows'],v)
    return {'version':v['number'],'score':quality['score'],'records':len(v['rows']),
            'created_at':v['created_at'],'measured_dimensions':quality['measured_dimensions']}

@app.post('/api/import')
def import_file(file:UploadFile=File(),sec:str=Form(),sheet:str=Form(''),u=Depends(user)):
    content=file.file.read(10*1024*1024+1)
    if len(content)>10*1024*1024: raise HTTPException(413,'Limite de 10 MB')
    try:
        suffix=Path(file.filename or '').suffix.lower()
        if suffix=='.csv':
            try: text=content.decode('utf-8-sig')
            except UnicodeDecodeError: text=content.decode('cp1252')
            frame=pd.read_csv(io.StringIO(text),sep=None,engine='python')
        elif suffix=='.xlsx':
            import zipfile
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if sum(i.file_size for i in z.infolist())>50*1024*1024: raise HTTPException(413,'Planilha descompactada excede 50 MB')
            frame=pd.read_excel(io.BytesIO(content),sheet_name=sheet or 0)
        else: raise HTTPException(422,'Utilize CSV ou XLSX')
        if frame.empty or len(frame)>100000: raise HTTPException(422,'Quantidade de linhas inválida')
        rows=records(frame)
    except HTTPException: raise
    except Exception as exc: raise HTTPException(422,'Não foi possível ler a planilha ou a aba selecionada') from exc
    with LOCK:
        state=store.read();revision=state['revision']
        candidates=[d for d in state['datasets'] if d['sec']==sec and set(frame.columns)=={c['nome_coluna'] for c in d['dictionary']}]
        if len(candidates)!=1: raise HTTPException(422,'Colunas devem corresponder a um dataset da secretaria selecionada')
        d=candidates[0];writable(u,d);v=version(d,rows,u['name'],accuracy_reference=False)
        v['row_states']=['raw']*len(rows)
        v['initial_diagnosis']=initial_diagnosis(d,v)
        d['versions'].append(v)
        for s in state['suggestions']:
            if s['dataset']==d['id'] and s['status']=='pending': s['status']='superseded'
        for issue in v['quality']['issues']:
            state['suggestions'].append({'id':max([s['id'] for s in state['suggestions']],default=0)+1,'dataset':d['id'],'sec':sec,**issue,'status':'pending','method':'Regras do notebook'})
        store.write(state,revision)
    return {'dataset':d['id'],'version':v['number'],'score':v['quality']['score']}

@app.post('/api/datasets/{id}/revalidate')
def revalidate(id:str,u=Depends(user)):
    with LOCK:
        state=store.read();d=find(state,id);writable(u,d)
        current=d['versions'][-1]
        rows=current['rows']
        quality=dataset_quality(d,rows,current)
        flagged={issue['row'] for issue in quality['issues']}
        flagged.update(s['row'] for s in state['suggestions'] if s['dataset']==id and s['status']=='pending')
        before=states(current)
        after=['processed' if i not in flagged else status for i,status in enumerate(before)]
        if after==before: return {'score':quality['score'],'validated':0}
        v=version(d,rows,u['name'],treated=not flagged,row_states=after)
        v['initial_diagnosis']=current.get('initial_diagnosis') or initial_diagnosis(d,current)
        d['versions'].append(v)
        store.write(state,state['revision'])
    return {'score':quality['score'],'validated':after.count('processed')-before.count('processed')}

class Grant(BaseModel):
    f:str
    t:str

@app.post('/api/grants')
def grant(body:Grant,u=Depends(user)):
    if u['role']!='admin': raise HTTPException(403,'Somente administrador')
    with LOCK:
        state=store.read();revision=state['revision'];ids={s['id'] for s in state['secretarias']}
        if body.f not in ids or body.t not in ids or body.f==body.t: raise HTTPException(422,'Secretarias inválidas')
        if any(g['f']==body.f and g['t']==body.t for g in state['grants']): raise HTTPException(409,'Concessão já existe')
        state['grants'].append({'id':os.urandom(8).hex(),**body.model_dump(),'by':u['name'],'until':'Sem prazo','created_at':now()});store.write(state,revision)
    return {'ok':True}

@app.delete('/api/grants/{id}')
def revoke(id:str,u=Depends(user)):
    if u['role']!='admin': raise HTTPException(403,'Somente administrador')
    with LOCK:
        state=store.read();revision=state['revision'];state['grants']=[g for g in state['grants'] if g['id']!=id];store.write(state,revision)
    return {'ok':True}

@app.post('/api/datasets/{id}/publish')
def publish(id:str,u=Depends(user)):
    with LOCK:
        state=store.read();revision=state['revision'];d=find(state,id);writable(u,d);v=d['versions'][-1]
        check=publication_check(d,v)
        if not check['eligible']: raise HTTPException(422,'Publicação bloqueada: '+ '; '.join(check['reasons']))
        d['published_version']=v['number'];d['publication']={'version':v['number'],'indices':check['indices'],'score':check['score']};d['published_at']=now();store.write(state,revision)
    return {'url':'/public/'+id}

@app.get('/api/datasets/{id}/versions/{number}')
def dataset_version(id:str,number:int,u=Depends(user)):
    state=store.read();d=find(state,id)
    if not accessible(u,d,state): raise HTTPException(403,'Sem acesso')
    v=next((v for v in d['versions'] if v['number']==number),None)
    if v is None: raise HTTPException(404,'Versão não encontrada')
    result=deepcopy(v)
    result['quality']=dataset_quality(d,v['rows'],v)
    if not own(u,d):
        result['changes']=[]
        result['quality']['issues']=[]
    return result

def public_dataset(id):
    d=find(store.read(),id)
    if d['classification']!='publico' or d['personal'] or d['published_version'] is None: raise HTTPException(404,'Dataset não publicado')
    v=next((v for v in d['versions'] if v['number']==d['published_version']),None)
    if v is None: raise HTTPException(404,'Publicação indisponível')
    result=published_projection(d,v)
    if not publication_check(d,result)['eligible']: raise HTTPException(404,'Publicação não atende à política atual')
    return d,result

@app.get('/public/{id}/download')
def download(id:str,format:Literal['csv','json']='csv'):
    d,v=public_dataset(id)
    if format=='json': return Response(json.dumps(v['rows'],ensure_ascii=False),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="{id}.json"'})
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=[c['nome_coluna'] for c in d['dictionary']]);writer.writeheader();writer.writerows(v['rows'])
    return Response('\ufeff'+out.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{id}.csv"'})

@app.get('/public/{id}',response_class=HTMLResponse)
def public_page(id:str):
    from app.portal import render
    d,v=public_dataset(id)
    return render(d,v,store.read()['secretarias'])
