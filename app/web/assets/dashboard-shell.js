const $=s=>document.querySelector(s);
const P={dash:'<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>',
building:'<path d="M3 21h18M5 21V7l7-4 7 4v14M9 9h1M14 9h1M9 13h1M14 13h1M10 21v-4h4v4"/>',
list:'<path d="M3 6h.01M3 12h.01M3 18h.01M8 6h13M8 12h13M8 18h13"/>',
hist:'<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2"/>',
db:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
map:'<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14"/>',
globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
shield:'<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
moon:'<path d="M21 13A9 9 0 1 1 11 3a7 7 0 0 0 10 10z"/>',
menu:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/>',
lock:'<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
upload:'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
file:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6"/>',
x:'<path d="M18 6 6 18M6 6l12 12"/>'};
const ic=n=>`<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n]}</svg>`;

let LIM=95;
const SEC=[];
SEC.forEach(s=>s.score=Math.round(s.m.reduce((a,b)=>a+b)/4));
const MET=['Completude','Acurácia','Consistência','Validade'];
const SUG=[];
const PASS=[];
const CAT=[];
const INST=[];
const NAMES={admin:'Administrador',saude:'Saúde',educacao:'Educação',assistencia:'Assistência Social',ti:'Tecnologia e Inovação'};
const SUB={};
const TITLES={geral:'Visão geral',secretaria:'Secretarias',sugestoes:'Fila de sugestões',passport:'Data Passport',catalogo:'Catálogo de datasets',mapa:'Mapeamento administrativo',publicar:'Publicar no CKAN',permissoes:'Permissões'};
const NAV=[['Painel',[['geral','dash'],['secretaria','building'],['mapa','map']]],['Qualidade dos dados',[['sugestoes','list'],['passport','hist'],['catalogo','db']]],['Dados abertos',[['publicar','globe']]],['Administração',[['permissoes','shield']]]];
let role='admin',view='geral',cur='saude',mf='all';
let grants=[];
const dec={};

const adm=()=>role==='admin';
const MAP_MEDIUM_MIN=70;
const kind=v=>v>=LIM?'ok':v>=MAP_MEDIUM_MIN?'warn':'bad';
const sname=id=>SEC.find(s=>s.id===id).n;
const tier=s=>adm()?'full':s.id===role?'own':s.available&&grants.some(g=>g.f===s.id&&g.t===role)?'grant':'lock';
const vis=s=>tier(s)!=='lock';
const mine=s=>adm()||s.id===role;
const avg=a=>Math.round(a.reduce((x,y)=>x+y,0)/a.length);
const bdg=(t,k='')=>`<span class="b ${k}">${t}</span>`;
const note=t=>`<div class="note">${ic('info')}<span>${t}</span></div>`;
const bar=(v,k)=>`<div class="bar"><i class="fill-${k||kind(v)}" style="width:${v}%"></i></div>`;
const head=(t,s,r='')=>`<div class="head"><div><h1>${t}</h1><p class="sub">${s||''}</p></div>${r}</div>`;
const panel=(t,d,body)=>`<section class="card cp"><div class="ch"><div><h3>${t}</h3>${d?`<p>${d}</p>`:''}</div></div>${body}</section>`;
const suggestionStatus=id=>dec[id]==='ok'?bdg('Aprovada','ok'):dec[id]==='no'?bdg('Rejeitada'):bdg('Pendente','warn');
const actions=id=>dec[id]||DATA.user.preview?suggestionStatus(id):`<button class="btn" data-a="sug" data-id="${id}" data-d="ok">Aprovar</button> <button class="btn bad" data-a="sug" data-id="${id}" data-d="no">Rejeitar</button>`;

