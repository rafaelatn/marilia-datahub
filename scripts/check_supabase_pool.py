"""Confirm access and report field conformity for each loaded dataset."""
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
        for dataset in datasets:
            version=dataset['versions'][-1]
            metric=dataset_quality(dataset,version['rows'],version)['dimensions']['conformity']
            print(f"{dataset['name']}: {len(version['rows'])} registros, "
                  f"{metric['valid']}/{metric['checked']} campos conformes")
    except HTTPException as exc:
        raise SystemExit(exc.detail) from None
    print(f'Pool confirmado. Datasets disponíveis: {len(datasets)}.')


if __name__=='__main__':
    main()
