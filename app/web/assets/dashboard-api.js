// Adaptador de dados: mantém componentes, navegação, estilos e estrutura do HTML.
let DATA=null;
let recordFilter='all';
let recordSearch={column:'',query:''};
let previewDepartment=null;
const currentVersion=d=>d.versions.at(-1);
const rowStates=v=>v.row_states||v.rows.map(()=>v.treated?'processed':'raw');
const counts=v=>({processed:rowStates(v).filter(s=>s==='processed').length,raw:rowStates(v).filter(s=>s==='raw').length});
const searchText=value=>String(value??'').normalize('NFD').replace(/\p{M}/gu,'').toLocaleLowerCase('pt-BR');
function matchingRows(d,v,status,search){
  const columns=d.dictionary.map(c=>c.nome_coluna);
  if(search.column&&!columns.includes(search.column))return [];
  const selected=search.column?[search.column]:columns;
  const query=searchText(search.query);
  const states=rowStates(v);
  return v.rows.flatMap((r,i)=>{
    if(status!=='all'&&states[i]!==status)return [];
    if(query&&!selected.some(column=>searchText(r[column]).includes(query)))return [];
    return [{r,i}];
  });
}
const processingLabel=v=>counts(v).processed&&counts(v).raw?'Brutos e processados':counts(v).processed?'Processado':'Bruto / em tratamento';
function distribution(){
  const datasets=DATA.datasets;
  const total=datasets.reduce((n,d)=>n+currentVersion(d).rows.length,0);
  const processed=datasets.reduce((n,d)=>n+counts(currentVersion(d)).processed,0);
  return {total,processed,raw:total-processed,bases:datasets.length};
}
const numberBR=n=>Number(n).toLocaleString('pt-BR');
const mean=values=>values.length?Math.round(values.reduce((a,v)=>a+v,0)/values.length*100)/100:null;
const previewNotice=()=>DATA.user.preview
  ?note(`Visualização de <b>${esc(NAMES[role])}</b> · somente leitura. Selecione Administração (STI) para voltar.`):'';
