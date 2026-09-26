-- SecretariatPro Phase 35
-- Multiempresa, membresías, 4 días offline, retención 2 años y cuenta de prueba asociación.
-- Ejecutar una sola vez en Supabase > SQL Editor con permisos de propietario del proyecto.

begin;

create extension if not exists pgcrypto;

create or replace function public.sp_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.sp_workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(trim(name)) between 2 and 120),
  slug text not null unique,
  workspace_type text not null check (workspace_type in ('personal', 'association')),
  owner_user_id uuid not null references auth.users(id) on delete restrict,
  assignment_mode text not null default 'assigned' check (assignment_mode in ('open', 'assigned')),
  visual_identity_mode text not null default 'single' check (visual_identity_mode in ('single', 'competition')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create table if not exists public.sp_workspace_members (
  workspace_id uuid not null references public.sp_workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner', 'competition_manager', 'producer')),
  status text not null default 'active' check (status in ('invited', 'active', 'suspended')),
  invited_by uuid references auth.users(id) on delete set null,
  joined_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (workspace_id, user_id)
);

create table if not exists public.sp_plans (
  id text primary key,
  name text not null,
  audience text not null check (audience in ('personal', 'association', 'enterprise')),
  entitlements jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.sp_subscriptions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.sp_workspaces(id) on delete cascade,
  plan_id text not null references public.sp_plans(id) on delete restrict,
  status text not null default 'trial' check (status in ('trial', 'active', 'past_due', 'expired', 'suspended', 'cancelled')),
  starts_at timestamptz not null default now(),
  ends_at timestamptz not null,
  retention_until timestamptz,
  offline_grace_days integer not null default 4 check (offline_grace_days between 0 and 30),
  payment_provider text,
  provider_customer_id text,
  provider_subscription_id text unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  cancelled_at timestamptz,
  constraint sp_subscription_dates check (ends_at > starts_at)
);

create table if not exists public.sp_registered_devices (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.sp_workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  device_fingerprint text not null,
  device_name text,
  platform text,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  revoked_at timestamptz,
  unique (workspace_id, device_fingerprint)
);

create table if not exists public.sp_active_sessions (
  id uuid primary key default gen_random_uuid(),
  device_id uuid not null references public.sp_registered_devices(id) on delete cascade,
  workspace_id uuid not null references public.sp_workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  application text not null check (application in ('secretariatpro', 'manager')),
  match_id uuid,
  started_at timestamptz not null default now(),
  heartbeat_at timestamptz not null default now(),
  ended_at timestamptz
);

create table if not exists public.sp_tablet_sessions (
  id uuid primary key default gen_random_uuid(),
  host_session_id uuid not null references public.sp_active_sessions(id) on delete cascade,
  token_hash text not null unique,
  connected_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  expires_at timestamptz not null
);

create table if not exists public.sp_visual_themes (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.sp_workspaces(id) on delete cascade,
  competition_id uuid,
  name text not null default 'Identidad principal',
  config jsonb not null default '{}'::jsonb,
  version integer not null default 1,
  published boolean not null default false,
  locked boolean not null default true,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists sp_visual_themes_scope_unique
on public.sp_visual_themes(workspace_id, coalesce(competition_id, '00000000-0000-0000-0000-000000000000'::uuid), version);

create table if not exists public.sp_import_jobs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.sp_workspaces(id) on delete cascade,
  created_by uuid not null references auth.users(id) on delete cascade,
  source_type text not null check (source_type in ('xlsx', 'csv')),
  import_scope text[] not null default array[]::text[],
  original_filename text not null,
  storage_path text,
  status text not null default 'uploaded' check (status in ('uploaded', 'analysing', 'review', 'importing', 'completed', 'failed', 'cancelled')),
  column_mapping jsonb not null default '{}'::jsonb,
  summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists public.sp_import_rows (
  id bigserial primary key,
  import_job_id uuid not null references public.sp_import_jobs(id) on delete cascade,
  sheet_name text,
  row_number integer not null,
  entity_type text not null check (entity_type in ('competition', 'team', 'player', 'coach', 'roster', 'producer', 'match', 'result', 'event', 'visual_identity')),
  source_data jsonb not null default '{}'::jsonb,
  normalized_data jsonb not null default '{}'::jsonb,
  status text not null default 'pending' check (status in ('pending', 'valid', 'warning', 'error', 'imported', 'skipped')),
  messages jsonb not null default '[]'::jsonb
);

create index if not exists sp_members_user_idx on public.sp_workspace_members(user_id, status);
create index if not exists sp_subscriptions_workspace_idx on public.sp_subscriptions(workspace_id, ends_at desc);
create index if not exists sp_sessions_workspace_idx on public.sp_active_sessions(workspace_id, heartbeat_at desc) where ended_at is null;
create index if not exists sp_import_jobs_workspace_idx on public.sp_import_jobs(workspace_id, created_at desc);

create or replace function public.sp_subscription_retention()
returns trigger
language plpgsql
as $$
begin
  if new.retention_until is null then
    new.retention_until := new.ends_at + interval '2 years';
  end if;
  return new;
end;
$$;

drop trigger if exists sp_workspaces_updated_at on public.sp_workspaces;
create trigger sp_workspaces_updated_at before update on public.sp_workspaces
for each row execute function public.sp_set_updated_at();

drop trigger if exists sp_members_updated_at on public.sp_workspace_members;
create trigger sp_members_updated_at before update on public.sp_workspace_members
for each row execute function public.sp_set_updated_at();

drop trigger if exists sp_plans_updated_at on public.sp_plans;
create trigger sp_plans_updated_at before update on public.sp_plans
for each row execute function public.sp_set_updated_at();

drop trigger if exists sp_subscriptions_updated_at on public.sp_subscriptions;
create trigger sp_subscriptions_updated_at before update on public.sp_subscriptions
for each row execute function public.sp_set_updated_at();

drop trigger if exists sp_subscriptions_retention on public.sp_subscriptions;
create trigger sp_subscriptions_retention before insert or update of ends_at, retention_until on public.sp_subscriptions
for each row execute function public.sp_subscription_retention();

drop trigger if exists sp_visual_themes_updated_at on public.sp_visual_themes;
create trigger sp_visual_themes_updated_at before update on public.sp_visual_themes
for each row execute function public.sp_set_updated_at();

drop trigger if exists sp_import_jobs_updated_at on public.sp_import_jobs;
create trigger sp_import_jobs_updated_at before update on public.sp_import_jobs
for each row execute function public.sp_set_updated_at();

insert into public.sp_plans(id, name, audience, entitlements)
values
  ('personal', 'Particular', 'personal', '{"max_computers":2,"tablets_count":false,"max_producers":1,"visual_identity_mode":"single","bulk_import":true,"offline_grace_days":4}'::jsonb),
  ('association', 'Asociación', 'association', '{"max_computers":null,"tablets_count":false,"max_producers":null,"visual_identity_mode":"competition","bulk_import":true,"offline_grace_days":4}'::jsonb),
  ('association_test', 'Asociación de pruebas', 'association', '{"max_computers":25,"tablets_count":false,"max_producers":25,"visual_identity_mode":"competition","bulk_import":true,"ai_import":true,"offline_grace_days":4}'::jsonb)
on conflict (id) do update set
  name = excluded.name,
  audience = excluded.audience,
  entitlements = excluded.entitlements,
  active = true;

-- Helpers RLS. SECURITY DEFINER evita recursión al comprobar miembros.
create or replace function public.sp_is_workspace_member(target_workspace uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.sp_workspace_members m
    where m.workspace_id = target_workspace
      and m.user_id = auth.uid()
      and m.status = 'active'
  );
$$;

create or replace function public.sp_has_workspace_role(target_workspace uuid, accepted_roles text[])
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.sp_workspace_members m
    where m.workspace_id = target_workspace
      and m.user_id = auth.uid()
      and m.status = 'active'
      and m.role = any(accepted_roles)
  );
$$;

grant execute on function public.sp_is_workspace_member(uuid) to authenticated;
grant execute on function public.sp_has_workspace_role(uuid, text[]) to authenticated;

alter table public.sp_workspaces enable row level security;
alter table public.sp_workspace_members enable row level security;
alter table public.sp_plans enable row level security;
alter table public.sp_subscriptions enable row level security;
alter table public.sp_registered_devices enable row level security;
alter table public.sp_active_sessions enable row level security;
alter table public.sp_tablet_sessions enable row level security;
alter table public.sp_visual_themes enable row level security;
alter table public.sp_import_jobs enable row level security;
alter table public.sp_import_rows enable row level security;

drop policy if exists sp_workspaces_read on public.sp_workspaces;
create policy sp_workspaces_read on public.sp_workspaces for select to authenticated
using (public.sp_is_workspace_member(id));

drop policy if exists sp_workspaces_manage on public.sp_workspaces;
create policy sp_workspaces_manage on public.sp_workspaces for update to authenticated
using (public.sp_has_workspace_role(id, array['owner','competition_manager']))
with check (public.sp_has_workspace_role(id, array['owner','competition_manager']));

drop policy if exists sp_members_read on public.sp_workspace_members;
create policy sp_members_read on public.sp_workspace_members for select to authenticated
using (user_id = auth.uid() or public.sp_has_workspace_role(workspace_id, array['owner','competition_manager']));

drop policy if exists sp_members_manage on public.sp_workspace_members;
create policy sp_members_manage on public.sp_workspace_members for all to authenticated
using (public.sp_has_workspace_role(workspace_id, array['owner','competition_manager']))
with check (public.sp_has_workspace_role(workspace_id, array['owner','competition_manager']));

drop policy if exists sp_plans_read on public.sp_plans;
create policy sp_plans_read on public.sp_plans for select to authenticated using (active = true);

drop policy if exists sp_subscriptions_read on public.sp_subscriptions;
create policy sp_subscriptions_read on public.sp_subscriptions for select to authenticated
using (public.sp_is_workspace_member(workspace_id));

drop policy if exists sp_devices_own on public.sp_registered_devices;
create policy sp_devices_own on public.sp_registered_devices for all to authenticated
using (user_id = auth.uid() and public.sp_is_workspace_member(workspace_id))
with check (user_id = auth.uid() and public.sp_is_workspace_member(workspace_id));

drop policy if exists sp_sessions_own on public.sp_active_sessions;
create policy sp_sessions_own on public.sp_active_sessions for all to authenticated
using (user_id = auth.uid() and public.sp_is_workspace_member(workspace_id))
with check (user_id = auth.uid() and public.sp_is_workspace_member(workspace_id));

drop policy if exists sp_tablet_host on public.sp_tablet_sessions;
create policy sp_tablet_host on public.sp_tablet_sessions for all to authenticated
using (exists(select 1 from public.sp_active_sessions s where s.id = host_session_id and s.user_id = auth.uid()))
with check (exists(select 1 from public.sp_active_sessions s where s.id = host_session_id and s.user_id = auth.uid()));

drop policy if exists sp_themes_read on public.sp_visual_themes;
create policy sp_themes_read on public.sp_visual_themes for select to authenticated
using (public.sp_is_workspace_member(workspace_id));

drop policy if exists sp_themes_manage on public.sp_visual_themes;
create policy sp_themes_manage on public.sp_visual_themes for all to authenticated
using (public.sp_has_workspace_role(workspace_id, array['owner','competition_manager']))
with check (public.sp_has_workspace_role(workspace_id, array['owner','competition_manager']));

drop policy if exists sp_imports_read on public.sp_import_jobs;
create policy sp_imports_read on public.sp_import_jobs for select to authenticated
using (public.sp_is_workspace_member(workspace_id));

drop policy if exists sp_imports_manage on public.sp_import_jobs;
create policy sp_imports_manage on public.sp_import_jobs for all to authenticated
using (public.sp_has_workspace_role(workspace_id, array['owner','competition_manager']))
with check (public.sp_has_workspace_role(workspace_id, array['owner','competition_manager']) and created_by = auth.uid());

drop policy if exists sp_import_rows_access on public.sp_import_rows;
create policy sp_import_rows_access on public.sp_import_rows for all to authenticated
using (exists(select 1 from public.sp_import_jobs j where j.id = import_job_id and public.sp_is_workspace_member(j.workspace_id)))
with check (exists(select 1 from public.sp_import_jobs j where j.id = import_job_id and public.sp_has_workspace_role(j.workspace_id, array['owner','competition_manager'])));

-- Añade el tenant a las tablas deportivas ya existentes.
do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'seasons','competitions','teams','players','rosters','matches',
    'match_players','match_events','scoreboard_operators'
  ] loop
    if to_regclass('public.' || table_name) is not null then
      execute format(
        'alter table public.%I add column if not exists workspace_id uuid references public.sp_workspaces(id) on delete cascade',
        table_name
      );
      execute format('create index if not exists %I on public.%I(workspace_id)', 'sp_' || table_name || '_workspace_idx', table_name);
    end if;
  end loop;
