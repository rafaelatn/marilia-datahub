-- One immutable reference document per dataset and reference release.
create table if not exists public.datahub_accuracy_reference (
  reference_id text not null,
  dataset_id text not null,
  records jsonb not null check (jsonb_typeof(records) = 'array'),
  primary key (reference_id, dataset_id)
);
alter table public.datahub_accuracy_reference enable row level security;
revoke all on public.datahub_accuracy_reference from public, anon, authenticated, service_role;
grant select on public.datahub_accuracy_reference to service_role;

-- Archive the state replaced by the full demo load. Accessible to database admins.
create table if not exists public.datahub_state_import_backup (
  backup_id bigint generated always as identity primary key,
  saved_at timestamptz not null default now(),
  revision bigint not null,
  document jsonb not null
);
alter table public.datahub_state_import_backup enable row level security;
revoke all on public.datahub_state_import_backup from public, anon, authenticated, service_role;
