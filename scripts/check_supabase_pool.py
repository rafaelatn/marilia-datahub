"""Confirm the imported state and reference counts through the PostgreSQL pool."""
from fastapi import HTTPException

from app import store
from app.processing import dataset_quality


def main():
    if store.demo() or not store.database_url():
        raise SystemExit('Configure DATAHUB_MODE=supabase e SUPABASE_DATABASE_URL no .env.')
    if not store.auth_api_key():
        raise SystemExit('Configure também a chave de API para o login pelo Supabase Auth.')
    try:
        datasets=store.read()['datasets']
        total=matched=references=0
        for dataset in datasets:
            version=dataset['versions'][-1]
            rows=version['rows']
            metric=dataset_quality(dataset,rows,version)['dimensions']['accuracy']
            total+=len(rows)
            references+=metric.get('reference_records',0)
            matched+=metric.get('matched_records',0)
            print(f"{dataset['name']}: {len(rows)} registros, {metric.get('matched_records',0)} correspondências")
    except HTTPException as exc:
        raise SystemExit(exc.detail) from None
    if (len(datasets),total,references,matched)!=(5,1120,1120,1120):
        raise SystemExit(f'Conexão ativa, mas a carga diverge: {len(datasets)} datasets, '
                         f'{total} registros, {references} fichas e {matched} correspondências.')
    print('Pool confirmado: 5 datasets, 1.120 registros e 1.120 fichas correspondentes.')


if __name__=='__main__':
    main()
