-- SecretariatPro Manager · Fase 39
-- Rosters por temporada, dorsales únicos y recursos visuales compartidos.
-- Ejecutar una sola vez en Supabase > SQL Editor.

begin;

create extension if not exists pgcrypto;

alter table if exists public.rosters
  add column if not exists workspace_id uuid references public.sp_workspaces(id) on delete cascade;
alter table if exists public.rosters
  add column if not exists member_type text not null default 'player';
alter table if exists public.rosters
  add column if not exists active boolean not null default true;
alter table if exists public.rosters
  add column if not exists captain boolean not null default false;

update public.rosters
set member_type = 'player'
where member_type is null or btrim(member_type) = '';

with ranked as (
  select id,
         row_number() over (
           partition by workspace_id, competition_id, team_id, player_id
           order by id
         ) as rn
  from public.rosters
  where active is true
    and player_id is not null
    and coalesce(member_type, 'player') = 'player'
)
update public.rosters r
set active = false
from ranked d
where r.id = d.id and d.rn > 1;

with ranked as (
  select id,
         row_number() over (
           partition by workspace_id, competition_id, team_id, shirt_number
           order by id
         ) as rn
  from public.rosters
  where active is true
    and shirt_number is not null
    and coalesce(member_type, 'player') = 'player'
)
update public.rosters r
set active = false
from ranked d
where r.id = d.id and d.rn > 1;

create unique index if not exists rosters_active_player_unique
on public.rosters(workspace_id, competition_id, team_id, player_id)
where active is true and coalesce(member_type, 'player') = 'player';

create unique index if not exists rosters_active_number_unique
on public.rosters(workspace_id, competition_id, team_id, shirt_number)
where active is true
  and shirt_number is not null
  and coalesce(member_type, 'player') = 'player';

create index if not exists rosters_workspace_team_competition_idx
on public.rosters(workspace_id, team_id, competition_id, active);

create index if not exists rosters_workspace_player_idx
on public.rosters(workspace_id, player_id, active);

do $$
begin
  if to_regclass('public.sp_visual_themes') is not null
     and to_regclass('public.competitions') is not null
     and not exists (
       select 1 from pg_constraint
       where conname = 'sp_visual_themes_competition_id_fkey'
         and conrelid = 'public.sp_visual_themes'::regclass
     ) then
    alter table public.sp_visual_themes
      add constraint sp_visual_themes_competition_id_fkey
      foreign key (competition_id) references public.competitions(id) on delete cascade;
  end if;
end $$;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'workspace-assets',
  'workspace-assets',
  true,
  10485760,
  array['image/png','image/jpeg','image/webp','image/svg+xml']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create or replace function public.sp_asset_workspace_id(object_name text)
returns uuid
language plpgsql
immutable
as $$
begin
  return split_part(object_name, '/', 1)::uuid;
exception when others then
  return null;
end;
$$;

grant execute on function public.sp_asset_workspace_id(text) to anon, authenticated;

drop policy if exists workspace_assets_public_read on storage.objects;
create policy workspace_assets_public_read
on storage.objects for select
to public
using (bucket_id = 'workspace-assets');

drop policy if exists workspace_assets_manager_insert on storage.objects;
create policy workspace_assets_manager_insert
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'workspace-assets'
  and public.sp_has_workspace_role(
    public.sp_asset_workspace_id(name),
    array['owner','competition_manager']
  )
);

drop policy if exists workspace_assets_manager_update on storage.objects;
create policy workspace_assets_manager_update
on storage.objects for update
to authenticated
using (
  bucket_id = 'workspace-assets'
  and public.sp_has_workspace_role(
    public.sp_asset_workspace_id(name),
    array['owner','competition_manager']
  )
)
with check (
  bucket_id = 'workspace-assets'
  and public.sp_has_workspace_role(
    public.sp_asset_workspace_id(name),
    array['owner','competition_manager']
  )
);

drop policy if exists workspace_assets_manager_delete on storage.objects;
create policy workspace_assets_manager_delete
on storage.objects for delete
to authenticated
using (
  bucket_id = 'workspace-assets'
  and public.sp_has_workspace_role(
    public.sp_asset_workspace_id(name),
    array['owner','competition_manager']
  )
);

commit;
notify pgrst, 'reload schema';
