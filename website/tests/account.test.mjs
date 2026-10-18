import { test } from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';
import { accountFlow, errorMessage, retrySessionRequest } from '../src/lib/account-flow.mjs';

const user = { id: 'test-user', email: 'test@example.invalid', user_metadata: {} };
const session = { user, access_token: 'test-only-session' };
const jwtError = { code: 'PGRST303', message: 'JWT expired' };
const bundle = build({
  entryPoints: [new URL('../src/scripts/account.ts', import.meta.url).pathname],
  bundle: true, write: false, format: 'iife', platform: 'browser',
  plugins: [{ name: 'test-client', setup(builder) {
    builder.onResolve({ filter: /^@supabase\/supabase-js$/ }, () => ({ path: 'client', namespace: 'test' }));
    builder.onLoad({ filter: /.*/, namespace: 'test' }, () => ({ contents: 'export const createClient = () => globalThis.testClient;' }));
  } }]
}).then((result) => result.outputFiles[0].text);
const settle = () => new Promise((resolve) => setTimeout(resolve, 20));

async function portal(t, { query = '?type=recovery', lang = 'es', rpc, members, updateError = null } = {}) {
  const dom = new JSDOM(`<div data-account-portal data-lang="${lang}">
    <div data-account-loading></div><div data-account-message hidden></div>
    <div data-account-signed-out></div><div data-account-signed-in hidden>
    <div data-profile-name></div><div data-profile-email></div><div data-avatar></div>
    <h2 data-password-title></h2><p data-password-help></p>
    <form data-password-form><input name="password"><input name="confirm_password"><button>Save</button></form>
    <div data-memberships></div></div></div>`, {
    url: `https://example.invalid/cuenta${query}`, runScripts: 'outside-only'
  });
  t.after(() => dom.window.close());
  let callback;
  const calls = { rpc: 0, refresh: 0, update: 0, queries: 0 };
  const emit = (event, value = session) => callback(event, value);
  dom.window.testClient = {
    auth: {
      onAuthStateChange(fn) { callback = fn; },
      async refreshSession() { calls.refresh++; emit('TOKEN_REFRESHED', { ...session, access_token: 'fresh-test-only' }); return { data: { session }, error: null }; },
      async updateUser() { calls.update++; return { data: { user }, error: updateError }; }
    },
    async rpc() { calls.rpc++; return rpc ? rpc(calls.rpc) : { data: 0, error: null }; },
    from(table) {
      const request = {
        select() { return this; }, eq() { return this; }, in() { return this; }, order() { return this; },
        then(resolve, reject) {
          calls.queries++;
          return Promise.resolve(table === 'sp_workspace_members' && members ? members() : { data: [], error: null }).then(resolve, reject);
        }
      };
      return request;
    }
  };
  dom.window.eval(await bundle);
  const one = (selector) => dom.window.document.querySelector(selector);
  async function savePassword() {
    const form = one('form');
    form.elements.namedItem('password').value = 'dummy-test-password';
    form.elements.namedItem('confirm_password').value = 'dummy-test-password';
    form.dispatchEvent(new dom.window.Event('submit', { cancelable: true, bubbles: true }));
    await settle();
  }
  return { dom, calls, emit, one, savePassword };
}

test('recovery and invitation URL intents remain distinct; plain API errors retain their message', () => {
  assert.equal(accountFlow({ search: '?type=recovery', hash: '' }), 'recovery');
  assert.equal(accountFlow({ search: '', hash: '#type=invite' }), 'invite');
  assert.equal(errorMessage({ message: 'Permission denied' }, 'generic'), 'Permission denied');
});

test('recovery renders for an existing session, without accepting or announcing an invitation', async (t) => {
  const p = await portal(t);
  p.emit('INITIAL_SESSION'); p.emit('SIGNED_IN'); await settle();
  assert.equal(p.calls.rpc, 0);
  assert.match(p.one('[data-password-title]').textContent, /Recupera/);
  assert.match(p.one('[data-account-message]').textContent, /nueva contraseña/);
  assert.equal(p.one('[data-account-signed-in]').hidden, false);
  assert.equal(p.calls.queries, 1);
});

