import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { PGlite } from '@electric-sql/pglite';
const id = n => `00000000-0000-0000-0000-${String(n).padStart(12,'0')}`;
const migration = readFileSync(new URL('../supabase/migrations/20261108232123_live_event_integrity_and_assignments.sql', import.meta.url), 'utf8');

test('assigned access, atomic goals, durable retries, edits and cancellation with real PostgreSQL RLS', async () => {
  const db = new PGlite();
  try {
    await db.exec(`
      create role anon; create role authenticated; create schema auth;
      grant usage on schema auth to authenticated;
      create function auth.uid() returns uuid language sql as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
      create table sp_workspace_members(workspace_id uuid,user_id uuid,role text,status text);
      create function sp_is_workspace_member(w uuid) returns boolean language sql stable security definer set search_path=public as $$
        select exists(select 1 from sp_workspace_members where workspace_id=w and user_id=auth.uid() and status='active') $$;
      create function sp_has_workspace_role(w uuid,roles text[]) returns boolean language sql stable security definer set search_path=public as $$
        select exists(select 1 from sp_workspace_members where workspace_id=w and user_id=auth.uid() and status='active' and role=any(roles)) $$;
      create table matches(id uuid primary key,workspace_id uuid,competition_id uuid,assigned_to uuid,home_team_id uuid,away_team_id uuid,broadcast_enabled boolean default true,home_score int default 0,away_score int default 0);
      create table match_events(id uuid primary key default gen_random_uuid(),workspace_id uuid,match_id uuid references matches,team_id uuid,player_id uuid,event_type text,match_time text,notes text,created_by uuid,created_at timestamptz default now(),cancelled_at timestamptz,cancelled_by uuid,related_event_id uuid references match_events,penalty_type text,penalty_minutes int,team_penalty_seconds int,personal_penalty_minutes int);
      create table match_players(id uuid primary key,workspace_id uuid,match_id uuid references matches,player_id uuid);
      create table rosters(workspace_id uuid,competition_id uuid,team_id uuid,player_id uuid,member_type text);
      grant select,insert,update,delete on matches,match_events,match_players,rosters to authenticated;
    `);
    for (const t of ['matches','match_events','match_players']) await db.exec(`
      alter table ${t} enable row level security;
      create policy legacy_open on ${t} for all to authenticated using(true) with check(true);
    `);
    for (const [table, label] of [['match_events','events'],['match_players','players']]) {
      for (const action of ['read','insert','update']) {
        const condition = `exists(select 1 from matches m where m.id=${table}.match_id and m.assigned_to=auth.uid())`;
        await db.exec(`create policy "Operators only ${action} assigned match ${label}" on ${table} as restrictive for ${action==='read'?'select':action} to authenticated ${action!=='insert'?`using(${condition})`:''} ${action!=='read'?`with check(${condition})`:''}`);
      }
    }
    await db.exec(migration);
    for (const [user,workspace,role,status] of [[1,10,'owner','active'],[2,10,'producer','active'],[3,10,'producer','active'],[4,10,'producer','suspended'],[5,20,'owner','active']])
      await db.query('insert into sp_workspace_members values($1,$2,$3,$4)',[id(workspace),id(user),role,status]);
    for (const [match,workspace,user,enabled] of [[101,10,2,true],[102,10,3,true],[103,10,null,true],[104,10,2,false],[105,20,2,true],[106,10,4,true]])
      await db.query('insert into matches(id,workspace_id,competition_id,assigned_to,home_team_id,away_team_id,broadcast_enabled) values($1,$2,$3,$4,$5,$6,$7)',[id(match),id(workspace),id(30),user?id(user):null,id(40),id(41),enabled]);
    for (const [team,player] of [[40,50],[40,51],[41,52],[41,53]])
      await db.query("insert into rosters values($1,$2,$3,$4,'player')",[id(10),id(30),id(team),id(player)]);
    const asUser = async n => { await db.exec('reset role'); await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id(n)]); await db.exec('set role authenticated'); };
    const write = async (match,event,action,data={}) => (await db.query('select sp_write_match_event($1,$2,$3,$4) result',[id(match),id(event),action,JSON.stringify(data)])).rows[0].result;
    const goal = {team_id:id(40),player_id:id(50),assistant_id:id(51),match_time:'10:20',notes:'powerplay_goal'};
    await asUser(2);
    assert.deepEqual((await db.query('select id from matches order by id')).rows.map(r=>r.id),[id(101)]);
    for (const match of [102,103,104,105,106]) await assert.rejects(write(match,201,'goal',goal),/no asignado/);
    await assert.rejects(write(101,201,'goal',{...goal,assistant_id:id(52)}),/Asistente/);
    await assert.rejects(write(101,201,'goal',{...goal,recalculate_score:true}),/Solo Manager/);
    assert.equal((await db.query('select count(*)::int n from match_events')).rows[0].n,0);
    const first = await write(101,201,'goal',goal);
    assert.equal(first.created,true); assert.equal(first.assist.related_event_id,id(201));
    for (let n=0;n<5;n++) {
      const retry=await write(101,201,'goal',goal);
      assert.equal(retry.created,false); assert.equal(retry.assist.id,first.assist.id);
    }
    assert.equal((await db.query('select count(*)::int n from match_events')).rows[0].n,2);
    await write(101,202,'goal',goal); // Two legitimate goals at the same clock time.
    const edited = await write(101,201,'edit',{...goal,team_id:id(41),player_id:id(52),assistant_id:id(53),match_time:'09:59'});
    assert.equal(edited.event.team_id,id(41)); assert.equal(edited.assist.player_id,id(53)); assert.equal(edited.assist.match_time,'09:59');
    await assert.rejects(write(101,201,'edit',{...goal,assistant_id:id(52)}),/Asistente/);
    assert.equal((await db.query('select team_id from match_events where id=$1',[id(201)])).rows[0].team_id,id(41));
    await write(101,201,'cancel'); await write(101,201,'cancel');
    assert.equal((await db.query('select count(*)::int n from match_events where cancelled_at is null')).rows[0].n,2);
    assert.ok((await write(101,201,'goal',goal)).event.cancelled_at);
    await assert.rejects(db.query('update matches set assigned_to=$1 where id=$2',[id(3),id(101)]),/asignación/);
    await asUser(3);
    assert.equal((await db.query('select * from match_events')).rows.length,0);
    assert.equal((await db.query('update match_events set cancelled_at=now() returning id')).rows.length,0);
    await assert.rejects(write(102,201,'edit',goal),/no encontrado/);
    await asUser(4);
    assert.equal((await db.query('select * from matches')).rows.length,0);
    await asUser(1);
    assert.equal((await db.query('select * from matches')).rows.length,5);
    for (const match of [103,104]) assert.equal((await write(match,match+200,'goal',goal)).created,true);
    await write(103,305,'goal',{...goal,recalculate_score:true});
    assert.equal((await db.query('select home_score from matches where id=$1',[id(103)])).rows[0].home_score,2);
    await write(103,305,'edit',{...goal,team_id:id(41),player_id:id(52),assistant_id:null,recalculate_score:true});
    assert.deepEqual((await db.query('select home_score,away_score from matches where id=$1',[id(103)])).rows[0],{home_score:1,away_score:1});
    await write(103,305,'cancel',{recalculate_score:true});
    await write(103,305,'cancel',{recalculate_score:true});
    assert.deepEqual((await db.query('select home_score,away_score from matches where id=$1',[id(103)])).rows[0],{home_score:1,away_score:0});
    assert.ok((await write(101,202,'cancel')).event.cancelled_at);
    await asUser(5);
    await assert.rejects(write(101,202,'cancel'),/no asignado/);
    await db.exec('reset role');
    assert.equal((await db.query("select has_function_privilege('anon','sp_write_match_event(uuid,uuid,text,jsonb)','execute') ok")).rows[0].ok,false);
  } finally { await db.close(); }
});
