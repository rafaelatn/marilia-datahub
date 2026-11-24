# Marília DataHub

Projeto acadêmico para organizar, avaliar e publicar dados municipais. Os esquemas iniciais cobrem cinco bases de Saúde, Educação, Assistência Social e TI.

## O que o sistema faz

- Organiza as bases por secretaria e permite buscar registros por coluna e por estado: bruto ou processado.
- Mede a conformidade estrutural dos campos e registros. Completude, consistência e validade detalham o diagnóstico.
- Mostra sugestões de correção para aprovação ou rejeição.
- Permite que cada secretaria publique seus próprios dados aptos no portal de demonstração. O administrador gerencia as permissões e pode visualizar o painel como uma secretaria.

## Como o código está organizado

| Pasta | Conteúdo |
| --- | --- |
| `app/` | API em FastAPI, regras de qualidade e conexão com o banco |
| `app/web/` | HTML, CSS e JavaScript do login, do painel e do portal |
| `supabase/migrations/` | Scripts SQL que criam as tabelas |
| `scripts/` | Verificação da conexão e da carga no Supabase |
| `tests/` | Testes do sistema |

## Como rodar

1. Use **Python 3.12** e instale as dependências com `pip install -r requirements.txt`.
2. Copie `.env.example` para `.env` e preencha a URL do Supabase, a chave Publishable e a URL do pool PostgreSQL.
3. Para testar localmente por HTTP, use `COOKIE_SECURE=false`.
4. Rode `python -m uvicorn app.main:app --port 8019` e abra `http://127.0.0.1:8019/login`.

## Conformidade estrutural

Cada entrada em `app/schemas.json` define a versão, a chave de identificação e as colunas do dataset. Configure `nome_coluna`, `aliases`, `tipo_dado` (`texto`, `inteiro`, `decimal` ou `data`), `obrigatoria` e, conforme a coluna, `formato` (regex para texto, strftime para datas), `minimo`, `valores_permitidos`, `aliases_valores` e `formatos_entrada`. Ao alterar o esquema, incremente `versao` e publique a configuração. A nova regra vale para a próxima importação. Cada carga conserva o esquema usado no diagnóstico e no tratamento das suas versões.

O importador resolve nomes e aliases antes de buscar correspondências por similaridade. Arquivos com colunas desconhecidas ou mapeamento ambíguo são recusados. Colunas obrigatórias ausentes geram pendências. As correções de valores são aplicadas mediante aprovação das sugestões.

A nota de cada dataset é o total de campos conformes dividido pelo total de campos previstos nas linhas, multiplicado por 100. Uma célula vazia de coluna opcional é conforme. A conformidade por registro exige campos conformes e ausência de repetição da chave na ordem avaliada. A secretaria usa a média simples das notas dos seus datasets. O painel compara a entrada original com o estado atual e mostra a diferença em pontos percentuais. Cargas antigas sem diagnóstico estrutural inicial exibem o antes como indisponível.

### Sugestões semânticas

Na importação, as colunas com `similaridade_semantica: true` podem receber sugestões para valores fora do domínio que ficaram sem correção determinística. O modelo multilíngue MiniLM usado na P1 roda no backend via ONNX Runtime quantizado em CPU. O sistema sugere a categoria permitida com maior similaridade por cosseno se o resultado atingir 0,72 e, quando houver outra categoria, superá-la por pelo menos 0,025. O diagnóstico registra a execução, e cada sugestão tem o método, a similaridade e permanece sujeita à aprovação humana. A nota de conformidade continua a ser calculada somente pelo esquema.

Na primeira análise com candidatos, o backend obtém os arquivos da revisão fixa do modelo público e os mantém em cache local temporário. Nenhum texto importado é enviado ao servidor de origem do modelo. A função aceita `DATAHUB_MODEL_DIR` para usar um cache previamente preparado com `tokenizer.json` e `model.onnx`. A importação registra indisponibilidade da análise semântica se houver falha no carregamento. Para limitar o custo por arquivo, são avaliados até 64 pares distintos de coluna e valor por importação.
