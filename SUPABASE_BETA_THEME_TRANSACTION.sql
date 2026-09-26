-- Apply after SUPABASE_BETA_VISUAL_SCOPE.sql. Required by the Manager in this release.
begin;

-- Existing beta data may contain multiple published rows in one scope.
with ranked as (
  select id, row_number() over (
    partition by workspace_id, coalesce(competition_id, '00000000-0000-0000-0000-000000000000'::uuid)
    order by updated_at desc, version desc, id desc
  ) as position
  from public.sp_visual_themes where published
)
update public.sp_visual_themes t set published = false
from ranked r where t.id = r.id and r.position > 1;

create unique index if not exists sp_visual_themes_one_published
on public.sp_visual_themes(workspace_id, coalesce(competition_id, '00000000-0000-0000-0000-000000000000'::uuid))
where published;

create or replace function public.sp_create_visual_theme(
  p_workspace uuid, p_competition uuid, p_name text, p_config jsonb, p_publish boolean default false
) returns jsonb language plpgsql security definer set search_path = public as $$
declare
  next_version integer;
  result public.sp_visual_themes%rowtype;
begin
  if auth.uid() is null or not public.sp_has_workspace_role(p_workspace, array['owner', 'competition_manager']) then
    raise exception 'No tienes permisos para publicar identidades';
  end if;
  if p_config is null or jsonb_typeof(p_config) <> 'object' then
    raise exception 'La identidad visual debe ser un objeto';
  end if;
  if p_competition is not null then
    if not exists (select 1 from public.sp_workspaces where id = p_workspace and visual_identity_mode = 'competition')
       or not exists (select 1 from public.competitions where id = p_competition and workspace_id = p_workspace) then
      raise exception 'Ámbito de competición no permitido';
    end if;
  end if;
  perform pg_advisory_xact_lock(hashtext('sp_visual:' || p_workspace::text || ':' || coalesce(p_competition::text, 'general')));
  select coalesce(max(version), 0) + 1 into next_version
  from public.sp_visual_themes
  where workspace_id = p_workspace and competition_id is not distinct from p_competition;
  if p_publish then
    update public.sp_visual_themes set published = false
    where workspace_id = p_workspace and competition_id is not distinct from p_competition and published;
  end if;
  insert into public.sp_visual_themes(workspace_id, competition_id, name, config, version, published, locked, created_by)
  values (p_workspace, p_competition, coalesce(nullif(trim(p_name), ''), 'Identidad principal'),
          p_config, next_version, p_publish, true, auth.uid())
  returning * into result;
  return to_jsonb(result);
end;
$$;

create or replace function public.sp_publish_visual_theme(p_workspace uuid, p_theme uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  target public.sp_visual_themes%rowtype;
  result public.sp_visual_themes%rowtype;
begin
  if auth.uid() is null or not public.sp_has_workspace_role(p_workspace, array['owner', 'competition_manager']) then
    raise exception 'No tienes permisos para publicar identidades';
  end if;
  select * into target from public.sp_visual_themes
  where id = p_theme and workspace_id = p_workspace;
  if not found then raise exception 'Identidad visual no encontrada'; end if;
  if target.competition_id is not null then
    if not exists (select 1 from public.sp_workspaces where id = p_workspace and visual_identity_mode = 'competition')
       or not exists (select 1 from public.competitions where id = target.competition_id and workspace_id = p_workspace) then
      raise exception 'Ámbito de competición no permitido';
    end if;
  end if;
  perform pg_advisory_xact_lock(hashtext('sp_visual:' || p_workspace::text || ':' || coalesce(target.competition_id::text, 'general')));
  update public.sp_visual_themes set published = false
  where workspace_id = p_workspace and competition_id is not distinct from target.competition_id and published;
  update public.sp_visual_themes set published = true, locked = true
  where id = p_theme and workspace_id = p_workspace
  returning * into result;
  return to_jsonb(result);
end;
$$;

revoke all on function public.sp_create_visual_theme(uuid, uuid, text, jsonb, boolean) from public, anon;
revoke all on function public.sp_publish_visual_theme(uuid, uuid) from public, anon;
grant execute on function public.sp_create_visual_theme(uuid, uuid, text, jsonb, boolean) to authenticated;
grant execute on function public.sp_publish_visual_theme(uuid, uuid) to authenticated;
commit;