function geral(){
  
  const me=SEC.find(s=>s.id===role),recv=grants.filter(g=>g.t===role).length;
  const pend=adm()?SEC.reduce((a,s)=>a+s.pend,0):me.pend;
  const K=adm()?[['Pendências abertas',pend,'sugestões aguardando decisão','list'],['Datasets publicados',DATA.datasets.filter(d=>d.published_version!==null).length+' de '+DATA.datasets.length,'no portal de dados abertos','globe'],['Concessões ativas',grants.length,'acessos cruzados entre secretarias','shield']]
  :[['Média da sua secretaria',me.score==null?'—':numberBR(me.score),'Datasets atuais da secretaria','dash'],['Suas pendências',me.pend,'sugestões aguardando decisão','list'],['Seu dataset publicado',me.pub?'Sim':'Não',me.pub?'visível no portal':`exige score mínimo de ${LIM}`,'globe'],['Acessos concedidos a você',recv,'secretarias liberadas','shield']];
  
  const pb=SEC.filter(vis).sort((a,b)=>b.pend-a.pend).map(s=>`<div class="m" style="grid-template-columns:1fr 90px 24px"><span>${s.n}</span>${bar(s.pend/Math.max(1,...SEC.map(x=>x.pend))*100,'warn')}<b>${s.pend}</b></div>`).join('');
  const cards=SEC.map(s=>{const t=tier(s);
    const bd=t==='pub'?bdg('Publicado','ok'):t==='grant'?bdg('Acesso concedido','pri'):t==='own'?bdg('Sua secretaria','pri'):t==='lock'?bdg('Privado','bad'):bdg(s.pub?'Publicado':'Interno',s.pub?'ok':'');
    return t==='lock'?`<div class="card sc lock"><h4>${s.n} ${ic('lock')}</h4><small>Requer concessão do administrador</small><div style="margin-top:12px">${bd}</div></div>`
    :`<button class="card sc" data-a="sec" data-id="${s.id}"><h4>${s.n}</h4><small>Atualizado ${s.upd}</small><div class="num">${s.score==null?'—':numberBR(s.score)}</div>${s.score==null?'':bar(s.score)}<div style="margin-top:12px">${bd}</div></button>`}).join('');
  return head('Bom dia, '+NAMES[role].split(' ')[0],SUB[role])
  +(adm()?'':note(`Controle de acesso ativo: você vê o painel de <b>${me.n}</b>. As demais secretarias aparecem trancadas, até o administrador conceder acesso.`))
  +`<div class="kpis">${K.map(k=>`<div class="card kpi"><div class="l">${k[0]}${ic(k[3])}</div><div class="v">${k[1]}</div><div class="n">${k[2]}</div></div>`).join('')}</div>
  ${overviewQuality()}<div class="overview-pending">${panel('Pendências por secretaria','Sugestões de padronização em aberto',pb)}</div>
  <h3 style="margin:24px 0 12px;font-size:15px">Secretarias</h3><div class="cards">${cards}</div>`;
}

function secretaria(){
  const s=SEC.find(x=>x.id===cur),ro=!mine(s);
  const sg=SUG.filter(x=>x.s===s.id);
  return head(s.n,ro?'Visualização somente leitura (acesso concedido pelo administrador)':'Detalhamento do Data Quality Score',s.score==null?'':bdg('Média da secretaria '+numberBR(s.score),kind(s.score)))
  +departmentTabs()
  +`<div class="dataset-grid department-quality">${DATA.datasets.filter(d=>d.sec===cur).map(d=>datasetQuality(d,true)).join('')}</div>`
  +panel('Inconsistências detectadas','Acompanhe o status das sugestões desta secretaria',(!ro&&sg.length?'<div class="row"><button class="btn" data-a="nav" data-id="sugestoes">Abrir fila de sugestões</button></div>':'')+(sg.length?`<div class="tw"><table><tr><th>Termo original</th><th>Sugestão</th><th>Motivo</th><th title="Similaridade textual entre o termo original e a sugestão. Não é o Data Quality Score.">Similaridade</th><th>Status</th></tr>${sg.map(x=>`<tr><td>${x.a}</td><td>${x.b}</td><td>${x.why}</td><td class="mono">${x.p!=null?numberBR(x.p)+'%':'Sem par textual'}</td><td>${suggestionStatus(x.id)}</td></tr>`).join('')}</table></div>`:'<p class="sub">Nenhuma sugestão para esta secretaria.</p>'));
}

