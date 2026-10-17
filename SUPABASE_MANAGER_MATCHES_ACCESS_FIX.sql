-- Repair the legacy restrictive SELECT policy, which also constrains
-- INSERT/UPDATE ... RETURNING used by Manager. Keep tenant isolation and
-- the existing assigned-only access for non-manager operators.
begin;
alter policy "Operators only read assigned matches" on public.matches
using (
  assigned_to = auth.uid()
  or public.sp_has_workspace_role(
    workspace_id, array['owner', 'competition_manager']::text[]
  )
);
commit;

-- Verify after applying:
select policyname, permissive, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public' and tablename = 'matches'
order by policyname;

-- Rollback (only if this change needs to be reverted):
-- alter policy "Operators only read assigned matches" on public.matches
-- using (assigned_to = auth.uid());
