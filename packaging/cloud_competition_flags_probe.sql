-- Synthetic real-project checks. No emails or persistent test rows.
begin;
do $$
declare
  owner_a uuid:=gen_random_uuid(); owner_b uuid:=gen_random_uuid();
  manager_a uuid:=gen_random_uuid(); producer_a uuid:=gen_random_uuid();
  workspace_a uuid:=gen_random_uuid(); workspace_b uuid:=gen_random_uuid();
  cup_a uuid:=gen_random_uuid(); cup_b uuid:=gen_random_uuid();
  team_a uuid:=gen_random_uuid(); team_b uuid:=gen_random_uuid();
  changed integer;
begin
  insert into auth.users(id,email,email_confirmed_at,aud,role,raw_user_meta_data)
    select u,'sp-flags-audit-'||u::text||'@example.invalid',now(),'authenticated','authenticated','{}'::jsonb
    from unnest(array[owner_a,owner_b,manager_a,producer_a]) u;
  insert into public.sp_workspaces(id,name,slug,workspace_type,owner_user_id)
    values(workspace_a,'Flags audit A','sp-flags-audit-'||workspace_a::text,'personal',owner_a),
          (workspace_b,'Flags audit B','sp-flags-audit-'||workspace_b::text,'personal',owner_b);
  insert into public.sp_workspace_members(workspace_id,user_id,role,status)
    values(workspace_a,owner_a,'owner','active'),(workspace_b,owner_b,'owner','active'),
          (workspace_a,manager_a,'competition_manager','active'),(workspace_a,producer_a,'producer','active');
  insert into public.competitions(id,workspace_id,name) values(cup_a,workspace_a,'Audit cup A'),(cup_b,workspace_b,'Audit cup B');
  insert into public.teams(id,workspace_id,name,short_name,logo_url)
    values(team_a,workspace_a,'Audit team A','AUD-A','https://assets.test/crest-a.svg'),
          (team_b,workspace_b,'Audit team B','AUD-B','https://assets.test/crest-b.svg');
  perform set_config('request.jwt.claim.sub',manager_a::text,true);
  perform set_config('request.jwt.claims',jsonb_build_object('sub',manager_a,'role','authenticated')::text,true);
  set local role authenticated;
  if exists(select 1 from public.teams where id=team_b) or exists(select 1 from public.competitions where id=cup_b)
    then raise exception 'Cross-workspace flag/competition read allowed'; end if;
  update public.competitions set is_international=true where id=cup_a;
  get diagnostics changed=row_count;
  if changed<>1 then raise exception 'Manager cannot enable international mode'; end if;
  update public.teams set flag_url='https://assets.test/flag-a.svg' where id=team_a;
  get diagnostics changed=row_count;
  if changed<>1 then raise exception 'Manager cannot save team flag'; end if;
  if not exists(select 1 from public.teams where id=team_a and logo_url='https://assets.test/crest-a.svg')
    then raise exception 'Flag changed crest'; end if;
  update public.teams set flag_url='https://assets.test/foreign.svg' where id=team_b;
  get diagnostics changed=row_count;
  if changed<>0 then raise exception 'Manager changed foreign flag'; end if;
  update public.competitions set is_international=true where id=cup_b;
  get diagnostics changed=row_count;
  if changed<>0 then raise exception 'Manager changed foreign competition'; end if;
  perform set_config('request.jwt.claim.sub',producer_a::text,true);
  perform set_config('request.jwt.claims',jsonb_build_object('sub',producer_a,'role','authenticated')::text,true);
  update public.teams set flag_url=null where id=team_a;
  get diagnostics changed=row_count;
  if changed<>0 then raise exception 'Producer changed team flag'; end if;
  update public.competitions set is_international=false where id=cup_a;
  get diagnostics changed=row_count;
  if changed<>0 then raise exception 'Producer changed international mode'; end if;
  if not exists(select 1 from public.teams where id=team_a and flag_url='https://assets.test/flag-a.svg')
    then raise exception 'Producer cannot read the assigned workspace flag'; end if;
  reset role;
end;
$$;
rollback;
select jsonb_build_object('passed',true,'fixtures_rolled_back',true,'sent_emails',0,
 'checks',array['tenant_read','manager_competition_mode','manager_team_flag','crest_preserved',
 'foreign_flag_denied','foreign_competition_denied','producer_flag_denied','producer_mode_denied','producer_read']) as flag_regression;