function sugestoes(){
  const L=SUG.filter(x=>adm()||x.s===role);
  return head('Fila de sugestões','Aprovações voltam ao fluxo de mineração como feedback')+(adm()?'':note('Exibindo apenas sugestões da sua secretaria.'))
  +panel('Sugestões de padronização','Similaridade compara o rótulo original com a correção sugerida. Datas, valores vazios e sugestões sem texto de referência aparecem como Sem par textual.',`<div class="tw"><table><tr><th>Secretaria</th><th>Termo original</th><th>Sugestão</th><th>Motivo</th><th title="Similaridade textual entre o termo original e a sugestão. Não é o Data Quality Score.">Similaridade</th><th></th></tr>${L.map(x=>`<tr><td>${sname(x.s)}</td><td>${x.a}</td><td>${x.b}</td><td>${x.why}</td><td class="mono">${x.p!=null?numberBR(x.p)+'%':'Sem par textual'}</td><td>${actions(x.id)}</td></tr>`).join('')}</table></div>`);
}

function passport(){
  return head('Data Passport','Histórico de versões e alterações de cada conjunto de dados')+(adm()?'':note('Exibindo apenas o histórico da sua secretaria.'))
  +panel('Registro de alterações','',`<div class="tw"><table><tr><th>Versão</th><th>Secretaria</th><th>Alteração</th><th>Responsável</th><th>Data</th></tr>${PASS.filter(r=>adm()||r[1]===role).map(r=>`<tr><td class="mono">${r[0]}</td><td>${sname(r[1])}</td><td>${r[2]}</td><td>${r[3]}</td><td>${r[4]}</td></tr>`).join('')}</table></div>`);
}

function catalogo(){
  const cls={Público:'ok',Interno:'warn',Restrito:'bad'};
  const rows=CAT.filter(r=>vis(SEC.find(s=>s.id===r[1])));
  return head('Catálogo de datasets','Metadados, versão e classificação de cada conjunto de dados')
  +panel('Datasets','Catálogo interno de metadados',`<div class="tw"><table><tr><th>Dataset</th><th>Secretaria</th><th>Versão</th><th>Classificação</th><th>Score</th></tr>${rows.map(r=>{const s=SEC.find(x=>x.id===r[1]);return `<tr><td>${r[0]}</td><td>${s.n}</td><td class="mono">${r[2]}</td><td>${bdg(r[3],cls[r[3]])}</td><td>${bdg(s.score,kind(s.score))}</td></tr>`}).join('')}</table></div>`);
}

function mapa(){
  const L=INST.filter(i=>vis(SEC.find(s=>s.id===i[2]))&&(mf==='all'||i[2]===mf));
  const fl=[['all','Todas as secretarias'],...SEC.filter(vis).map(s=>[s.id,s.n])];
  return head('Mapeamento administrativo','Unidades e serviços por secretaria, coloridos pelo score da base de origem')+(adm()?'':note('Mapa restrito às unidades da sua secretaria e às unidades das secretarias com acesso concedido pelo administrador.'))
  +`<div class="chips">${fl.map(f=>`<button class="chip ${mf===f[0]?'on':''}" data-a="mf" data-id="${f[0]}">${f[1]}</button>`).join('')}</div>
  <div class="tiles">${L.map(i=>`<div class="tile" style="border-left-color:var(--${kind(i[1])})" title="Score ${i[1]}">${i[0]}<small class="mono">${i[1]}</small></div>`).join('')}</div>
  <div class="lg"><span><i style="background:var(--ok)"></i>Score alto (≥ ${LIM})</span><span><i style="background:var(--warn)"></i>Score médio (≥ ${MAP_MEDIUM_MIN} e &lt; ${LIM})</span><span><i style="background:var(--bad)"></i>Score baixo (&lt; ${MAP_MEDIUM_MIN})</span></div>`;
}


function openPublication(s){return false}

function publicar(){
  const L=SEC.filter(mine);
  return head('Publicar no CKAN',`Demonstração visual · score mínimo ${LIM} · Publicar abre a página em uma nova aba`)+(adm()?'':note('Você só pode publicar datasets da sua própria secretaria.'))
  +panel('Datasets tratados','Publicação por ação do responsável',L.map(s=>{const ok=s.score>=LIM;
  return `<div class="row"><div><b>${s.n}</b><small>Score ${s.score} · dataset tratado e validado</small></div><div style="display:flex;gap:10px;align-items:center">${s.pub?bdg('Publicado','ok'):bdg(ok?'Apto':`Abaixo do mínimo (${LIM})`,ok?'ok':'warn')}<button class="btn p" data-a="pub" data-id="${s.id}" ${ok?'':'disabled'} aria-label="${s.pub?'Ver publicação de':'Publicar'} ${s.n} em nova aba">${s.pub?'Ver publicação ↗':'Publicar ↗'}</button></div></div>`}).join(''));
}