end $$;

-- Cuenta solicitada: cualquier email cuyo comienzo sea a.garciarenones.
-- Se crea como propietaria de una asociación de pruebas con acceso activo.
do $$
declare
  target_user uuid;
  target_email text;
  target_workspace uuid;
begin
  select id, email into target_user, target_email
  from auth.users
  where lower(email) like 'a.garciarenones%'
  order by created_at
  limit 1;

  if target_user is null then
    raise notice 'No se encontró una cuenta cuyo email empiece por a.garciarenones. Créala primero y vuelve a ejecutar este bloque.';
    return;
  end if;

  insert into public.sp_workspaces(name, slug, workspace_type, owner_user_id, assignment_mode, visual_identity_mode)
  values ('Asociación de pruebas', 'a-garciarenones-asociacion', 'association', target_user, 'open', 'competition')
  on conflict (slug) do update set
    owner_user_id = excluded.owner_user_id,
    workspace_type = 'association',
    assignment_mode = 'open',
    visual_identity_mode = 'competition',
    deleted_at = null
  returning id into target_workspace;

  insert into public.sp_workspace_members(workspace_id, user_id, role, status, invited_by)
  values (target_workspace, target_user, 'owner', 'active', target_user)
  on conflict (workspace_id, user_id) do update set role = 'owner', status = 'active';

  insert into public.sp_subscriptions(
    workspace_id, plan_id, status, starts_at, ends_at, offline_grace_days,
    payment_provider, provider_customer_id, provider_subscription_id
  )
  values (
    target_workspace, 'association_test', 'active', now(), now() + interval '1 year', 4,
    'manual_test', target_email, 'test-a-garciarenones'
  )
  on conflict (provider_subscription_id) do update set
    workspace_id = excluded.workspace_id,
    plan_id = excluded.plan_id,
    status = 'active',
    starts_at = least(public.sp_subscriptions.starts_at, now()),
    ends_at = now() + interval '1 year',
    retention_until = now() + interval '3 years',
    offline_grace_days = 4;

  -- Los datos deportivos actuales pasan a pertenecer a la asociación de prueba.
  if to_regclass('public.seasons') is not null then execute 'update public.seasons set workspace_id = $1 where workspace_id is null' using target_workspace; end if;
  if to_regclass('public.competitions') is not null then execute 'update public.competitions set workspace_id = $1 where workspace_id is null' using target_workspace; end if;
  if to_regclass('public.teams') is not null then execute 'update public.teams set workspace_id = $1 where workspace_id is null' using target_workspace; end if;
  if to_regclass('public.players') is not null then execute 'update public.players set workspace_id = $1 where workspace_id is null' using target_workspace; end if;
  if to_regclass('public.rosters') is not null then execute 'update public.rosters set workspace_id = $1 where workspace_id is null' using target_workspace; end if;
  if to_regclass('public.matches') is not null then execute 'update public.matches set workspace_id = $1 where workspace_id is null' using target_workspace; end if;
  if to_regclass('public.match_players') is not null then execute 'update public.match_players set workspace_id = $1 where workspace_id is null' using target_workspace; end if;
  if to_regclass('public.match_events') is not null then execute 'update public.match_events set workspace_id = $1 where workspace_id is null' using target_workspace; end if;
  if to_regclass('public.scoreboard_operators') is not null then execute 'update public.scoreboard_operators set workspace_id = $1 where id = $2' using target_workspace, target_user; end if;

  raise notice 'Acceso asociación concedido a % con workspace %', target_email, target_workspace;
