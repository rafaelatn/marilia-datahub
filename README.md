# Marília DataHub

O Marília DataHub é um projeto acadêmico para importar, padronizar, validar e publicar dados das secretarias municipais. O sistema mede a **conformidade estrutural** das planilhas e usa o modelo multilíngue **MiniLM** para sugerir correções em valores textuais.

Os esquemas iniciais cobrem cinco bases municipais: atendimentos nas UBS, vacinação nas UBS, matrículas por escola, famílias cadastradas nos CRAS e chamados de suporte de TI.

## Como funciona

1. **Importação.** A secretaria envia uma planilha CSV ou XLSX. O sistema associa os cabeçalhos às colunas do esquema pelo nome, por nomes alternativos ou por similaridade de escrita com RapidFuzz.
2. **Validação.** O sistema aplica as regras da base, registra o diagnóstico inicial e encaminha as pendências para a fila de sugestões.
3. **Revisão.** O responsável analisa as correções propostas e pode aprová-las ou rejeitá-las. Uma correção aprovada gera uma nova versão e atualiza a conformidade. O histórico fica disponível no **Data Passport**.
4. **Publicação.** A secretaria pode publicar registros processados no portal demonstrativo quando eles atendem aos critérios de qualidade e acesso público. O sistema verifica a classificação da base, a ausência de dados pessoais, o limite mínimo de **95% de conformidade** e as pendências de validação.

## Conformidade estrutural

O painel apresenta os resultados atuais da planilha em dois cartões:

| Indicador | Como é calculado |
| --- | --- |
| **Campos no padrão** | Campos que atendem ao esquema ÷ campos previstos nas linhas avaliadas. Campos opcionais podem estar vazios. |
| **Linhas no padrão** | Linhas com campos conformes e sem repetição da chave de identificação ÷ linhas avaliadas. |

A seção **Na importação → Hoje** compara a mesma carga em dois momentos e mostra a variação dos campos em pontos percentuais. Para cargas antigas sem diagnóstico inicial registrado, o painel apresenta a situação atual. Os cartões **Ainda em tratamento** e **Já processados** mostram a conformidade de cada grupo no momento da consulta.

Em **Ver detalhes da validação**, é possível conferir o preenchimento obrigatório, a repetição de chaves, a validade dos valores preenchidos e a versão das regras aplicadas. A conferência da veracidade dos valores depende de fontes oficiais por base.

### Regras de validação por base

O arquivo [`app/schemas.json`](app/schemas.json) define a versão, a chave de identificação e as colunas de cada base. Cada coluna pode ter nome, aliases, tipo, formato, obrigatoriedade, valor mínimo e categorias permitidas.

Ao alterar as regras, incremente `versao` no esquema correspondente. As novas importações usam a configuração atualizada. Cada carga mantém o esquema utilizado no diagnóstico e no tratamento de suas versões.

## Sugestões com inteligência artificial

O modelo multilíngue `paraphrase-multilingual-MiniLM-L12-v2`, da família Sentence Transformers, roda no backend em CPU com ONNX Runtime. Ele analisa valores fora das categorias previstas em colunas com `similaridade_semantica: true` quando a validação por regras fica sem uma correção para sugerir.

O MiniLM representa os textos como vetores (*embeddings*) e compara o valor original com as categorias permitidas por similaridade de cosseno. A melhor opção deve atingir **0,72** e, quando houver outra candidata, superar a segunda por pelo menos **0,025**. A fila mostra o método e a similaridade. A aplicação da correção depende de aprovação humana, e o cálculo da conformidade é feito pelas regras do esquema.

Em um teste sintético, o MiniLM sugeriu **Educação Infantil** para **Pré-escola e creche**, com **81,4% de similaridade**. Depois da aprovação, a conformidade dos campos da carga de teste passou de **83,33% para 100%**.

Na primeira análise com candidatos, o backend baixa os arquivos de uma revisão fixa do modelo e os mantém em cache temporário. A planilha é analisada no backend. `DATAHUB_MODEL_DIR` permite indicar um cache preparado com `tokenizer.json` e `model.onnx`. São avaliados até 64 pares distintos de coluna e valor por importação. Se o modelo estiver indisponível, a importação segue com a validação por regras e registra a falha da análise semântica.

## Estrutura do projeto

| Caminho | Responsabilidade |
| --- | --- |
| [`app/main.py`](app/main.py) | API FastAPI, autenticação e permissões por secretaria |
| [`app/schemas.json`](app/schemas.json) | Esquemas de validação versionados |
| [`app/quality.py`](app/quality.py) | Validação e cálculo da conformidade |
| [`app/semantic.py`](app/semantic.py) | Inferência com MiniLM e sugestões semânticas |
| [`app/web/`](app/web/) | Login, painel e portal demonstrativo em HTML, CSS e JavaScript |
| [`supabase/migrations/`](supabase/migrations/) | Migrações PostgreSQL |
| [`tests/`](tests/) | Testes de aplicação, conformidade e sugestões semânticas |

## Executar localmente

No PowerShell, com **Python 3.12** instalado:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

No `.env`, preencha `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` e `SUPABASE_DATABASE_URL` com os dados do seu projeto Supabase. Mantenha `DATAHUB_MODE=supabase`. Para acesso local via HTTP, use `COOKIE_SECURE=false`. Mantenha o `.env` fora do Git.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8019
```

Abra [a página de login local](http://127.0.0.1:8019/login) com uma conta cadastrada no Supabase Auth. Para executar os testes:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Deploy na Vercel

O projeto usa o GitHub como origem do código e a Vercel para hospedagem. Com a integração Git ativa, o envio de uma branch gera um **Preview**, e o merge na branch de produção inicia o deploy. Configure as variáveis do Supabase no ambiente da Vercel e use `COOKIE_SECURE=true` em produção.

Após o deploy, confira `/health`, o login e a tela de **Conformidade estrutural** de uma base. O portal é demonstrativo e segue a estrutura do CKAN. A integração com uma instância externa fica para uma etapa futura.