function permissoes(){
  const o=SEC.map(s=>`<option value="${s.id}">${s.n}</option>`).join('');
  return head('Permissões entre secretarias','Concessões de acesso cruzado, visíveis apenas para o administrador da STI')
  +panel('Nova concessão','',`<div class="form"><select id="gf" aria-label="Secretaria dona do dado">${o}</select><span>libera para</span><select id="gt" aria-label="Secretaria com acesso">${o}</select><button class="btn p" data-a="grant">Conceder acesso</button></div>
  <div class="tw"><table><tr><th>Secretaria dona do dado</th><th>Secretaria com acesso</th><th>Concedido por</th><th>Validade</th><th></th></tr>${grants.map((g,i)=>`<tr><td>${sname(g.f)}</td><td>${sname(g.t)}</td><td>${g.by}</td><td>${g.until}</td><td><button class="btn bad" data-a="rev" data-id="${i}">Revogar</button></td></tr>`).join('')||'<tr><td colspan="5" class="sub">Nenhuma concessão ativa. Use o formulário acima para liberar um dado a outra secretaria.</td></tr>'}</table></div>`);
}

const V={geral,secretaria,sugestoes,passport,catalogo,mapa,publicar,permissoes};
function render(){
  if(view==='permissoes'&&!adm())view='geral';
  $('#side').innerHTML=`<div class="brand"><div class="logo">MD</div><div><b>Marília DataHub</b><small>Gestão pública</small></div></div>`
   +NAV.map(([g,items])=>{const it=items.filter(i=>i[0]!=='permissoes'||adm());return it.length?`<div class="grp">${g}</div>`+it.map(([v,i])=>`<button class="nav ${view===v?'on':''}" data-a="nav" data-id="${v}">${ic(i)}${TITLES[v]}</button>`).join(''):''}).join('')
   +`<div class="sfoot"><b>Sessão DataHub</b>${DATA.mode==='demo'?'Demonstração local · perfis para testes':'Supabase Auth · sessão validada'}</div>`;
  $('#page').innerHTML=previewNotice()+V[view]();
  $('#crumb').textContent=TITLES[view];
  $('#who').textContent=NAMES[role];$('#av').textContent=NAMES[role].split(' ').map(x=>x[0]).join('');
  $('#role').value=role;
  document.querySelector('[data-a="menu"]').innerHTML=ic('menu');
  $('#impBtn').hidden=!!DATA.user.preview;
  $('#impBtn').innerHTML=ic('upload')+'<span class="lbl">Importar arquivo</span>';
  const dark=document.documentElement.dataset.theme?document.documentElement.dataset.theme==='dark':matchMedia('(prefers-color-scheme:dark)').matches;
  $('#themeBtn').innerHTML=ic(dark?'sun':'moon');
}
function go(v){view=v;$('#app').classList.remove('open');render();scrollTo(0,0)}
function toast(t){const e=document.createElement('div');e.className='toast';e.textContent=t;document.body.appendChild(e);setTimeout(()=>e.remove(),2600)}


