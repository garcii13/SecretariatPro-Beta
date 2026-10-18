-- Real-project regression, using only generated synthetic fixtures.
-- ROLLBACK removes every inserted user/operator/workspace/member. No email is sent.
begin;
do $$
declare
  owner_a uuid := gen_random_uuid();
  owner_b uuid := gen_random_uuid();
  manager_a uuid := gen_random_uuid();
  producer_a uuid := gen_random_uuid();
  suspended_a uuid := gen_random_uuid();
  workspace_a uuid := gen_random_uuid();
  workspace_b uuid := gen_random_uuid();
  result jsonb;
  before_member jsonb;
  after_member jsonb;
  denied boolean;
  changed integer;
begin
  insert into auth.users(id,email,email_confirmed_at,aud,role,raw_user_meta_data)
  select u, 'sp-audit-'||u::text||'@example.invalid',now(),'authenticated','authenticated','{}'::jsonb
    from unnest(array[owner_a,owner_b,manager_a,producer_a,suspended_a]) u;
  insert into public.sp_workspaces(id,name,slug,workspace_type,owner_user_id)
    values(workspace_a,'Audit temporary A','sp-audit-'||workspace_a::text,'personal',owner_a),
          (workspace_b,'Audit temporary B','sp-audit-'||workspace_b::text,'personal',owner_b);
  insert into public.sp_workspace_members(workspace_id,user_id,role,status)
    values(workspace_a,owner_a,'owner','active'),(workspace_b,owner_b,'owner','active'),
          (workspace_a,manager_a,'competition_manager','active'),
          (workspace_a,producer_a,'producer','active'),(workspace_a,suspended_a,'producer','suspended');

  perform set_config('request.jwt.claim.sub',manager_a::text,true);
  perform set_config('request.jwt.claims',jsonb_build_object('sub',manager_a,'role','authenticated')::text,true);
  set local role authenticated;
  if exists(select 1 from public.sp_workspaces where id=workspace_b) then raise exception 'Cross-workspace read allowed'; end if;
  select to_jsonb(m) into before_member from public.sp_workspace_members m where workspace_id=workspace_a and user_id=owner_a;
  result := public.sp_invite_workspace_member(workspace_a,owner_a,'producer');
  if result->'membership'->>'role' <> 'owner' or (result->>'created')::boolean then raise exception 'Owner invitation changed membership'; end if;
  result := public.sp_add_existing_member(workspace_a,'sp-audit-'||owner_a::text||'@example.invalid','producer');
  if result->>'role' <> 'owner' then raise exception 'Legacy RPC changed owner'; end if;
  select to_jsonb(m) into after_member from public.sp_workspace_members m where workspace_id=workspace_a and user_id=owner_a;
  if before_member is distinct from after_member then raise exception 'Owner row changed'; end if;
  result := public.sp_add_existing_member(workspace_a,'sp-audit-'||suspended_a::text||'@example.invalid','competition_manager');
  if result->>'status' <> 'suspended' or result->>'role' <> 'producer' then raise exception 'Legacy RPC revived suspended member'; end if;

  denied := false;
  begin perform public.sp_invite_workspace_member(workspace_b,producer_a,'producer'); exception when insufficient_privilege then denied := true; end;
  if not denied then raise exception 'Foreign invitation allowed'; end if;
  denied := false;
  begin update public.sp_workspace_members set role='owner' where workspace_id=workspace_a and user_id=manager_a; exception when insufficient_privilege then denied := true; end;
  if not denied then raise exception 'Self-escalation allowed'; end if;
  denied := false;
  begin update public.sp_workspace_members set status='suspended' where workspace_id=workspace_a and user_id=owner_a; exception when insufficient_privilege then denied := true; end;
  if not denied then raise exception 'Owner suspension allowed'; end if;
  denied := false;
  begin delete from public.sp_workspace_members where workspace_id=workspace_a and user_id=owner_a; exception when insufficient_privilege then denied := true; end;
  if not denied then raise exception 'Owner deletion allowed'; end if;
  denied := false;
  begin update public.sp_workspaces set owner_user_id=manager_a where id=workspace_a; exception when insufficient_privilege then denied := true; end;
  if not denied then raise exception 'Owner transfer allowed'; end if;
  denied := false;
  begin update public.sp_workspaces set sport_mode='handball' where id=workspace_a; exception when insufficient_privilege then denied := true; end;
  if not denied then raise exception 'Manager changed owner-only sport setting'; end if;

  perform set_config('request.jwt.claim.sub',producer_a::text,true);
  perform set_config('request.jwt.claims',jsonb_build_object('sub',producer_a,'role','authenticated')::text,true);
  denied := false;
  begin perform public.sp_invite_workspace_member(workspace_a,owner_b,'producer'); exception when insufficient_privilege then denied := true; end;
  if not denied then raise exception 'Producer invitation allowed'; end if;
  perform set_config('request.jwt.claim.sub',owner_a::text,true);
  perform set_config('request.jwt.claims',jsonb_build_object('sub',owner_a,'role','authenticated')::text,true);
  update public.sp_workspaces set sport_mode='handball' where id=workspace_a;
  get diagnostics changed=row_count;
  if changed<>1 then raise exception 'Legitimate owner update blocked'; end if;
  reset role;
end;
$$;
rollback;
select jsonb_build_object('passed',true,'fixtures_rolled_back',true,'sent_emails',0,
  'checks',array['tenant_read','owner_reinvite','legacy_owner_reinvite','legacy_suspended_reinvite',
   'foreign_invite','self_escalation','owner_suspend','owner_delete','owner_transfer','manager_sport',
   'producer_invite','owner_sport']) as membership_regression;
