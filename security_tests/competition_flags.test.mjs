import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { PGlite } from '@electric-sql/pglite';
const id = n => `00000000-0000-0000-0000-${String(n).padStart(12,'0')}`;
const sql = readFileSync(new URL('../supabase/migrations/20261019074154_competition_international_flags.sql', import.meta.url), 'utf8');

test('competition flags migration preserves original assets, overrides, RLS and workspace isolation', async () => {
  const db = new PGlite();
  try {
    await db.exec(`create role authenticated;
      create table competitions(id uuid primary key,workspace_id uuid);
      create table teams(id uuid primary key,workspace_id uuid,logo_url text,alternate_logo_url text);
      create table sp_visual_themes(id uuid primary key,workspace_id uuid,competition_id uuid,
        published boolean,config jsonb,version integer,updated_at timestamptz default now());
      alter table competitions enable row level security; alter table teams enable row level security;
      create policy comp_read on competitions for select to authenticated using(workspace_id=nullif(current_setting('test.workspace',true),'')::uuid);
      create policy comp_write on competitions for update to authenticated using(workspace_id=nullif(current_setting('test.workspace',true),'')::uuid and current_setting('test.role',true)='manager');
      create policy team_read on teams for select to authenticated using(workspace_id=nullif(current_setting('test.workspace',true),'')::uuid);
      create policy team_write on teams for update to authenticated using(workspace_id=nullif(current_setting('test.workspace',true),'')::uuid and current_setting('test.role',true)='manager');
      grant select,update on competitions,teams to authenticated;`);
    for(const [n,workspace] of [[1,10],[2,10],[3,20]]){
      await db.query('insert into competitions values($1,$2)',[id(n),id(workspace)]);
      await db.query('insert into teams values($1,$2,$3,$4)',[id(n),id(workspace),'crest-'+n,'alternate-'+n]);
    }
    const theme = async (n, workspace, competition, international, flags, published=true) =>
      db.query('insert into sp_visual_themes(id,workspace_id,competition_id,published,config,version) values($1,$2,$3,$4,$5,1)',
        [id(n),id(workspace),competition ? id(competition) : null,published,JSON.stringify({appearance:{team_identity:{international,flags}}})]);
    await theme(100,10,null,true,{[id(1)]:'https://assets.test/one.svg',[id(3)]:'https://malicious.test/cross-workspace.svg'});
    await theme(101,10,2,false,{});
    await theme(102,20,null,false,{[id(3)]:'https://assets.test/three.svg'});
    const policies = (await db.query('select * from pg_policies order by tablename,policyname')).rows;
    await db.exec(sql);
    assert.deepEqual((await db.query('select is_international from competitions order by id')).rows.map(r=>r.is_international),[true,false,false]);
    assert.deepEqual((await db.query('select flag_url from teams order by id')).rows.map(r=>r.flag_url),['https://assets.test/one.svg',null,'https://assets.test/three.svg']);
    assert.deepEqual((await db.query('select logo_url,alternate_logo_url from teams order by id')).rows.map(r=>[r.logo_url,r.alternate_logo_url]),[['crest-1','alternate-1'],['crest-2','alternate-2'],['crest-3','alternate-3']]);
    assert.deepEqual((await db.query('select * from pg_policies order by tablename,policyname')).rows,policies);
    await db.query('update competitions set is_international=false where id=$1',[id(1)]);
    await db.exec(sql);
    assert.equal((await db.query('select is_international from competitions where id=$1',[id(1)])).rows[0].is_international,false);
    await db.query("select set_config('test.workspace',$1,false)",[id(10)]);
    await db.exec("select set_config('test.role','producer',false);set role authenticated;");
    assert.equal((await db.query('select * from teams')).rows.length,2);
    assert.equal((await db.query('update teams set flag_url=$1 where id=$2 returning id',['https://assets.test/changed.svg',id(1)])).rows.length,0);
    await db.exec("reset role;select set_config('test.role','manager',false);set role authenticated;");
    assert.equal((await db.query('update competitions set is_international=true where id=$1 returning id',[id(2)])).rows.length,1);
    assert.equal((await db.query('update teams set flag_url=$1 where id=$2 returning id',['https://assets.test/changed.svg',id(3)])).rows.length,0);
  } finally { await db.close(); }
});
