import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { PGlite } from '@electric-sql/pglite';

const id = n => `00000000-0000-0000-0000-${String(n).padStart(12, '0')}`;
test('real PostgreSQL invitation function preserves owner, suspension, roles and tenant boundaries', async () => {
  const db = new PGlite();
  try {
    await db.exec(`
      create role anon; create role authenticated;
      create schema auth;
      create function auth.uid() returns uuid language sql as $$
        select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
      create table auth.users(id uuid primary key, email_confirmed_at timestamptz);
      create table sp_workspaces(id uuid primary key, owner_user_id uuid);
      create table sp_workspace_members(
        workspace_id uuid references sp_workspaces, user_id uuid references auth.users,
        role text not null check (role in ('owner','competition_manager','producer')),
        status text not null default 'active' check (status in ('active','suspended','invited')),
        invited_by uuid, joined_at timestamptz not null default now(),
        created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
        primary key(workspace_id,user_id));
      create function sp_has_workspace_role(target_workspace uuid, accepted_roles text[])
        returns boolean language sql as $$ select exists(select 1 from sp_workspace_members
          where workspace_id=target_workspace and user_id=auth.uid()
          and status='active' and role=any(accepted_roles)) $$;
    `);
    await db.exec(readFileSync(new URL('../SUPABASE_AUDIT_INVITATIONS.sql', import.meta.url), 'utf8'));
    for (const n of [1,2,3,4,5,6]) await db.query('insert into auth.users values ($1,$2)', [id(n), n===4?null:'2026-10-01']);
    await db.query('insert into sp_workspaces values ($1,$2),($3,$4)', [id(10),id(1),id(20),id(6)]);
    for (const [user,role,status] of [[1,'owner','active'],[2,'competition_manager','active'],[3,'producer','suspended'],[5,'producer','active']]) {
      await db.query('insert into sp_workspace_members(workspace_id,user_id,role,status) values($1,$2,$3,$4)', [id(10),id(user),role,status]);
    }
    const asUser = user => db.query("select set_config('request.jwt.claim.sub',$1,false)", [user ? id(user) : '']);
    const invite = async (workspace, user, role='producer') => (await db.query(
      'select sp_invite_workspace_member($1,$2,$3) result', [id(workspace),id(user),role])).rows[0].result;
    await asUser(2);
    for (const [user,expectedRole,expectedStatus] of [[1,'owner','active'],[2,'competition_manager','active'],[3,'producer','suspended']]) {
      const before=(await db.query('select * from sp_workspace_members where workspace_id=$1 and user_id=$2',[id(10),id(user)])).rows[0];
      const result=await invite(10,user);
      assert.equal(result.created,false); assert.equal(result.membership.role,expectedRole);
      assert.equal(result.membership.status,expectedStatus);
      const after=(await db.query('select * from sp_workspace_members where workspace_id=$1 and user_id=$2',[id(10),id(user)])).rows[0];
      assert.deepEqual(after,before,'a repeated invitation must not write any membership field');
    }
    const added=await invite(10,4,'competition_manager');
    assert.equal(added.created,true); assert.equal(added.membership.status,'invited');
    assert.equal((await invite(10,4,'producer')).membership.role,'competition_manager');
    await assert.rejects(invite(20,4),/rol no permite/);
    await assert.rejects(invite(10,6,'owner'),/Rol no válido/);
    await asUser(5); await assert.rejects(invite(10,6),/rol no permite/);
    await asUser(3); await assert.rejects(invite(10,6),/rol no permite/);
    await asUser(null); await assert.rejects(invite(10,6),/rol no permite/);
    await asUser(1);
    assert.equal((await invite(10,6)).membership.status,'active');
    // Owner row missing: never recreate it with a weaker role.
    await db.query('update sp_workspaces set owner_user_id=$1 where id=$2',[id(4),id(20)]);
    await db.query("insert into sp_workspace_members(workspace_id,user_id,role) values($1,$2,'competition_manager')",[id(20),id(1)]);
    await assert.rejects(invite(20,4),/propietario/);
    const acl=(await db.query("select has_function_privilege('anon','sp_invite_workspace_member(uuid,uuid,text)','EXECUTE') anon, has_function_privilege('authenticated','sp_invite_workspace_member(uuid,uuid,text)','EXECUTE') auth")).rows[0];
    assert.equal(acl.anon,false); assert.equal(acl.auth,true);
  } finally { await db.close(); }
});
