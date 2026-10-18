-- Protect membership invariants even when a client calls PostgREST directly.
-- Keep the legacy RPC callable for older Manager versions, but idempotent.
begin;

create or replace function public.sp_guard_membership_identity()
returns trigger language plpgsql security definer set search_path = public, pg_temp as $$
declare
  workspace_owner uuid;
  workspace uuid;
  member_user uuid;
begin
  workspace := case when tg_op = 'DELETE' then old.workspace_id else new.workspace_id end;
  member_user := case when tg_op = 'DELETE' then old.user_id else new.user_id end;
  select owner_user_id into workspace_owner from public.sp_workspaces where id = workspace;
  -- Parent/user removal cascades must remain possible for legitimate account/workspace deletion.
  if tg_op = 'DELETE' and (workspace_owner is null or not exists(select 1 from auth.users where id=member_user)) then
    return old;
  end if;
  if auth.uid() is not null then
    if tg_op = 'UPDATE' and (new.workspace_id <> old.workspace_id or new.user_id <> old.user_id) then
      raise exception 'La identidad de una membresía no se puede cambiar' using errcode='42501';
    end if;
    if tg_op = 'DELETE' and old.user_id = workspace_owner then
      raise exception 'No se puede eliminar al propietario del espacio' using errcode='42501';
    end if;
    if tg_op = 'UPDATE' and old.user_id = workspace_owner and
       (to_jsonb(new)-'updated_at') is distinct from (to_jsonb(old)-'updated_at') then
      raise exception 'No se puede modificar al propietario desde una membresía' using errcode='42501';
    end if;
  end if;
  if tg_op <> 'DELETE' and new.role = 'owner' and new.user_id is distinct from workspace_owner then
    raise exception 'No se puede otorgar el rol de propietario mediante una membresía' using errcode='42501';
  end if;
  if tg_op <> 'DELETE' and new.user_id = workspace_owner and new.role <> 'owner' then
    raise exception 'La membresía del propietario debe conservar su rol' using errcode='42501';
  end if;
  if tg_op = 'DELETE' then return old; end if;
  return new;
end;
$$;

drop trigger if exists sp_membership_identity_guard on public.sp_workspace_members;
create trigger sp_membership_identity_guard before insert or update or delete on public.sp_workspace_members
for each row execute function public.sp_guard_membership_identity();
revoke all on function public.sp_guard_membership_identity() from public, anon, authenticated;

create or replace function public.sp_guard_workspace_owner()
returns trigger language plpgsql set search_path = public, pg_temp as $$
begin
  if auth.uid() is not null then
    if new.owner_user_id is distinct from old.owner_user_id then
      raise exception 'El propietario no se puede cambiar desde el cliente' using errcode='42501';
    end if;
    if new.sport_mode is distinct from old.sport_mode and auth.uid() <> old.owner_user_id then
      raise exception 'Solo el propietario puede cambiar el deporte' using errcode='42501';
    end if;
  end if;
  return new;
end;
$$;
drop trigger if exists sp_workspace_owner_guard on public.sp_workspaces;
create trigger sp_workspace_owner_guard before update on public.sp_workspaces
for each row execute function public.sp_guard_workspace_owner();
revoke all on function public.sp_guard_workspace_owner() from public, anon, authenticated;

create or replace function public.sp_add_existing_member(
  target_workspace uuid, target_email text, target_role text default 'producer'
) returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare
  target_user uuid;
  target_name text;
  clean_email text := lower(trim(target_email));
  result jsonb;
begin
  if auth.uid() is null or not public.sp_has_workspace_role(target_workspace, array['owner','competition_manager']) then
    raise exception 'Tu rol no permite añadir miembros a este espacio' using errcode='42501';
  end if;
  select id, coalesce(raw_user_meta_data->>'display_name',raw_user_meta_data->>'full_name',split_part(email,'@',1))
    into target_user,target_name from auth.users where lower(email)=clean_email limit 1;
  if target_user is null then raise exception 'No existe todavía una cuenta de SecretariatPro con ese correo'; end if;
  result := public.sp_invite_workspace_member(target_workspace,target_user,lower(trim(target_role)));
  if to_regclass('public.scoreboard_operators') is not null then
    begin
      execute 'insert into public.scoreboard_operators(id,email,display_name,workspace_id) values($1,$2,$3,$4) on conflict(id) do nothing'
      using target_user,clean_email,target_name,target_workspace;
    exception when others then
      raise notice 'No se pudo sincronizar el directorio operativo';
    end;
  end if;
  return jsonb_build_object('ok',true,'user_id',target_user,'email',clean_email,'display_name',target_name,
    'role',result->'membership'->>'role','status',result->'membership'->>'status',
    'already_member',not (result->>'created')::boolean);
end;
$$;
revoke all on function public.sp_add_existing_member(uuid,text,text) from public, anon;
grant execute on function public.sp_add_existing_member(uuid,text,text) to authenticated;

-- These helpers require a signed-in caller. RLS keeps its authenticated EXECUTE grant.
revoke all on function public.sp_has_workspace_role(uuid,text[]) from public, anon;
revoke all on function public.sp_is_workspace_member(uuid) from public, anon;
grant execute on function public.sp_has_workspace_role(uuid,text[]) to authenticated;
grant execute on function public.sp_is_workspace_member(uuid) to authenticated;
-- Trigger invocation is unaffected by revoking direct RPC execution.
revoke all on function public.sync_scoreboard_operator() from public, anon, authenticated;
alter function public.set_updated_at() set search_path = public, pg_temp;
alter function public.sp_set_updated_at() set search_path = public, pg_temp;
alter function public.sp_subscription_retention() set search_path = public, pg_temp;
alter function public.sp_asset_workspace_id(text) set search_path = public, pg_temp;
commit;
