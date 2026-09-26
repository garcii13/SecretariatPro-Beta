-- SecretariatPro Beta · invitaciones, alta de membresía y vista segura.
-- Ejecutar una vez en Supabase > SQL Editor.

begin;

-- La vista debe respetar la identidad del usuario que consulta y las políticas
-- RLS de competitions, competition_teams, matches y teams.
alter view public.competition_standings set (security_invoker = true);
revoke all on public.competition_standings from anon;
grant select on public.competition_standings to authenticated;

-- Una invitación crea primero una membresía pendiente. Al abrir el enlace de
-- correo, Supabase autentica al usuario y el portal activa sólo sus filas.
create or replace function public.sp_accept_my_invitations()
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  accepted integer := 0;
begin
  if auth.uid() is null then
    raise exception 'Debes iniciar sesión';
  end if;

  update public.sp_workspace_members
     set status = 'active',
         joined_at = now(),
         updated_at = now()
   where user_id = auth.uid()
     and status = 'invited';
  get diagnostics accepted = row_count;
  return accepted;
end;
$$;

revoke all on function public.sp_accept_my_invitations() from public, anon;
grant execute on function public.sp_accept_my_invitations() to authenticated;

commit;

-- Verificación esperada: security_invoker=true, anon_select=false y auth=true.
select jsonb_build_object(
  'security_invoker', (select reloptions @> array['security_invoker=true'] from pg_class where oid = 'public.competition_standings'::regclass),
  'anon_select', has_table_privilege('anon', 'public.competition_standings', 'SELECT'),
  'authenticated_select', has_table_privilege('authenticated', 'public.competition_standings', 'SELECT')
) as verification;
