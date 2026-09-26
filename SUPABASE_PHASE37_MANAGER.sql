-- SecretariatPro Manager · Fase 37
-- Ejecutar después de SUPABASE_PHASE35_MULTI_TENANT.sql.
-- Añade la incorporación segura de usuarios existentes a una asociación.

begin;

create or replace function public.sp_add_existing_member(
  target_workspace uuid,
  target_email text,
  target_role text default 'producer'
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  target_user_id uuid;
  clean_email text := lower(trim(target_email));
  clean_role text := lower(trim(target_role));
  target_name text;
begin
  if auth.uid() is null then
    raise exception 'Debes iniciar sesión';
  end if;

  if not public.sp_has_workspace_role(target_workspace, array['owner','competition_manager']) then
    raise exception 'Tu rol no permite añadir miembros a este espacio';
  end if;

  if clean_role not in ('competition_manager', 'producer') then
    raise exception 'Rol no válido';
  end if;

  select id,
         coalesce(
           raw_user_meta_data ->> 'display_name',
           raw_user_meta_data ->> 'full_name',
           split_part(email, '@', 1)
         )
    into target_user_id, target_name
  from auth.users
  where lower(email) = clean_email
  limit 1;

  if target_user_id is null then
    raise exception 'No existe todavía una cuenta de SecretariatPro con ese correo';
  end if;

  insert into public.sp_workspace_members(
    workspace_id, user_id, role, status, invited_by, joined_at
  )
  values (
    target_workspace, target_user_id, clean_role, 'active', auth.uid(), now()
  )
  on conflict (workspace_id, user_id) do update
    set role = excluded.role,
        status = 'active',
        invited_by = auth.uid(),
        updated_at = now();

  -- Mantiene legible el directorio operativo utilizado por Manager y los partidos.
  -- El bloque es tolerante por compatibilidad con instalaciones antiguas.
  if to_regclass('public.scoreboard_operators') is not null then
    begin
      execute $sql$
        insert into public.scoreboard_operators(id, email, display_name, workspace_id)
        values ($1, $2, $3, $4)
        on conflict (id) do update
          set email = excluded.email,
              display_name = excluded.display_name,
              workspace_id = excluded.workspace_id
      $sql$ using target_user_id, clean_email, target_name, target_workspace;
    exception when others then
      raise notice 'No se pudo sincronizar scoreboard_operators: %', sqlerrm;
    end;
  end if;

  return jsonb_build_object(
    'ok', true,
    'user_id', target_user_id,
    'email', clean_email,
    'display_name', target_name,
    'role', clean_role,
    'status', 'active'
  );
end;
$$;

grant execute on function public.sp_add_existing_member(uuid, text, text) to authenticated;

commit;

-- Comprobación opcional:
-- select public.sp_add_existing_member(
--   (select id from public.sp_workspaces where slug = 'a-garciarenones-asociacion'),
--   'correo-del-realizador@ejemplo.com',
--   'producer'
-- );
