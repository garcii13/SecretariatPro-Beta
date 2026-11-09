-- Beta 12: assignment is enforced in the database, including direct API calls.
-- Managers retain their workspace's administrative/federation act access.
begin;

drop policy if exists sp_assignment_guard_matches on public.matches;
create policy sp_assignment_guard_matches on public.matches as restrictive
for all to authenticated
using (public.sp_is_workspace_member(workspace_id) and (
  public.sp_has_workspace_role(workspace_id, array['owner','competition_manager'])
  or (assigned_to = (select auth.uid()) and broadcast_enabled)))
with check (public.sp_is_workspace_member(workspace_id) and (
  public.sp_has_workspace_role(workspace_id, array['owner','competition_manager'])
  or (assigned_to = (select auth.uid()) and broadcast_enabled)));

-- Replace legacy assigned-only guards so managers can also keep administrative
-- acts for unassigned matches and matches without a broadcast.
do $$
declare t text; p text;
begin
  foreach t in array array['match_events','match_players'] loop
    for p in select policyname from pg_policies where schemaname='public'
      and tablename=t and policyname like 'Operators only % assigned match %'
    loop execute format('drop policy %I on public.%I',p,t); end loop;
    execute format('drop policy if exists sp_assignment_guard on public.%I',t);
    execute format('create policy sp_assignment_guard on public.%1$I as restrictive for all to authenticated
      using (exists (select 1 from public.matches m where m.id=%1$I.match_id and m.workspace_id=%1$I.workspace_id))
      with check (exists (select 1 from public.matches m where m.id=%1$I.match_id and m.workspace_id=%1$I.workspace_id))',t);
  end loop;
end $$;

-- A producer may update the result, but cannot move/reassign a match to acquire
-- another producer's act or grant access to another account.
create or replace function public.sp_guard_match_assignment() returns trigger
language plpgsql security invoker set search_path=public as $$
begin
  if auth.uid() is not null and not public.sp_has_workspace_role(old.workspace_id,array['owner','competition_manager'])
    and (new.workspace_id,new.competition_id,new.assigned_to,new.home_team_id,new.away_team_id,new.broadcast_enabled)
      is distinct from (old.workspace_id,old.competition_id,old.assigned_to,old.home_team_id,old.away_team_id,old.broadcast_enabled)
  then raise exception 'Solo Manager puede cambiar la asignación o los equipos del partido' using errcode='42501'; end if;
  return new;
end $$;
drop trigger if exists sp_guard_match_assignment on public.matches;
create trigger sp_guard_match_assignment before update on public.matches
for each row execute function public.sp_guard_match_assignment();
revoke all on function public.sp_guard_match_assignment() from public, anon;

-- One transaction per goal + assist / correction / cancellation. Row locking
-- serializes concurrent retries and assignment changes. RLS remains in force.
create or replace function public.sp_write_match_event(
  p_match_id uuid, p_event_id uuid, p_action text, p_data jsonb default '{}'
) returns jsonb language plpgsql security invoker set search_path=public as $$
declare
  m public.matches%rowtype;
  e public.match_events%rowtype;
  previous public.match_events%rowtype;
  a public.match_events%rowtype;
  team uuid; player uuid; assistant uuid; event_kind text;
  penalty text; minutes integer; seconds integer; personal integer;
  recalculate boolean := coalesce((p_data->>'recalculate_score')::boolean,false);
begin
  if auth.uid() is null then raise exception 'Inicia sesión' using errcode='42501'; end if;
  if p_action not in ('goal','edit','cancel') or p_event_id is null then
    raise exception 'Operación no válida' using errcode='22023';
  end if;
  select * into m from public.matches where id=p_match_id for update;
  if not found then raise exception 'Partido no disponible o no asignado' using errcode='42501'; end if;
  if recalculate and not public.sp_has_workspace_role(m.workspace_id,array['owner','competition_manager']) then
    raise exception 'Solo Manager puede recalcular el resultado del acta' using errcode='42501';
  end if;
  select * into e from public.match_events where id=p_event_id and match_id=m.id;
  if p_action='goal' and found then
    if e.created_by is distinct from auth.uid() or e.event_type <> 'goal' then
      raise exception 'La petición pertenece a otro evento' using errcode='42501';
    end if;
    select * into a from public.match_events where related_event_id=e.id and event_type='assist' and cancelled_at is null limit 1;
    return jsonb_build_object('event',to_jsonb(e),'assist',case when a.id is not null then to_jsonb(a) end,'created',false);
  end if;
  if p_action <> 'goal' and not found then raise exception 'Evento no encontrado' using errcode='22023'; end if;
  previous := e;
  if p_action='cancel' then
    update public.match_events set cancelled_at=coalesce(cancelled_at,now()),cancelled_by=coalesce(cancelled_by,auth.uid())
      where match_id=m.id and (id=e.id or (related_event_id=e.id and event_type='assist'));
    select * into e from public.match_events where id=p_event_id;
    if recalculate and e.event_type='goal' then
      update public.matches set
        home_score=(select count(*) from public.match_events where match_id=m.id and team_id=m.home_team_id and event_type='goal' and cancelled_at is null),
        away_score=(select count(*) from public.match_events where match_id=m.id and team_id=m.away_team_id and event_type='goal' and cancelled_at is null)
        where id=m.id;
    end if;
    return jsonb_build_object('event',to_jsonb(e),'previous',to_jsonb(previous),'created',false);
  end if;
  if p_action='edit' and (e.cancelled_at is not null or e.event_type not in ('goal','penalty')) then
    raise exception 'Solo se pueden editar goles y expulsiones activos' using errcode='22023';
  end if;
  team := (p_data->>'team_id')::uuid;
  player := (p_data->>'player_id')::uuid;
  assistant := nullif(p_data->>'assistant_id','')::uuid;
  event_kind := case when p_action='goal' then 'goal' else e.event_type end;
  if team is null or team not in (m.home_team_id,m.away_team_id) then
    raise exception 'Equipo ajeno al partido' using errcode='22023';
  end if;
  if player is null or not exists(select 1 from public.rosters r where r.workspace_id=m.workspace_id
    and r.competition_id=m.competition_id and r.team_id=team and r.player_id=player
    and coalesce(r.member_type,'player') <> 'coach') then
    raise exception 'El jugador no pertenece a la plantilla de este equipo' using errcode='22023';
  end if;
  if assistant is not null and (event_kind <> 'goal' or assistant=player or not exists(
    select 1 from public.rosters r where r.workspace_id=m.workspace_id and r.competition_id=m.competition_id
    and r.team_id=team and r.player_id=assistant and coalesce(r.member_type,'player') <> 'coach')) then
    raise exception 'Asistente no válido para este equipo' using errcode='22023';
  end if;
  if length(coalesce(p_data->>'match_time','')) > 20 or length(coalesce(p_data->>'notes','')) > 2000 then
    raise exception 'Tiempo o notas demasiado largos' using errcode='22023';
  end if;
  if event_kind='penalty' then
    penalty := coalesce(p_data->>'penalty_type',e.penalty_type,'2');
    if penalty not in ('2','2+2','2+10') then raise exception 'Sanción no válida' using errcode='22023'; end if;
    minutes := case penalty when '2+2' then 4 when '2+10' then 12 else 2 end;
    seconds := case penalty when '2+2' then 240 else 120 end;
    personal := case penalty when '2+10' then 10 else 0 end;
  end if;
  if p_action='goal' then
    insert into public.match_events(id,workspace_id,match_id,team_id,player_id,event_type,match_time,notes,created_by)
      values(p_event_id,m.workspace_id,m.id,team,player,'goal',nullif(p_data->>'match_time',''),nullif(p_data->>'notes',''),auth.uid()) returning * into e;
  else
    update public.match_events set team_id=team,player_id=player,match_time=nullif(p_data->>'match_time',''),
      notes=nullif(p_data->>'notes',''),penalty_type=penalty,penalty_minutes=minutes,
      team_penalty_seconds=seconds,personal_penalty_minutes=personal where id=e.id returning * into e;
  end if;
  if event_kind='goal' then
    select * into a from public.match_events where match_id=m.id and related_event_id=e.id
      and event_type='assist' and cancelled_at is null order by created_at,id limit 1;
    if assistant is null then
      update public.match_events set cancelled_at=now(),cancelled_by=auth.uid()
        where match_id=m.id and related_event_id=e.id and event_type='assist' and cancelled_at is null;
      a := null;
    elsif a.id is null then
      insert into public.match_events(workspace_id,match_id,team_id,player_id,event_type,match_time,related_event_id,created_by)
        values(m.workspace_id,m.id,team,assistant,'assist',e.match_time,e.id,auth.uid()) returning * into a;
    else
      update public.match_events set team_id=team,player_id=assistant,match_time=e.match_time where id=a.id returning * into a;
      update public.match_events set cancelled_at=now(),cancelled_by=auth.uid()
        where match_id=m.id and related_event_id=e.id and event_type='assist' and cancelled_at is null and id<>a.id;
    end if;
  end if;
  if recalculate and event_kind='goal' then
    update public.matches set
      home_score=(select count(*) from public.match_events where match_id=m.id and team_id=m.home_team_id and event_type='goal' and cancelled_at is null),
      away_score=(select count(*) from public.match_events where match_id=m.id and team_id=m.away_team_id and event_type='goal' and cancelled_at is null)
      where id=m.id;
  end if;
  return jsonb_build_object('event',to_jsonb(e),'assist',case when a.id is not null then to_jsonb(a) end,
    'previous',case when previous.id is not null then to_jsonb(previous) end,'created',p_action='goal');
end $$;
revoke all on function public.sp_write_match_event(uuid,uuid,text,jsonb) from public,anon;
grant execute on function public.sp_write_match_event(uuid,uuid,text,jsonb) to authenticated;
commit;