end $$;

-- Aislamiento obligatorio por workspace en las tablas deportivas.
do $$
declare
  table_name text;
  policy_name text;
begin
  foreach table_name in array array[
    'seasons','competitions','teams','players','rosters','matches',
    'match_players','match_events','scoreboard_operators'
  ] loop
    if to_regclass('public.' || table_name) is not null then
      execute format('alter table public.%I enable row level security', table_name);
      policy_name := 'sp_tenant_guard_' || table_name;
      execute format('drop policy if exists %I on public.%I', policy_name, table_name);
      execute format(
        'create policy %I on public.%I as restrictive for all to authenticated using (public.sp_is_workspace_member(workspace_id)) with check (public.sp_is_workspace_member(workspace_id))',
        policy_name, table_name
      );
      policy_name := 'sp_member_read_' || table_name;
      execute format('drop policy if exists %I on public.%I', policy_name, table_name);
      execute format(
        'create policy %I on public.%I for select to authenticated using (public.sp_is_workspace_member(workspace_id))',
        policy_name, table_name
      );
    end if;
  end loop;
end $$;

-- Escritura estructural: propietarios y gestores de competición.
do $$
declare
  table_name text;
  policy_name text;
begin
  foreach table_name in array array['seasons','competitions','teams','players','rosters','scoreboard_operators'] loop
    if to_regclass('public.' || table_name) is not null then
      policy_name := 'sp_manager_write_' || table_name;
      execute format('drop policy if exists %I on public.%I', policy_name, table_name);
      execute format(
        'create policy %I on public.%I for all to authenticated using (public.sp_has_workspace_role(workspace_id, array[''owner'',''competition_manager''])) with check (public.sp_has_workspace_role(workspace_id, array[''owner'',''competition_manager'']))',
        policy_name, table_name
      );
    end if;
  end loop;
end $$;

-- En la primera fase, miembros activos pueden operar partidos y actas dentro de su tenant.
-- La restricción abierta/asignada se aplica ya en SecretariatPro y se endurecerá en una RPC de sesión.
do $$
declare
  table_name text;
  policy_name text;
begin
  foreach table_name in array array['matches','match_players','match_events'] loop
    if to_regclass('public.' || table_name) is not null then
      policy_name := 'sp_production_write_' || table_name;
      execute format('drop policy if exists %I on public.%I', policy_name, table_name);
      execute format(
        'create policy %I on public.%I for all to authenticated using (public.sp_is_workspace_member(workspace_id)) with check (public.sp_is_workspace_member(workspace_id))',
        policy_name, table_name
      );
    end if;
  end loop;
end $$;

commit;

-- Comprobación final opcional:
-- select u.email, w.name, w.workspace_type, m.role, s.status, s.ends_at, s.retention_until, p.name as plan
-- from auth.users u
-- join public.sp_workspace_members m on m.user_id = u.id
-- join public.sp_workspaces w on w.id = m.workspace_id
-- left join public.sp_subscriptions s on s.workspace_id = w.id
-- left join public.sp_plans p on p.id = s.plan_id
-- where lower(u.email) like 'a.garciarenones%';