/* ===== Importar arquivo (xlsx / csv) ===== */
let imp=null;const MAXMB=10;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fsize=b=>b<1048576?Math.max(1,Math.round(b/1024))+' KB':(b/1048576).toFixed(1).replace('.',',')+' MB';
function openImp(){
  if (DATA.user.preview) return;
  imp={sec:adm()?cur:role,file:null,wb:null,sheet:null,rows:[],st:null,err:''};
  let o=$('#imp');if(!o){o=document.createElement('div');o.id='imp';o.className='ov';o.dataset.a='impbg';document.body.appendChild(o)}
  drawImp();
}
function closeImp(){const o=$('#imp');if(o)o.remove();imp=null}
function setSheet(n){
  imp.sheet=n;
  const r=XLSX.utils.sheet_to_json(imp.wb.Sheets[n],{header:1,defval:'',blankrows:false,raw:false});
  const cols=r.reduce((m,x)=>Math.max(m,x.length),0),body=r.slice(1).map(x=>Array.from({length:cols},(_,j)=>x[j]??''));
  const cells=body.length*cols,empty=body.reduce((a,x)=>a+x.filter(c=>String(c).trim()==='').length,0);
  const dup=body.length-new Set(body.map(x=>x.join('\u0001'))).size;
  imp.rows=r;imp.st={rows:body.length,cols,empty:cells?Math.round(empty/cells*100):0,dup};
}
async function loadFile(f){
  if(!f||!imp)return;
  const ext=(f.name.split('.').pop()||'').toLowerCase();
  imp.err='';
  if(!['xlsx','csv'].includes(ext)){imp.err='Formato não suportado. Envie um arquivo .xlsx ou .csv.';return drawImp()}
  if(f.size>MAXMB*1048576){imp.err=`O arquivo tem mais de ${MAXMB} MB.`;return drawImp()}
  if(!window.XLSX){imp.err='Não foi possível carregar o leitor de planilhas. Verifique a conexão e tente novamente.';return drawImp()}
  try{
    const buf=await f.arrayBuffer();let wb;
    if(ext==='csv'){let t;try{t=new TextDecoder('utf-8',{fatal:true}).decode(buf)}catch(_){t=new TextDecoder('windows-1252').decode(buf)}wb=XLSX.read(t,{type:'string'})}
    else wb=XLSX.read(buf,{type:'array'});
    if(!wb.SheetNames.length)throw 0;
    imp.file=f;imp.wb=wb;setSheet(wb.SheetNames[0]);
    if(imp.rows.length<2){imp.file=null;imp.err='O arquivo não tem dados. É preciso ao menos o cabeçalho e uma linha.'}
  }catch(_){imp.file=null;imp.err='Não foi possível ler o arquivo. Confira se ele não está corrompido ou protegido por senha.'}
  drawImp();
}
function drawImp(){
  const o=$('#imp');if(!o||!imp)return;
  const secs=adm()?SEC:SEC.filter(x=>x.id===role),st=imp.st;
  let body;
  if(!imp.file){
    body=`<div class="drop" id="impDrop" role="button" tabindex="0" data-a="impPick">${ic('upload')}<b>Arraste um arquivo aqui ou clique para escolher</b><small>.xlsx ou .csv · até ${MAXMB} MB</small></div>`;
  }else{
    const mx=Math.min(st.cols,8),hd=imp.rows[0],pv=imp.rows.slice(1,6);
    body=`<div class="fi">${ic('file')}<div><b>${esc(imp.file.name)}</b><small>${fsize(imp.file.size)}</small></div><button class="btn" data-a="impclr">Trocar arquivo</button></div>
    ${imp.wb.SheetNames.length>1?`<div class="fld"><label for="impSheet">Planilha</label><select id="impSheet">${imp.wb.SheetNames.map(n=>`<option ${n===imp.sheet?'selected':''}>${esc(n)}</option>`).join('')}</select></div>`:''}
    <div class="chips" style="margin-bottom:12px">${bdg(st.rows.toLocaleString('pt-BR')+' linhas','pri')}${bdg(st.cols+' colunas')}${bdg(st.empty+'% de células vazias',st.empty>=20?'warn':'')}${bdg(st.dup+(st.dup===1?' linha duplicada':' linhas duplicadas'),st.dup?'warn':'')}</div>
    <div class="tw"><table class="pv"><tr>${Array.from({length:mx},(_,j)=>`<th>${esc(hd[j]||'Coluna '+(j+1))}</th>`).join('')}</tr>${pv.map(r=>`<tr>${Array.from({length:mx},(_,j)=>`<td>${esc(r[j])}</td>`).join('')}</tr>`).join('')}</table></div>
    <p class="sub" style="font-size:12.5px;margin-top:8px">Prévia das ${pv.length} primeiras linhas${st.cols>mx?` e das ${mx} primeiras colunas`:''}.</p>`;
  }
  o.innerHTML=`<div class="card modal" role="dialog" aria-modal="true" aria-labelledby="impT">
    <div class="ch"><div><h3 id="impT">Importar arquivo</h3><p>Envie uma planilha para iniciar uma nova versão do dataset</p></div><button class="ib" data-a="impx" aria-label="Fechar">${ic('x')}</button></div>
    <div class="fld"><label for="impSec">Secretaria de destino</label><select id="impSec" ${adm()?'':'disabled'}>${secs.map(x=>`<option value="${x.id}" ${x.id===imp.sec?'selected':''}>${x.n}</option>`).join('')}</select></div>
    ${body}
    <input type="file" id="impFile" accept=".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv" hidden>
    ${imp.err?`<p class="er" role="alert">${imp.err}</p>`:''}
    <div class="mf"><button class="btn" data-a="impx">Cancelar</button><button class="btn p" data-a="impok" ${imp.file?'':'disabled'}>${imp.file?`Importar ${st.rows.toLocaleString('pt-BR')} linhas`:'Importar'}</button></div>
  </div>`;
  const f=imp.file?$('#impSec'):$('#impDrop');if(f)f.focus();
}
function doImport(){
  if(!imp||!imp.file)return;
  const s=SEC.find(x=>x.id===imp.sec),n=Math.max(...PASS.map(r=>+r[0].slice(1)))+1;
  PASS.unshift(['v'+n,s.id,`Importação de ${imp.file.name} (${imp.st.rows.toLocaleString('pt-BR')} linhas)`,NAMES[role],new Date().toLocaleDateString('pt-BR')]);
  s.upd='hoje';
  closeImp();toast(`Arquivo importado para ${s.n} · nova versão v${n}`);render();
}
document.addEventListener('keydown',e=>{
  if(!imp)return;
  if(e.key==='Escape')closeImp();
  else if((e.key==='Enter'||e.key===' ')&&e.target.dataset.a==='impPick'){e.preventDefault();$('#impFile').click()}
});
['dragover','dragleave','drop'].forEach(t=>document.addEventListener(t,e=>{
  if(!imp||!e.target.closest||!e.target.closest('.modal'))return;
  e.preventDefault();const d=$('#impDrop');
  if(t==='dragover'&&d)d.classList.add('on');else if(d)d.classList.remove('on');
  if(t==='drop')loadFile(e.dataTransfer.files[0]);
}));