function departmentTabs(){
  const options=SEC.filter(s=>s.available&&vis(s));
  if(options.length<2)return '';
  return `<div class="chips" role="group" aria-label="Secretarias disponíveis">${options.map(s=>
    `<button class="chip ${s.id===cur?'on':''}" aria-pressed="${s.id===cur}" data-a="sec" data-id="${s.id}">${esc(s.n)}${tier(s)==='grant'?' · acesso concedido':''}</button>`
  ).join('')}</div>`;
}
function qualitySeries(datasets){
  const versions=datasets.map(currentVersion);
  const groups=[
    ['Brutos',versions.filter(v=>counts(v).raw).map(v=>v.processing.raw_quality.score)],
    ['Todos os registros',versions.filter(v=>v.rows.length).map(v=>v.quality.score)],
    ['Processados',versions.filter(v=>counts(v).processed).map(v=>v.processing.processed_quality.score)],
  ];
  return groups.filter(([,scores])=>scores.length).map(([label,scores])=>({label,score:mean(scores)}));
}
function chart(series,compact=false){
  if(!series.length)return '<p class="sub">Nenhum registro disponível para calcular o score.</p>';
  const y=score=>18+(100-score)*0.74;
  const points=series.map(({label,score},i)=>({label,score,x:(i+0.5)*100/series.length,y:y(score)}));
  const line=points.map(p=>`${p.x},${p.y}`).join(' ');
  const area=`${points[0].x},92 ${line} ${points.at(-1).x},92`;
  const threshold=y(LIM);
  return `<figure class="quality-chart${compact?' compact':''}">
    <div class="chart-plot" aria-hidden="true">
      <svg class="chart" viewBox="0 0 100 100" preserveAspectRatio="none">
        <line x1="0" x2="100" y1="${threshold}" y2="${threshold}" class="chart-threshold" vector-effect="non-scaling-stroke"/>
        <polygon points="${area}" class="chart-area"/>
        <polyline points="${line}" class="chart-line" vector-effect="non-scaling-stroke"/>
      </svg>
      ${points.map(p=>`<span class="chart-point" style="left:${p.x}%;top:${p.y}%"><b>${numberBR(p.score)}</b></span>`).join('')}
    </div>
    <figcaption>
      <div class="chart-labels" style="grid-template-columns:repeat(${points.length}, minmax(0,1fr))">
        ${points.map(p=>`<span>${esc(p.label)}<span class="chart-sr">: ${numberBR(p.score)} de 100</span></span>`).join('')}
      </div>
      <small class="chart-key">Mínimo para publicar: ${LIM}/100</small>
    </figcaption>
  </figure>`;
}
function qualityComparison(v){
  const {raw_quality:raw,processed_quality:processed,raw_count,processed_count}=v.processing;
  const dimensions=[
    ['completeness','Completude','Campos obrigatórios preenchidos'],
    ['accuracy','Acurácia','Medidas numéricas conferidas com a base de referência'],
    ['consistency','Consistência','Registros sem repetição na chave de identificação'],
    ['validity','Validade','Valores preenchidos conformes ao tipo, formato e domínio'],
  ];
  function metric(q,key,rows){
    if(!rows)return 'Sem registros';
    const m=q.dimensions[key];
    const coverage=m.reference?`<br><span class="sub">${esc(m.reference)} · ${numberBR(m.matched_records)} de ${numberBR(m.total_records)} registros encontrados</span>`:'';
    if(m.score==null)return (key==='accuracy'&&!m.reference?'Sem referência':'Sem verificações')+coverage;
    return `<b>${numberBR(m.score)}%</b><br><span class="sub">${numberBR(m.failures)} falhas em ${numberBR(m.checked)} verificações</span>${coverage}`;
  }
  const total=(q,rows)=>rows?`<b>${numberBR(q.score)}/100</b><br><span class="sub">${q.measured_dimensions} de 4 dimensões medidas</span>`:'Sem registros';
  return panel('Comparativo de qualidade','Brutos e processados da carga atual',`<div class="tw"><table>
    <thead><tr><th>Dimensão</th><th>Brutos</th><th>Processados</th><th>O que foi verificado</th></tr></thead>
    <tbody>${dimensions.map(([key,label,rule])=>`<tr><th scope="row">${label}</th><td>${metric(raw,key,raw_count)}</td><td>${metric(processed,key,processed_count)}</td><td>${rule}</td></tr>`).join('')}
    <tr><th scope="row">Data Quality Score</th><td>${total(raw,raw_count)}</td><td>${total(processed,processed_count)}</td><td>Média das dimensões medidas</td></tr></tbody>
  </table></div>`);
}
function datasetQuality(d, compact=false){
  const v=currentVersion(d),q=v.quality,initial=v.initial_diagnosis;
  const diagnosis=initial?`Diagnóstico inicial: ${numberBR(initial.score)}/100 · ${numberBR(initial.records)} registros`:'Diagnóstico inicial desta carga indisponível';
  const canValidate=!DATA.user.preview&&(role==='admin'||role===d.sec)&&counts(v).raw>0;
  const metrics=MET.map((label,i)=>{
    const value=q.metrics[i];
    const synthetic=i===1&&q.dimensions.accuracy.reference;
    return `<div><dt>${label}${synthetic?' (demo)':''}</dt><dd>${value==null?(i===1&&!synthetic?'Sem referência':'Sem verificações'):numberBR(value)+'%'}</dd></div>`;
  }).join('');
  return panel(esc(d.name),`Score atual: ${numberBR(q.score)}/100 · ${diagnosis}`,
    chart(qualitySeries([d]),compact)+`<dl class="quality-metrics">${metrics}</dl>`+
    `<div class="quality-actions"><button class="btn" data-a="detail" data-id="${d.id}">Consultar registros</button>${canValidate?`<button class="btn" data-a="revalidate" data-id="${d.id}">Revalidar registros sem pendências</button>`:''}</div>`);
}
function overviewQuality(){
  return '<div class="overview-quality">'+SEC.filter(s=>s.available&&mine(s)).map(s=>{
    const datasets=DATA.datasets.filter(d=>d.sec===s.id);
    return panel(s.n,`Média da secretaria: ${s.score==null?'Sem dados':numberBR(s.score)+'/100'} · cada dataset tem o mesmo peso`,
      `<div class="dataset-grid">${datasets.map(d=>datasetQuality(d)).join('')}</div>`);
  }).join('')+'</div>';
}
function distributionPanel(compact=false){
  const s=distribution(),percentage=n=>s.total?Math.round(n/s.total*100):0;
  if(compact){
    const processed=s.total?s.processed/s.total*100:0;
    return '<div class="overview-distribution">'+panel('Distribuição dos registros',`${numberBR(s.total)} registros em ${s.bases} bases`,
      `<div class="distribution-bar" aria-hidden="true"><i style="width:${processed}%"></i></div>
      <div class="distribution-summary"><span><i></i><b>${numberBR(s.processed)}</b> processados (${percentage(s.processed)}%)</span>
      <span><i></i><b>${numberBR(s.raw)}</b> brutos (${percentage(s.raw)}%)</span>
      <button class="btn" data-a="refresh-real">Atualizar dados</button></div>`)+'</div>';
  }
  return panel('Distribuição dos registros','Dados atuais das bases disponíveis',
    `<div class="row"><div><b>${numberBR(s.total)} registros em ${s.bases} bases</b><small>Dados da planilha e registros sintéticos na mesma consulta</small></div><button class="btn" data-a="refresh-real">Atualizar dados</button></div>`+
    `<div class="row"><div><b>Processados: ${numberBR(s.processed)} (${percentage(s.processed)}%)</b><small>Score calculado por subconjunto</small></div>${bdg('Processados','ok')}</div>`+
    `<div class="row"><div><b>Brutos / em tratamento: ${numberBR(s.raw)} (${percentage(s.raw)}%)</b><small>Registros brutos em todas as bases; consulte as pendências na fila de sugestões</small></div>${bdg('Brutos / em tratamento','warn')}</div>`);
}
async function api(path,options={}){
  const headers={...(options.headers||{})};
  if(DATA?.mode==='demo')headers['X-Demo-Role']=role;
  else if(previewDepartment)headers['X-DataHub-Preview']=previewDepartment;
  if(options.body && !(options.body instanceof FormData))headers['Content-Type']='application/json';
  const r=await fetch('/api'+path,{...options,headers});
  if(!r.ok){let text;try{text=(await r.json()).detail}catch(_){text='Falha na API'}throw Error(typeof text==='string'?text:JSON.stringify(text))}
  return r.json();
}
async function refresh(){
  DATA=await api('/state');role=DATA.user.role;LIM=DATA.publication_min_score;
  const ds=DATA.datasets;
  SEC.splice(0,SEC.length,...DATA.secretarias.map(s=>{
    const bases=ds.filter(d=>d.sec===s.id),current=bases.map(d=>d.versions.at(-1));
    return {...s,score:s.quality?.mean??null,pend:DATA.suggestions.filter(x=>x.sec===s.id&&x.status==='pending').length,upd:current.length?new Date(current.at(-1).created_at).toLocaleDateString('pt-BR'):'—',pub:bases.some(d=>d.published_version!==null),available:!!bases.length};
  }));
  SUG.splice(0,SUG.length,...DATA.suggestions.filter(s=>['pending','approved','rejected'].includes(s.status)).map(s=>({id:s.id,s:s.sec,a:esc(s.before==null?'(vazio)':typeof s.before==='object'?JSON.stringify(s.before):s.before),b:esc(s.after??'Confirmar na fonte'),p:s.similarity??null,why:esc(s.reason+' · '+s.dataset+' · linha '+(s.row+2))})));
  Object.keys(dec).forEach(k=>delete dec[k]);DATA.suggestions.forEach(s=>{if(s.status==='approved')dec[s.id]='ok';if(s.status==='rejected')dec[s.id]='no'});
  PASS.splice(0,PASS.length,...ds.flatMap(d=>d.versions.map(v=>['v'+v.number,d.sec,esc(d.name)+' · '+(v.treated?'Tratado':'Original / em tratamento')+' · '+v.rows.length+' registros · '+v.changes.length+' alterações · Score '+v.quality.score,esc(v.author),new Date(v.created_at).toLocaleDateString('pt-BR')])).reverse());
  CAT.splice(0,CAT.length,...ds.map(d=>[esc(d.name),d.sec,'v'+d.versions.at(-1).number,({publico:'Público',restrito:'Restrito',sigiloso:'Sigiloso'})[d.classification],d.versions.at(-1).quality.score,d.id]));
  INST.splice(0,INST.length);ds.forEach(d=>{const v=d.versions.at(-1);const c=['unidade','escola','cras'].find(c=>c in (v.rows[0]||{}));if(c)[...new Set(v.rows.map(r=>r[c]))].forEach(n=>INST.push([esc(n),v.quality.score,d.sec]))});
  grants=DATA.grants;
  Object.assign(NAMES,Object.fromEntries(SEC.map(s=>[s.id,s.n])),{admin:esc(DATA.user.name)});
  Object.assign(SUB,Object.fromEntries(SEC.map(s=>[s.id,s.n+' · dados da secretaria'])),{admin:DATA.mode==='demo'?'Demonstração local · dados fornecidos ao projeto':'Administração · Supabase'});
  const maySwitch=DATA.mode==='demo'||DATA.user.can_preview;
  $('#role').innerHTML=maySwitch?'<option value="admin">Administração (STI)</option>'+SEC.map(s=>`<option value="${s.id}">Visualizar: ${esc(s.n)}</option>`).join(''):`<option value="${role}">${NAMES[role]}</option>`;
  $('#role').disabled=!maySwitch;
  $('#role').setAttribute('aria-label','Perfil de visualização');
  if(!SEC.some(s=>s.id===cur&&s.available))cur=SEC.find(s=>s.id===role&&s.available)?.id||SEC.find(s=>s.available)?.id||'saude';
  render();
  $('.sfoot').textContent=DATA.mode==='demo'?'Demonstração local · troca de perfil para testes':`Supabase Auth · ${DATA.user.name}`;
}

