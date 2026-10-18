import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { PGlite } from '@electric-sql/pglite';
const id = n => `00000000-0000-0000-0000-${String(n).padStart(12,'0')}`;

test('direct authenticated SQL cannot escalate roles, change owner, move memberships or revive invitations', async () => {
  const db=new PGlite();
  try {
    await db.exec(`
      create role anon; create role authenticated;
      create schema auth; grant usage on schema auth to authenticated;
      create function auth.uid() returns uuid language sql as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
      create table auth.users(id uuid primary key,email text,email_confirmed_at timestamptz,raw_user_meta_data jsonb default '{}');
      create table sp_workspaces(id uuid primary key,owner_user_id uuid references auth.users on delete restrict,sport_mode text default 'floorball');
      create table sp_workspace_members(workspace_id uuid references sp_workspaces on delete cascade,
        user_id uuid references auth.users on delete cascade, role text not null, status text not null default 'active',
        invited_by uuid,joined_at timestamptz not null default now(),created_at timestamptz not null default now(),updated_at timestamptz not null default now(),
        primary key(workspace_id,user_id));
      create table scoreboard_operators(id uuid primary key,email text,display_name text,workspace_id uuid);
      create function sp_has_workspace_role(target_workspace uuid,accepted_roles text[]) returns boolean language sql security definer set search_path=public as $$
        select exists(select 1 from sp_workspace_members where workspace_id=target_workspace and user_id=auth.uid() and status='active' and role=any(accepted_roles)) $$;
      create function sp_is_workspace_member(target_workspace uuid) returns boolean language sql security definer set search_path=public as $$
        select exists(select 1 from sp_workspace_members where workspace_id=target_workspace and user_id=auth.uid() and status='active') $$;
      create function sync_scoreboard_operator() returns trigger language plpgsql as $$ begin return new; end $$;
      create function set_updated_at() returns trigger language plpgsql as $$ begin return new; end $$;
      create function sp_set_updated_at() returns trigger language plpgsql as $$ begin return new; end $$;
      create function sp_subscription_retention() returns trigger language plpgsql as $$ begin return new; end $$;
      create function sp_asset_workspace_id(text) returns uuid language sql as $$ select null::uuid $$;
      alter table sp_workspaces enable row level security;
      alter table sp_workspace_members enable row level security;
      create policy workspace_read on sp_workspaces for select to authenticated using(sp_is_workspace_member(id));
      create policy workspace_manage on sp_workspaces for update to authenticated
        using(sp_has_workspace_role(id,array['owner','competition_manager'])) with check(sp_has_workspace_role(id,array['owner','competition_manager']));
      create policy members_read on sp_workspace_members for select to authenticated using(user_id=auth.uid() or sp_has_workspace_role(workspace_id,array['owner','competition_manager']));
      create policy members_manage on sp_workspace_members for all to authenticated
        using(sp_has_workspace_role(workspace_id,array['owner','competition_manager'])) with check(sp_has_workspace_role(workspace_id,array['owner','competition_manager']));
      grant all on sp_workspaces,sp_workspace_members to authenticated;
    `);
    await db.exec(readFileSync(new URL('../SUPABASE_AUDIT_INVITATIONS.sql',import.meta.url),'utf8'));
    await db.exec(readFileSync(new URL('../SUPABASE_AUDIT_MEMBERSHIP_GUARDS.sql',import.meta.url),'utf8'));
    for(const n of [1,2,3,4,5])await db.query('insert into auth.users(id,email,email_confirmed_at) values($1,$2,now())',[id(n),`audit${n}@example.invalid`]);
    await db.query('insert into sp_workspaces(id,owner_user_id) values($1,$2),($3,$4)',[id(10),id(1),id(20),id(5)]);
    for(const [user,role,status] of [[1,'owner','active'],[2,'competition_manager','active'],[3,'producer','active'],[4,'producer','suspended']])
      await db.query('insert into sp_workspace_members(workspace_id,user_id,role,status) values($1,$2,$3,$4)',[id(10),id(user),role,status]);
    await db.query("insert into sp_workspace_members(workspace_id,user_id,role) values($1,$2,'owner')",[id(20),id(5)]);
    const asUser=async n=>{await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id(n)]);await db.exec('set role authenticated');};
    await asUser(2);
    await assert.rejects(db.query("update sp_workspace_members set role='owner' where workspace_id=$1 and user_id=$2",[id(10),id(2)]),/propietario/);
    await assert.rejects(db.query("update sp_workspace_members set status='suspended' where workspace_id=$1 and user_id=$2",[id(10),id(1)]),/propietario/);
    await assert.rejects(db.query('delete from sp_workspace_members where workspace_id=$1 and user_id=$2',[id(10),id(1)]),/propietario/);
    await assert.rejects(db.query('update sp_workspaces set owner_user_id=$1 where id=$2',[id(2),id(10)]),/propietario/);
    await assert.rejects(db.query("update sp_workspaces set sport_mode='handball' where id=$1",[id(10)]),/propietario/);
    await assert.rejects(db.query('update sp_workspace_members set user_id=$1 where workspace_id=$2 and user_id=$3',[id(5),id(10),id(3)]),/identidad/);
    assert.equal((await db.query('select * from sp_workspaces where id=$1',[id(20)])).rows.length,0);
    const suspended=(await db.query("select sp_add_existing_member($1,'audit4@example.invalid','competition_manager') result",[id(10)])).rows[0].result;
    assert.equal(suspended.status,'suspended');assert.equal(suspended.role,'producer');
    const owner=(await db.query("select sp_add_existing_member($1,'audit1@example.invalid','producer') result",[id(10)])).rows[0].result;
    assert.equal(owner.role,'owner');assert.equal(owner.status,'active');
    await db.query("update sp_workspace_members set role='competition_manager' where workspace_id=$1 and user_id=$2",[id(10),id(3)]);
    await asUser(1);
    await db.query("update sp_workspaces set sport_mode='handball' where id=$1",[id(10)]);
    await db.exec('reset role');
    await db.query("select set_config('request.jwt.claim.sub','',false)");
    // Authorized parent deletion still cascades: the guard must not strand its owner row.
    await db.query('delete from sp_workspaces where id=$1',[id(10)]);
    assert.equal((await db.query('select * from sp_workspace_members where workspace_id=$1',[id(10)])).rows.length,0);
    assert.equal((await db.query("select has_function_privilege('anon','sp_add_existing_member(uuid,text,text)','execute') ok")).rows[0].ok,false);
  }finally{await db.close();}
});
