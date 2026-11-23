# Marília DataHub

O Marília DataHub reúne catálogo, qualidade de dados, revisão de sugestões e publicação no portal de demonstração. O FastAPI serve o login, o painel HTML e a API. O Supabase autentica os usuários e guarda os cinco datasets e o gabarito de acurácia.

## Organização

| Pasta ou arquivo | Responsabilidade |
|---|---|
| `app/main.py` | Rotas FastAPI, autenticação e permissões por secretaria |
| `app/quality.py` e `app/processing.py` | Diagnóstico, scores, processamento e critérios de publicação |
| `app/store.py` e `app/postgres.py` | Persistência e conexões PostgreSQL |
| `app/demo_reference.py` | Consulta e comparação com a referência de acurácia |
| `app/web/templates/` | HTML do login, do painel e do portal |
| `app/web/assets/` | CSS, componentes do painel e integração JavaScript com a API |
| `supabase/migrations/` | Estrutura SQL das tabelas, funções e permissões |
| `scripts/` | Verificação da carga do Supabase pelo pool |
| `tests/` | Testes locais com dados de teste isolados |
| `pyproject.toml` e `vercel.json` | Entrada FastAPI e inclusão dos arquivos web no deploy |

## Rodar localmente

Use Python 3.12. No PowerShell, abra a raiz do repositório e execute:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Preencha o `.env` com a URL do projeto Supabase, a chave Publishable e a URI do pool. Use `COOKIE_SECURE=false` no teste HTTP local. Depois, execute:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_supabase_pool
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8019
```

Abra [a tela de login local](http://127.0.0.1:8019/login). Use uma conta do Supabase Auth já habilitada no DataHub. A configuração de cada conta usa `app_metadata.datahub_role`. Os papéis são `admin`, `saude`, `educacao`, `assistencia` e `ti`.

## Publicar no GitHub e Vercel

1. Envie o conteúdo desta pasta para a raiz do repositório GitHub. Confira que `.env.example` está presente e que o `.env` ficou fora do commit.
2. Em **Vercel → Add New → Project**, importe o repositório GitHub e selecione **FastAPI** se o framework ainda não estiver detectado. A raiz do projeto é a pasta que contém `requirements.txt` e `vercel.json`. Deixe os comandos de build no padrão do framework.
3. Configure as variáveis abaixo em **Settings → Environment Variables** para Production. Use a URI do **Transaction pooler**, porta `6543`, copiada da janela **Connect** do Supabase. Preencha a senha do banco e use TLS. Armazene a URI como segredo do projeto. O driver desabilita prepared statements para compatibilidade com esse pool. [Modos de conexão do Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres) · [Variáveis no Vercel](https://vercel.com/docs/environment-variables)
4. Implante e confirme que `/health` responde com `status: ok` e `mode: supabase`. Abra `/login`, entre com a conta que já usa no Supabase e confira os cinco datasets, os 1.120 registros, a cobertura do gabarito e o portal de demonstração. [FastAPI no Vercel](https://vercel.com/docs/frameworks/backend/fastapi)

| Variável | Valor no Vercel |
|---|---|
| `DATAHUB_MODE` | `supabase` |
| `SUPABASE_URL` | URL do projeto Supabase já utilizado |
| `SUPABASE_PUBLISHABLE_KEY` | Chave Publishable do mesmo projeto |
| `SUPABASE_DATABASE_URL` | URI PostgreSQL do Transaction pooler com a senha do banco e `sslmode=require` |
| `COOKIE_SECURE` | `true` |

## Dados e segurança

Use o projeto Supabase que já contém a carga. O repositório traz as migrações de esquema para instalações novas. A carga anterior, o gabarito e os backups ficam no Supabase ou no seu ambiente privado, conforme a origem. A pasta de entrega contém somente código, HTML, configuração sem valores e dados mínimos de teste.

As rotas de consulta do painel exigem sessão Supabase Auth. O backend aplica as permissões antes de devolver dados. As rotas `/public/` servem os datasets liberados pelo fluxo de publicação. Ao implantar usando o mesmo banco, publicações já ativas ficam disponíveis no domínio hospedado.

No Vercel, o tamanho padrão do corpo de uma requisição é 4,5 MB, incluindo o formulário de upload. A demonstração de 1.120 registros cabe no fluxo atual. Para arquivos maiores, o limite da plataforma pode ser atingido antes do limite local. [Limites do Vercel](https://vercel.com/docs/functions/limitations)

## Testes

Com o ambiente virtual preparado, rode:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
