-- READ ONLY. Run after the invitation migration, export results as release evidence.
-- These inventories do not replace the authenticated multi-tenant acceptance tests.
select n.nspname as schema, c.relname as relation, c.relrowsecurity as rls,
       c.relforcerowsecurity as force_rls
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relkind='r'
and c.relname in ('sp_workspaces','sp_workspace_members','sp_visual_themes',
                 'competitions','teams','players','matches','match_events')
order by c.relname;

select tablename, policyname, roles, cmd, qual, with_check
from pg_policies where schemaname='public'
and tablename in ('sp_workspaces','sp_workspace_members','sp_visual_themes',
                 'competitions','teams','players','matches','match_events')
order by tablename, policyname;

select p.proname, pg_get_function_identity_arguments(p.oid) as arguments,
       p.prosecdef as security_definer, p.proconfig, md5(p.prosrc) as body_hash,
       has_function_privilege('anon',p.oid,'EXECUTE') as anon_execute,
       has_function_privilege('authenticated',p.oid,'EXECUTE') as authenticated_execute
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public' and p.proname in
 ('sp_invite_workspace_member','sp_accept_my_invitations','sp_create_visual_theme','sp_publish_visual_theme');

select c.reloptions, has_table_privilege('anon',c.oid,'SELECT') as anon_select
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relname='competition_standings';

select id, name, public from storage.buckets
where id in ('ocr-training-samples','team-logos','player-photos');
select policyname, roles, cmd, qual, with_check from pg_policies
where schemaname='storage' and tablename='objects' order by policyname;
