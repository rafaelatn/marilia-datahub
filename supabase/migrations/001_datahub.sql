-- Migração aditiva. Não execute o SQL original com DROP TABLE no seu projeto.
-- Documento transacional versionado: preserva entidades, linhas, versões e auditoria.
create table if not exists public.datahub_state (
  id integer primary key check (id = 1),
  revision bigint not null default 0,
  document jsonb not null check (jsonb_typeof(document) = 'object'),
  updated_at timestamptz not null default now()
);
alter table public.datahub_state enable row level security;
revoke all on public.datahub_state from anon, authenticated;
grant all on public.datahub_state to service_role;

-- Compare-and-swap: impede sobrescrita concorrente entre processos FastAPI.
create or replace function public.datahub_save(payload jsonb, expected_revision bigint)
returns boolean language plpgsql security invoker set search_path = public as $$
begin
  if expected_revision = -1 then
    insert into public.datahub_state(id,revision,document)
      values (1,0,jsonb_set(payload,'{revision}','0')) on conflict do nothing;
    return found;
  end if;
  update public.datahub_state set revision=expected_revision+1,
    document=jsonb_set(payload,'{revision}',to_jsonb(expected_revision+1)),updated_at=now()
    where id=1 and revision=expected_revision;
  return found;
end $$;
revoke all on function public.datahub_save(jsonb,bigint) from public,anon,authenticated;
grant execute on function public.datahub_save(jsonb,bigint) to service_role;
