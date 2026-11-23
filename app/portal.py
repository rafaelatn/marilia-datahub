"""Portal de publicação com o CSS e a estrutura visual do HTML recebido."""
from html import escape as esc
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from app.store import ROOT
from app.processing import PUBLICATION_MIN_SCORE

def render(d,v,secretarias):
    prefix=(ROOT/'app/web/templates/portal-header.html').read_text(encoding='utf-8')
    name=esc(d['name']);sec=esc(next(s['n'] for s in secretarias if s['id']==d['sec']))
    prefix=re.sub(r'<title>.*?</title>',f'<title>{name} · Portal de Dados Abertos</title>',prefix)
    cols=[c['nome_coluna'] for c in d['dictionary']]
    rows=v['rows'];count=len(rows);score=v['quality']['score']
    units={r[c] for r in rows for c in ('unidade','escola','cras','secretaria') if r.get(c)}
    dates=sorted({str(r.get('data_referencia',r.get('ano_letivo',''))) for r in rows})
    period=esc((dates[0]+' a '+dates[-1]) if dates else 'Não informado')
    preview='<table><thead><tr>'+''.join(f'<th>{esc(c)}</th>' for c in cols)+'</tr></thead><tbody>'
    preview+=''.join('<tr>'+''.join(f'<td>{esc(str(r.get(c) if r.get(c) is not None else "—"))}</td>' for c in cols)+'</tr>' for r in rows[:24])+'</tbody></table>'
    resources=''.join(f'<div class="res"><div class="format">{fmt.upper()}</div><div style="flex:1"><b>{name}</b><small>{fmt.upper()} · {count} registros processados</small></div><a class="btn" href="/public/{d["id"]}/download?format={fmt}" download="{d["id"]}.{fmt}">Baixar {fmt.upper()} ↓</a></div>' for fmt in ('csv','json'))
    metadata=[('Organização responsável','Secretaria de '+sec),('Identificador',esc(d['id'])),('Visibilidade','Público'),('Licença','Não informada'),('Frequência',esc(d.get('periodicity') or 'Não informada')),('Período dos dados',period),('Publicação local em',esc(d.get('published_at',''))),('Origem','Marília DataHub · dados processados · planilha e lote sintético')]
    metrics=[]
    for label,value in zip(['Completude','Acurácia','Consistência','Validade'],v['quality']['metrics']):
        if label=='Acurácia' and v['quality']['dimensions']['accuracy'].get('reference'):
            label='Acurácia (referência sintética)'
        display='Sem referência' if value is None else value
        bar='' if value is None else f'<div class="bar"><i style="width:{value}%"></i></div>'
        metrics.append(f'<div style="margin-bottom:12px"><div style="display:flex;justify-content:space-between;margin-bottom:5px"><span class="sub">{label}</span><b>{display}</b></div>{bar}</div>')
    return prefix+f'''<header class="portal-top"><div class="logo">MD</div><div><b>Marília · Dados Abertos</b><div class="sub">Catálogo público de dados · CKAN</div></div><span class="sp"></span><span class="b pri">Demonstração local</span></header>
<main class="portal"><div class="sub">Início / Organizações / {sec} / Conjunto de dados</div>
<section class="hero"><div class="label">SECRETARIA DE {sec.upper()}</div><h1>{name}</h1><p>Indicadores agregados fornecidos ao projeto e registros sintéticos, organizados conforme o dicionário desta base.</p><span class="b" style="background:#fff;color:#15803d;border:0">✓ Publicado no portal local</span> <span class="b" style="color:white;border-color:#ffffff50">Acesso público</span></section>
<div class="note"><span>ⓘ</span><span><b>Portal demonstrativo.</b> Estrutura do protótipo CKAN original, com os dados do projeto. Somente registros processados estão disponíveis. Nenhum envio ao CKAN externo foi realizado.</span></div>
<div class="layout"><div><div class="stats"><div class="card"><span class="sub">Qualidade dos dados</span><strong style="color:var(--ok)">{score} <small style="font-size:13px;color:var(--mut)">/ 100</small></strong><span class="sub">Limiar de publicação atingido</span></div><div class="card"><span class="sub">Recursos disponíveis</span><strong>2</strong><span class="sub">CSV e JSON</span></div><div class="card"><span class="sub">Cobertura dos dados</span><strong>{len(units)} unidades</strong><span class="sub">{count} registros processados</span></div></div>
<section class="card cp"><div class="ch"><div><h3>Dados e recursos</h3><p>Arquivos para consulta e reutilização</p></div></div>{resources}</section>
<section class="card cp" style="margin-top:20px"><div class="ch"><div><h3>Prévia dos dados</h3><p>{min(count,24)} de {count} registros · {period}</p></div><span class="b pri">CSV</span></div><div class="tw">{preview}</div><p class="sub" style="font-size:12px;margin-top:12px">Campos conforme o dicionário da base. Somente valores agregados, sem identificação de pessoas.</p></section>
<section class="card cp" style="margin-top:20px"><div class="ch"><h3>Sobre este conjunto de dados</h3></div><p>{name} · dados atuais. Publicação do subconjunto processado e validado; registros brutos continuam no painel interno.</p><div class="chips" style="margin:12px 0 0"><span class="b">{sec}</span><span class="b">dados processados</span><span class="b">Marília</span></div></section></div>
<aside><section class="card cp"><div class="ch"><h3>Informações da publicação</h3></div><dl class="metadata">{''.join(f'<dt>{a}</dt><dd>{b}</dd>' for a,b in metadata)}</dl></section><section class="card cp" style="margin-top:20px"><h3 style="font-size:15px;margin:0 0 14px">Qualidade na publicação</h3>{''.join(metrics)}<p class="sub" style="font-size:12px;margin-top:14px">Score global: média das métricas medidas. Mínimo exigido: {PUBLICATION_MIN_SCORE}/100.</p></section></aside></div><footer class="foot">Marília DataHub · Representação visual de publicação no CKAN · Projeto demonstrativo</footer></main></body></html>'''
