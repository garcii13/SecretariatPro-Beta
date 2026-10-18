-- One-time repair of the old invitation upsert's canonical-owner downgrade.
-- Ownership comes only from sp_workspaces.owner_user_id. Never reactivate an
-- invited/suspended member or alter staff, deleted workspaces or ownership.
begin;
do $$ begin
  if auth.uid() is not null then
    raise exception 'La reparación requiere mantenimiento administrativo' using errcode='42501';
  end if;
end $$;
with repaired as (
  update public.sp_workspace_members m
  set role='owner', updated_at=now()
  from public.sp_workspaces w
  where m.workspace_id=w.id and m.user_id=w.owner_user_id
    and w.deleted_at is null and m.status='active' and m.role<>'owner'
  returning m.workspace_id
)
select count(*) as repaired_canonical_owner_roles from repaired;
commit;