test('a rejected JWT refreshes and retries once, without an auth-event render loop', async (t) => {
  const p = await portal(t, { query: '', rpc: (n) => n === 1 ? { error: jwtError } : { data: 0, error: null } });
  p.emit('INITIAL_SESSION'); await settle();
  assert.equal(p.calls.refresh, 1); assert.equal(p.calls.rpc, 2);
  assert.equal(p.one('[data-account-message]').hidden, true);
  assert.match(p.one('[data-memberships]').textContent, /Todavía no perteneces/);
});

test('persistent JWT rejection remains actionable and never retries indefinitely', async (t) => {
  const p = await portal(t, { query: '', rpc: () => ({ error: jwtError }) });
  p.emit('INITIAL_SESSION'); await settle();
  assert.equal(p.calls.rpc, 2); assert.equal(p.calls.refresh, 1);
  assert.match(p.one('[data-memberships]').textContent, /JWT expired/);
});

test('successful password save stays successful when the invitation RPC fails', async (t) => {
  const p = await portal(t, { rpc: () => ({ error: { code: '42501', message: 'Access denied' } }) });
  p.emit('PASSWORD_RECOVERY'); await settle(); await p.savePassword();
  assert.equal(p.calls.update, 1);
  assert.match(p.one('[data-account-message]').textContent, /Contraseña guardada/);
  assert.match(p.one('[data-memberships]').textContent, /Access denied/);
  assert.equal(p.calls.refresh, 0);
  assert.equal(p.dom.window.location.search, '');
});

test('a failed password update keeps the recovery form and shows the real auth error', async (t) => {
  const p = await portal(t, { updateError: { message: 'Password is too weak' } });
  p.emit('PASSWORD_RECOVERY'); await settle(); await p.savePassword();
  assert.equal(p.one('[data-account-message]').dataset.kind, 'error');
  assert.match(p.one('[data-account-message]').textContent, /Password is too weak/);
  assert.equal(p.dom.window.location.search, '?type=recovery');
});

test('an expired link cannot announce successful recovery merely because an older session exists', async (t) => {
  const p = await portal(t, { query: '?type=recovery#error=access_denied&error_code=otp_expired' });
  p.emit('INITIAL_SESSION'); await settle();
  assert.equal(p.one('[data-account-message]').dataset.kind, 'error');
  assert.match(p.one('[data-account-message]').textContent, /No se ha podido validar/);
  assert.equal(p.one('[data-account-signed-in]').hidden, false);
});

test('membership responses cannot repopulate private content after signout', async (t) => {
  let finish;
  const pending = new Promise((resolve) => { finish = resolve; });
  const p = await portal(t, { members: () => pending });
  p.emit('INITIAL_SESSION'); await settle(); p.emit('SIGNED_OUT', null); await settle();
  finish({ data: [{ workspace_id: 'private', role: 'owner', status: 'active' }], error: null }); await settle();
  assert.equal(p.one('[data-memberships]').textContent, '');
  assert.equal(p.one('[data-account-signed-in]').hidden, true);
});

test('an actual invitation acceptance is announced in English', async (t) => {
  const p = await portal(t, { query: '?type=invite', lang: 'en', rpc: () => ({ data: 1, error: null }) });
  p.emit('SIGNED_IN'); await settle();
  assert.match(p.one('[data-account-message]').textContent, /Invitation accepted/);
  assert.match(p.one('[data-password-title]').textContent, /Create your password/);
});

test('refresh failures are returned and permissions are never retried', async () => {
  let requests = 0, refreshes = 0;
  const auth = { async refreshSession() { refreshes++; return { data: { session: null }, error: { message: 'Sign in again' } }; } };
  const result = await retrySessionRequest(auth, async () => { requests++; return { error: jwtError }; });
  assert.equal(result.error.message, 'Sign in again'); assert.equal(requests, 1);
  await retrySessionRequest(auth, async () => ({ error: { code: '42501' } }));
  assert.equal(refreshes, 1);
});