const originalOverview=V.geral;
V.geral=()=>{
  const html=originalOverview();
  return '<div class="overview-layout">'+html.replace('<div class="kpis">',distributionPanel(true)+'<div class="kpis">')+'</div>';
};
V.catalogo=()=>{
  return head('Catálogo de datasets','Dados da planilha e registros sintéticos integrados; score por dataset')
    +distributionPanel()
    +panel('Datasets','Selecione um dataset para consultar e filtrar os registros',
    `<div class="tw"><table><tr><th>Dataset</th><th>Secretaria</th><th>Registros</th><th>Estado</th><th>Classificação</th><th>Score da base</th></tr>${DATA.datasets.map(d=>{
      const v=currentVersion(d);
      const c=counts(v),q=v.quality;
      return `<tr><td><button class="btn" data-a="detail" data-id="${d.id}">${esc(d.name)}</button></td><td>${sname(d.sec)}</td><td class="mono">${numberBR(v.rows.length)} (${numberBR(c.raw)} brutos / ${numberBR(c.processed)} processados)</td><td>${bdg(processingLabel(v),c.raw?'warn':'ok')}</td><td>${bdg(({publico:'Público',restrito:'Restrito',sigiloso:'Sigiloso'})[d.classification])}</td><td>${bdg(numberBR(q.score),kind(q.score))}</td></tr>`;
    }).join('')||'<tr><td colspan="6">Nenhum dataset disponível.</td></tr>'}</table></div>`);
};
V.publicar=()=>head('Publicar no CKAN','Portal público de demonstração')+
  (DATA.user.preview?note('Um funcionário autenticado desta secretaria pode publicar os próprios datasets aptos. Nesta visualização, as ações são somente leitura.'):'')+
  panel('Verificações de publicação','Cada secretaria pode publicar seus datasets aptos. As verificações usam os registros processados.',DATA.datasets.filter(d=>role==='admin'||d.sec===role).map(d=>{
  const check=d.publication_check,ok=check.eligible;
  const published=d.published_version===currentVersion(d).number;
  const result=ok?'Todas as verificações passaram':`Publicação bloqueada: ${esc(check.reasons.join(' · '))}`;
  let action='';
  if(ok&&published)action=`<a class="btn p" href="/public/${encodeURIComponent(d.id)}" target="_blank" rel="noopener">Ver publicação ↗</a>`;
  else if(ok&&d.can_publish)action=`<button class="btn p" data-a="publish-real" data-id="${d.id}">Publicar ↗</button>`;
  return `<div class="row"><div class="publication-summary"><b>${esc(d.name)}</b><small>Score dos processados: ${check.processed_count?numberBR(check.score)+'/100':'Sem registros'} · mínimo: ${check.min_score}/100</small><small>${result}</small></div><div class="publication-actions">${bdg(ok?(published?'Publicado':'Apto'):'Bloqueado',ok?'ok':'warn')}${action}</div></div>`;
}).join(''));
V.passport=()=>head('Data Passport','Identificação e atualização dos dados atuais')+panel('Bases atuais','Somente os dados mais recentes',`<div class="tw"><table><tr><th>Dataset</th><th>Registros</th><th>Brutos</th><th>Processados</th><th>Atualização</th><th></th></tr>${DATA.datasets.filter(d=>role==='admin'||d.sec===role).map(d=>{const v=currentVersion(d),c=counts(v);return `<tr><td>${esc(d.name)}</td><td>${v.rows.length}</td><td>${c.raw}</td><td>${c.processed}</td><td>${new Date(v.created_at).toLocaleDateString('pt-BR')}</td><td><button class="btn" data-a="detail" data-id="${d.id}">Consultar registros</button></td></tr>`}).join('')}</table></div>`);