document.addEventListener('click',e=>{
  const el=e.target.closest('[data-a]');if(!el)return;
  const a=el.dataset.a,id=el.dataset.id;
  if(a==='nav'){if(id==='secretaria')cur=adm()?cur:role;go(id)}
  else if(a==='sec'){cur=id;go('secretaria')}
  else if(a==='mf'){mf=id;render()}
  else if(a==='sug'){dec[id]=el.dataset.d;toast(el.dataset.d==='ok'?'Sugestão aprovada e enviada à mineração':'Sugestão rejeitada');render()}
  else if(a==='pub'){const s=SEC.find(s=>s.id===id);if(!s||!mine(s)||s.score<LIM)return;if(openPublication(s)){s.pub=true;toast('Publicação simulada aberta em nova aba');render()}}
  else if(a==='rev'){grants.splice(+id,1);toast('Acesso revogado');render()}
  else if(a==='grant'){const f=$('#gf').value,t=$('#gt').value;if(f===t){toast('Escolha secretarias diferentes');return}grants.push({f,t,by:'Admin (STI)',until:'—'});toast('Acesso concedido');render()}
  else if(a==='imp')openImp()
  else if(a==='impx')closeImp()
  else if(a==='impbg'){if(e.target===el)closeImp()}
  else if(a==='impPick')$('#impFile').click()
  else if(a==='impclr'){imp.file=null;imp.err='';drawImp()}
  else if(a==='impok')doImport()
  else if(a==='theme'){const r=document.documentElement,d=r.dataset.theme?r.dataset.theme==='dark':matchMedia('(prefers-color-scheme:dark)').matches;r.dataset.theme=d?'light':'dark';render()}
  else if(a==='menu'){const ap=$('#app');matchMedia('(max-width:860px)').matches?ap.classList.toggle('open'):ap.classList.toggle('min')}
});
document.addEventListener('change',e=>{
  if(e.target.id==='impFile'){loadFile(e.target.files[0]);return}
  if(e.target.id==='impSec'){imp.sec=e.target.value;return}
  if(e.target.id==='impSheet'){setSheet(e.target.value);drawImp();return}
  if(e.target.id==='role'){role=e.target.value;mf='all';if(!adm())cur=role;render()}});
