-- Install before deploying the updated invite-member function.
-- Reinviting is idempotent; role/status changes use separate, protected operations.
begin;

create or replace function public.sp_invite_workspace_member(
  p_workspace uuid, p_user uuid, p_role text
) returns jsonb
language plpgsql security definer
set search_path = public, pg_temp
as $$
declare
  member public.sp_workspace_members%rowtype;
  confirmed boolean;
  owner_id uuid;
  inserted boolean := false;
begin
  if auth.uid() is null or not public.sp_has_workspace_role(p_workspace, array['owner', 'competition_manager']) then
    raise exception 'Tu rol no permite invitar miembros' using errcode = '42501';
  end if;
  if p_role is null or p_role not in ('producer', 'competition_manager') then
    raise exception 'Rol no válido' using errcode = '22023';
  end if;
  select owner_user_id into owner_id from public.sp_workspaces where id = p_workspace;
  if not found then raise exception 'Espacio no encontrado'; end if;

  select * into member from public.sp_workspace_members
    where workspace_id = p_workspace and user_id = p_user;
  if found then
    return jsonb_build_object('created', false, 'membership', to_jsonb(member));
  end if;
  -- Never create a lesser-role row for an owner whose membership is being repaired.
  if p_user = owner_id then
    raise exception 'No se puede modificar al propietario mediante una invitación' using errcode = '42501';
  end if;
  select email_confirmed_at is not null into confirmed from auth.users where id = p_user;
  if not found then raise exception 'Usuario no encontrado'; end if;

  insert into public.sp_workspace_members
    (workspace_id, user_id, role, status, invited_by, joined_at, updated_at)
  values
    (p_workspace, p_user, p_role, case when confirmed then 'active' else 'invited' end,
     auth.uid(), now(), now())
  on conflict (workspace_id, user_id) do nothing
  returning * into member;
  inserted := found;
  if not inserted then
    select * into member from public.sp_workspace_members
      where workspace_id = p_workspace and user_id = p_user;
    if not found then raise exception 'La membresía cambió durante la invitación; vuelve a intentarlo'; end if;
  end if;
  return jsonb_build_object('created', inserted, 'membership', to_jsonb(member));
end;
$$;

revoke all on function public.sp_invite_workspace_member(uuid, uuid, text) from public, anon;
grant execute on function public.sp_invite_workspace_member(uuid, uuid, text) to authenticated;
commit;