async function detail(id,number){
  const d=DATA.datasets.find(d=>d.id===id),v=d.versions.find(v=>v.number===number)||d.versions.at(-1);
  const cols=d.dictionary.map(c=>c.nome_coluna);
  const status=rowStates(v),visible=matchingRows(d,v,recordFilter,recordSearch),c=counts(v);
  const searching=!!(recordSearch.column||recordSearch.query);
  const searchForm=`<form id="record-search" class="record-search" data-id="${esc(d.id)}" data-number="${v.number}">
    <label for="record-column">Coluna<select id="record-column" name="column">
      <option value="">Todas as colunas</option>${cols.map(column=>`<option value="${esc(column)}" ${column===recordSearch.column?'selected':''}>${esc(column)}</option>`).join('')}
    </select></label>
    <label for="record-query">Valor da coluna<input id="record-query" name="query" type="search" value="${esc(recordSearch.query)}"></label>
    <div class="record-search-actions"><button class="btn p" type="submit">Pesquisar</button>${searching?`<button class="btn" type="button" data-a="record-clear" data-id="${esc(d.id)}" data-number="${v.number}">Limpar busca</button>`:''}</div>
  </form>`;
  const subsetQuality=recordFilter==='all'?v.quality:v.processing?.[recordFilter+'_quality']||v.quality;
  const rows=visible.map(({r,i})=>`<tr><td>${bdg(status[i]==='processed'?'Processado':'Bruto',status[i]==='processed'?'ok':'warn')}</td>${cols.map(c=>`<td>${esc(r[c]??'—')}</td>`).join('')}</tr>`).join('')
    ||`<tr><td colspan="${cols.length+1}">Nenhum registro encontrado com esses filtros.</td></tr>`;
  $('#page').innerHTML=previewNotice()+head(esc(d.name),`Dados atuais · ${processingLabel(v)} · ${numberBR(v.rows.length)} registros · Score ${numberBR(v.quality.score)}`)
    +qualityComparison(v)
    +panel('Registros',`${numberBR(visible.length)} ${visible.length===1?'linha exibida':'linhas exibidas'} · ${numberBR(c.raw)} brutos / ${numberBR(c.processed)} processados no dataset · Score do estado selecionado: ${numberBR(subsetQuality.score)}`, searchForm+`<div class="chips" role="group" aria-label="Estado dos registros">${[['all','Todos'],['raw','Brutos'],['processed','Processados']].map(([key,label])=>`<button class="chip ${recordFilter===key?'on':''}" aria-pressed="${recordFilter===key}" data-a="record-filter" data-id="${id}" data-number="${v.number}" data-filter="${key}">${label}</button>`).join('')}</div><div class="tw"><table><tr><th>Estado</th>${cols.map(c=>`<th>${esc(c)}</th>`).join('')}</tr>${rows}</table></div>`)
    +panel('Data Passport','Identificação e diagnóstico do dataset',`<p class="sub">Atualização: ${new Date(v.created_at).toLocaleString('pt-BR')} · Responsável: ${esc(v.author)}</p><p class="sub">Diagnóstico inicial: ${v.initial_diagnosis?numberBR(v.initial_diagnosis.score)+'/100':'Indisponível'} · Score atual: ${numberBR(v.quality.score)}/100</p><p class="sub">SHA-256: ${v.hash}</p>`);
}

