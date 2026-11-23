"""Parameterized PostgreSQL operations through the Supabase connection pooler."""
import os
from atexit import register
from threading import Lock

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout
from fastapi import HTTPException

pool = None
pool_lock = Lock()


def query(dsn, statement, params=()):
    global pool
    try:
        with pool_lock:
            if pool is None:
                options = conninfo_to_dict(dsn)
                sslmode = options.get('sslmode', 'require')
                if sslmode not in ('require', 'verify-ca', 'verify-full'):
                    raise HTTPException(503,'Configure TLS na conexão com o pool do Supabase.')
                pool = ConnectionPool(
                    dsn,kwargs={'sslmode':sslmode,'prepare_threshold':None,'connect_timeout':5},
                    min_size=0,max_size=1 if os.getenv('VERCEL') else 3,timeout=7,open=True,name='datahub',
                )
                register(pool.close)
        with pool.connection() as connection:
            return connection.execute(statement, params).fetchone()
    except (psycopg.Error,PoolTimeout) as exc:
        raise HTTPException(503,'Falha no pool PostgreSQL. Verifique a conexão e a migração do Supabase.') from exc


def read_state(dsn):
    row=query(dsn,'select document from public.datahub_state where id=1')
    return row[0] if row else None


def save_state(dsn, state, expected):
    return query(dsn,'select public.datahub_save(%s,%s)',(Jsonb(state),expected))[0]


def read_reference(dsn, reference_id, dataset_id):
    row=query(dsn,'select records from public.datahub_accuracy_reference where reference_id=%s and dataset_id=%s',
              (reference_id,dataset_id))
    return row[0] if row else None
