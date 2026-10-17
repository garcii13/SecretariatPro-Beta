-- Solo lectura: identificar políticas que bloquean crear o reasignar partidos.
select policyname, permissive, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public' and tablename = 'matches'
order by policyname;

select p.proname, pg_get_functiondef(p.oid) as definition
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname in ('sp_is_workspace_member', 'sp_has_workspace_role');