document.addEventListener('submit',async e=>{
  if(e.target.id!=='record-search')return;
  e.preventDefault();
  const form=new FormData(e.target);
  recordSearch={column:String(form.get('column')||''),query:String(form.get('query')||'').trim()};
  await detail(e.target.dataset.id,Number(e.target.dataset.number));
  $('#record-query').focus();
});

document.addEventListener('click',async e=>{
  const el=e.target.closest('[data-a]');if(!el)return;
  const a=el.dataset.a,id=el.dataset.id;
  if(!['sug','pub','publish-real','grant','rev','impok','detail','version','refresh-real','record-filter','revalidate','record-clear'].includes(a))return;
  e.preventDefault();e.stopImmediatePropagation();
  el.disabled=true;
  try{
    if(a==='record-clear'){
      recordSearch={column:'',query:''};
      await detail(id,Number(el.dataset.number));$('#record-query').focus();return
    }
    if(a==='record-filter'){recordFilter=el.dataset.filter;await detail(id,Number(el.dataset.number));return}
    if(a==='sug')await api('/suggestions/'+id+'/decision',{method:'POST',body:JSON.stringify({decision:el.dataset.d==='ok'?'approved':'rejected'})});
    if(a==='revalidate'){
      const result=await api('/datasets/'+id+'/revalidate',{method:'POST'});
      await refresh();toast(`${numberBR(result.validated)} registros revalidados`);
      return;
    }
    if(a==='publish-real'){
      const tab=window.open('about:blank','_blank');
      try{const result=await api('/datasets/'+id+'/publish',{method:'POST'});if(tab)tab.location=result.url;else location.href=result.url}catch(err){tab?.close();throw err}
    }
    if(a==='pub')throw Error('Selecione o dataset na tela de publicação');
    if(a==='grant')await api('/grants',{method:'POST',body:JSON.stringify({f:$('#gf').value,t:$('#gt').value})});
    if(a==='rev')await api('/grants/'+grants[Number(id)].id,{method:'DELETE'});
    if(a==='impok'){
      if(!imp?.file)throw Error('Escolha um arquivo');
      const form=new FormData();form.append('file',imp.file);form.append('sec',imp.sec);form.append('sheet',imp.sheet||'');
      await api('/import',{method:'POST',body:form});closeImp();
    }
    if(a==='detail'||a==='version'){
      recordFilter='all';
      recordSearch={column:'',query:''};
      await detail(id,Number(el.dataset.number));return
    }
    await refresh();toast('Alteração salva');
  }catch(err){toast(err.message)}finally{el.disabled=false}
},true);
document.addEventListener('change',async e=>{
  if(e.target.id!=='role')return;
  e.stopImmediatePropagation();
  if(DATA.mode!=='demo'&&!DATA.user.can_preview)return;
  const previousRole=role,previousPreview=previewDepartment;
  if(DATA.mode==='demo')role=e.target.value;
  else previewDepartment=e.target.value==='admin'?null:e.target.value;
  e.target.disabled=true;
  mf='all';view='geral';recordFilter='all';recordSearch={column:'',query:''};
  try{await refresh()}catch(err){
    role=previousRole;previewDepartment=previousPreview;render();toast(err.message);
  }finally{e.target.disabled=false}
},true);
refresh().catch(err=>{$('#page').textContent=err.message+' · Acesse /login para autenticar.'});
