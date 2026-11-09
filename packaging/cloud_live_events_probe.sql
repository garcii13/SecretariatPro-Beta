-- Synthetic fixtures only. Every write is rolled back; no email is sent.
begin;
do $$
declare
 owner_id uuid := gen_random_uuid(); producer_id uuid := gen_random_uuid(); other_id uuid := gen_random_uuid();
 ws uuid := gen_random_uuid(); comp uuid := gen_random_uuid(); home uuid := gen_random_uuid(); away uuid := gen_random_uuid();
 scorer uuid := gen_random_uuid(); helper uuid := gen_random_uuid(); away_player uuid := gen_random_uuid();
 assigned uuid := gen_random_uuid(); unassigned uuid := gen_random_uuid(); other_match uuid := gen_random_uuid();
 event_id uuid := gen_random_uuid(); admin_event uuid := gen_random_uuid();
 result jsonb; denied boolean; n integer;
begin
 insert into auth.users(id,email,email_confirmed_at,aud,role,raw_user_meta_data)
 select u,'sp-live-audit-'||u::text||'@example.invalid',now(),'authenticated','authenticated','{}'::jsonb
 from unnest(array[owner_id,producer_id,other_id]) u;
 insert into public.scoreboard_operators(id,email)
 select u,'sp-live-audit-'||u::text||'@example.invalid' from unnest(array[owner_id,producer_id,other_id]) u on conflict(id) do nothing;
 insert into public.sp_workspaces(id,name,slug,workspace_type,owner_user_id)
 values(ws,'Beta 12 temporary audit','sp-live-audit-'||ws::text,'personal',owner_id);
 insert into public.sp_workspace_members(workspace_id,user_id,role,status)
 values(ws,owner_id,'owner','active'),(ws,producer_id,'producer','active'),(ws,other_id,'producer','active');
 insert into public.competitions(id,workspace_id,name) values(comp,ws,'Temporary beta 12 audit');
 insert into public.teams(id,workspace_id,name,short_name) values(home,ws,'Audit home '||ws::text,'HOM'),(away,ws,'Audit away '||ws::text,'AWY');
 insert into public.players(id,workspace_id,first_name,last_name) values(scorer,ws,'Audit','Scorer'),(helper,ws,'Audit','Helper'),(away_player,ws,'Audit','Away');
 insert into public.rosters(workspace_id,competition_id,team_id,player_id) values(ws,comp,home,scorer),(ws,comp,home,helper),(ws,comp,away,away_player);
 insert into public.matches(id,workspace_id,competition_id,home_team_id,away_team_id,assigned_to)
 values(assigned,ws,comp,home,away,producer_id),(unassigned,ws,comp,home,away,null),(other_match,ws,comp,home,away,other_id);
 perform set_config('request.jwt.claim.sub',producer_id::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',producer_id,'role','authenticated')::text,true);
 set local role authenticated;
 select count(*) into n from public.matches where workspace_id=ws;
 if n<>1 then raise exception 'Producer sees unassigned/other matches: %',n; end if;
 denied:=false;
 begin perform public.sp_write_match_event(unassigned,event_id,'goal',jsonb_build_object('team_id',home,'player_id',scorer)); exception when insufficient_privilege then denied:=true; end;
 if not denied then raise exception 'Unassigned goal accepted'; end if;
 result:=public.sp_write_match_event(assigned,event_id,'goal',jsonb_build_object('team_id',home,'player_id',scorer,'assistant_id',helper,'match_time','10:20'));
 if not (result->>'created')::boolean then raise exception 'Goal not created'; end if;
 result:=public.sp_write_match_event(assigned,event_id,'goal',jsonb_build_object('team_id',home,'player_id',scorer,'assistant_id',helper,'match_time','10:20'));
 if (result->>'created')::boolean then raise exception 'Retry duplicated goal'; end if;
 select count(*) into n from public.match_events where match_id=assigned and cancelled_at is null;
 if n<>2 then raise exception 'Goal/assist count differs: %',n; end if;
 result:=public.sp_write_match_event(assigned,event_id,'edit',jsonb_build_object('team_id',away,'player_id',away_player,'match_time','10:21'));
 if result->'event'->>'team_id'<>away::text then raise exception 'Team edit failed'; end if;
 perform public.sp_write_match_event(assigned,event_id,'cancel');
 perform public.sp_write_match_event(assigned,event_id,'cancel');
 select count(*) into n from public.match_events where match_id=assigned and cancelled_at is null;
 if n<>0 then raise exception 'Cancellation left active events'; end if;
 perform set_config('request.jwt.claim.sub',owner_id::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',owner_id,'role','authenticated')::text,true);
 result:=public.sp_write_match_event(unassigned,admin_event,'goal',jsonb_build_object('team_id',home,'player_id',scorer,'recalculate_score',true));
 select home_score into n from public.matches where id=unassigned;
 if n<>1 then raise exception 'Manager score not updated atomically'; end if;
 perform public.sp_write_match_event(unassigned,admin_event,'cancel','{"recalculate_score":true}'::jsonb);
 select home_score into n from public.matches where id=unassigned;
 if n<>0 then raise exception 'Manager score not reduced'; end if;
 reset role;
end $$;
rollback;
select jsonb_build_object('passed',true,'fixtures_rolled_back',true,'sent_emails',0,
 'checks',array['assigned_only','denied_unassigned','atomic_goal_assist','retry','edit_team','cancel_retry','manager_unassigned','manager_atomic_score']) as live_events_regression;
