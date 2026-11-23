# Marília DataHub

Projeto acadêmico para organizar, avaliar e publicar dados municipais. O painel de demonstração usa **1.120 registros sintéticos** em cinco bases de Saúde, Educação, Assistência Social e TI.

## O que o sistema faz

- Organiza as bases por secretaria e permite buscar registros por coluna e por estado: bruto ou processado.
- Calcula a qualidade de cada base em quatro dimensões: completude, acurácia, consistência e validade. A acurácia é medida com um gabarito sintético.
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
