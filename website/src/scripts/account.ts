import { createClient, type User } from '@supabase/supabase-js';
import { accountFlow, errorMessage, hasAuthLinkError, retrySessionRequest } from '../lib/account-flow.mjs';

const roots = document.querySelectorAll<HTMLElement>('[data-account-portal]');

for (const root of roots) {
  const lang = root.dataset.lang === 'en' ? 'en' : 'es';
  const es = lang === 'es';
  const url = root.dataset.supabaseUrl ?? '';
  const key = root.dataset.supabaseKey ?? '';
  const client = createClient(url, key, {
    auth: { detectSessionInUrl: true, persistSession: true, autoRefreshToken: true }
  });

  const one = <T extends Element>(selector: string) => root.querySelector<T>(selector);
  const loading = one<HTMLElement>('[data-account-loading]');
  const signedOut = one<HTMLElement>('[data-account-signed-out]');
  const signedIn = one<HTMLElement>('[data-account-signed-in]');
  const notice = one<HTMLElement>('[data-account-message]');
  const loginForm = one<HTMLFormElement>('[data-login-form]');
  const resetForm = one<HTMLFormElement>('[data-reset-form]');
  const profileForm = one<HTMLFormElement>('[data-profile-form]');
  const passwordForm = one<HTMLFormElement>('[data-password-form]');
  const memberships = one<HTMLElement>('[data-memberships]');
  const avatar = one<HTMLElement>('[data-avatar]');
  let currentUser: User | null = null;
  let flow = accountFlow(location);
  let linkError = hasAuthLinkError(location);
  let renderRevision = 0;
  let sessionKey: string | null = null;

  const text = {
    unexpected: es ? 'No se pudo completar la operación.' : 'The operation could not be completed.',
    loginOk: es ? 'Sesión iniciada.' : 'Signed in.',
    resetSent: es ? 'Revisa tu correo para continuar.' : 'Check your email to continue.',
    profileSaved: es ? 'Perfil actualizado.' : 'Profile updated.',
    passwordSaved: es ? 'Contraseña guardada.' : 'Password saved.',
    mismatch: es ? 'Las contraseñas no coinciden.' : 'Passwords do not match.',
    avatarLarge: es ? 'La imagen no puede superar 8 MB.' : 'The image cannot exceed 8 MB.',
    signedOut: es ? 'Sesión cerrada.' : 'Signed out.',
    noMemberships: es ? 'Todavía no perteneces a ningún espacio de trabajo.' : 'You do not belong to a workspace yet.',
    inviteAccepted: es ? 'Invitación aceptada. Ya puedes usar SecretariatPro.' : 'Invitation accepted. You can now use SecretariatPro.',
    recoveryReady: es ? 'Sesión activa. Guarda tu nueva contraseña para completar la recuperación.' : 'Signed in. Save your new password to complete recovery.',
    recoveryTitle: es ? 'Recupera tu contraseña' : 'Reset your password',
    recoveryHelp: es ? 'Elige una nueva contraseña de al menos 8 caracteres.' : 'Choose a new password with at least 8 characters.',
    workspaceError: es ? 'No se pudieron cargar tus espacios de trabajo: ' : 'Your workspaces could not be loaded: ',
    linkError: es ? 'No se ha podido validar el enlace. Puede haber caducado o haberse utilizado. Solicita otro enlace; si ya tienes una sesión activa, puedes cambiar tu contraseña desde este formulario.' : 'The link could not be verified. It may have expired or already been used. Request another link; if you already have an active session, you can change your password using this form.',
    createPassword: es ? 'Crea tu contraseña' : 'Create your password',
    createPasswordHelp: es ? 'Elige una contraseña de al menos 8 caracteres para completar la invitación.' : 'Choose a password of at least 8 characters to complete your invitation.'
  };

  function showMessage(message = '', kind: 'ok' | 'error' = 'ok') {
    if (!notice) return;
    notice.textContent = message;
    notice.dataset.kind = kind;
    notice.hidden = !message;
  }

  function setBusy(form: HTMLFormElement | null, busy: boolean) {
    if (!form) return;
    for (const control of form.querySelectorAll<HTMLInputElement | HTMLButtonElement>('input, button')) {
      control.disabled = busy;
    }
    form.dataset.busy = String(busy);
  }

  function initials(value: string) {
    return value.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase() ?? '').join('') || '?';
  }

  function profileName(user: User) {
    return String(user.user_metadata?.display_name || user.user_metadata?.full_name || user.email?.split('@')[0] || (es ? 'Usuario' : 'User'));
  }

  function renderAvatar(user: User) {
    if (!avatar) return;
    avatar.replaceChildren();
    const avatarUrl = String(user.user_metadata?.avatar_url || '');
    if (avatarUrl) {
      const image = document.createElement('img');
      image.src = avatarUrl;
      image.alt = es ? 'Foto de perfil' : 'Profile photo';
      avatar.append(image);
    } else {
      const fallback = document.createElement('span');
      fallback.textContent = initials(profileName(user));
      avatar.append(fallback);
    }
  }

  async function acceptInvitations() {
    const { data, error } = await retrySessionRequest(client.auth, () => client.rpc('sp_accept_my_invitations'));
    if (error) throw error;
    return Number(data || 0);
  }

  async function renderMemberships(user: User, revision = renderRevision) {
    if (!memberships) return;
    memberships.replaceChildren();
    const { data: memberRows, error: memberError } = await retrySessionRequest(client.auth, () => client
      .from('sp_workspace_members')
      .select('workspace_id,role,status,joined_at')
      .eq('user_id', user.id)
      .order('joined_at', { ascending: true }));
    if (memberError) throw memberError;

    const ids = (memberRows ?? []).map((row) => String(row.workspace_id));
    let workspaces: Array<{ id: string; name: string }> = [];
    if (ids.length) {
      const { data, error } = await retrySessionRequest(client.auth, () => client.from('sp_workspaces').select('id,name').in('id', ids).order('name'));
      if (error) throw error;
      workspaces = data ?? [];
    }
    if (revision !== renderRevision || currentUser?.id !== user.id) return;
    const nameById = new Map(workspaces.map((workspace) => [String(workspace.id), workspace.name]));

    if (!memberRows?.length) {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = text.noMemberships;
      memberships.append(empty);
      return;
    }

    const roleNames: Record<string, string> = es
      ? { owner: 'Propietario', competition_manager: 'Manager de competición', producer: 'Realizador' }
      : { owner: 'Owner', competition_manager: 'Competition manager', producer: 'Producer' };
    const list = document.createElement('div');
    list.className = 'workspace-list';
    for (const row of memberRows) {
      const item = document.createElement('div');
      item.className = 'workspace-item';
      const copy = document.createElement('div');
      const name = document.createElement('strong');
      name.textContent = nameById.get(String(row.workspace_id)) || (es ? 'Espacio de trabajo' : 'Workspace');
      const status = document.createElement('span');
      status.textContent = row.status === 'active' ? (es ? 'Activo' : 'Active') : String(row.status || '');
      copy.append(name, status);
      const role = document.createElement('span');
      role.className = 'workspace-role';
      role.textContent = roleNames[String(row.role)] || String(row.role || '');
      item.append(copy, role);
      list.append(item);
    }
    memberships.append(list);
  }

  async function renderSession(user: User | null) {
    const revision = ++renderRevision;
    currentUser = user;
    memberships?.replaceChildren();
    if (loading) loading.hidden = true;
    if (signedOut) signedOut.hidden = Boolean(user);
    if (signedIn) signedIn.hidden = !user;
    if (linkError) showMessage(text.linkError, 'error');
    if (!user) return;

    one<HTMLElement>('[data-profile-name]')!.textContent = profileName(user);
    one<HTMLElement>('[data-profile-email]')!.textContent = user.email ?? '';
    const displayName = profileForm?.elements.namedItem('display_name') as HTMLInputElement | null;
    if (displayName) displayName.value = profileName(user);
    renderAvatar(user);

    one<HTMLElement>('[data-password-title]')!.textContent = flow === 'recovery' ? text.recoveryTitle : flow === 'invite' ? text.createPassword : (es ? 'Cambiar contraseña' : 'Change password');
    one<HTMLElement>('[data-password-help]')!.textContent = flow === 'recovery' ? text.recoveryHelp : flow === 'invite' ? text.createPasswordHelp : (es ? 'Usa al menos 8 caracteres.' : 'Use at least 8 characters.');
    if (flow === 'recovery' && !linkError) showMessage(text.recoveryReady);

    try {
      const accepted = flow === 'recovery' ? 0 : await acceptInvitations();
      if (revision !== renderRevision) return;
      await renderMemberships(user, revision);
      if (accepted > 0 && revision === renderRevision && !linkError) showMessage(text.inviteAccepted);
    } catch (error) {
      if (revision !== renderRevision || !memberships) return;
      const message = document.createElement('p');
      message.setAttribute('role', 'status');
      message.textContent = text.workspaceError + errorMessage(error, text.unexpected);
      memberships.replaceChildren(message);
    }
  }

  loginForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    setBusy(loginForm, true);
    showMessage();
    try {
      const email = (loginForm.elements.namedItem('email') as HTMLInputElement).value.trim();
      const password = (loginForm.elements.namedItem('password') as HTMLInputElement).value;
      const { data, error } = await client.auth.signInWithPassword({ email, password });
      if (error) throw error;
      flow = null;
      linkError = false;
      await renderSession(data.user);
      showMessage(text.loginOk);
    } catch (error) {
      showMessage(errorMessage(error, text.unexpected), 'error');
    } finally {
      setBusy(loginForm, false);
    }
  });

  resetForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    setBusy(resetForm, true);
    showMessage();
    try {
      const email = (resetForm.elements.namedItem('email') as HTMLInputElement).value.trim();
      const accountPath = lang === 'en' ? '/en/account?type=recovery' : '/cuenta?type=recovery';
      const { error } = await client.auth.resetPasswordForEmail(email, { redirectTo: location.origin + accountPath });
      if (error) throw error;
      showMessage(text.resetSent);
    } catch (error) {
      showMessage(errorMessage(error, text.unexpected), 'error');
    } finally {
      setBusy(resetForm, false);
    }
  });

  profileForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!currentUser) return;
    setBusy(profileForm, true);
    showMessage();
    try {
      const displayName = (profileForm.elements.namedItem('display_name') as HTMLInputElement).value.trim();
      const file = (profileForm.elements.namedItem('avatar') as HTMLInputElement).files?.[0];
      let avatarUrl = String(currentUser.user_metadata?.avatar_url || '');
      if (file) {
        if (file.size > 8 * 1024 * 1024) throw new Error(text.avatarLarge);
        const extension = file.type === 'image/png' ? 'png' : file.type === 'image/webp' ? 'webp' : 'jpg';
        const path = `${currentUser.id}/profile.${extension}`;
        const { error: uploadError } = await client.storage.from('avatars').upload(path, file, {
          upsert: true,
          contentType: file.type,
          cacheControl: '3600'
        });
        if (uploadError) throw uploadError;
        avatarUrl = `${client.storage.from('avatars').getPublicUrl(path).data.publicUrl}?v=${Date.now()}`;
        const oldPaths = ['jpg', 'png', 'webp'].filter((item) => item !== extension).map((item) => `${currentUser!.id}/profile.${item}`);
        await client.storage.from('avatars').remove(oldPaths);
      }
      const metadata = { ...currentUser.user_metadata, display_name: displayName, full_name: displayName, avatar_url: avatarUrl };
      const { data, error } = await client.auth.updateUser({ data: metadata });
      if (error) throw error;
      currentUser = data.user;
      await client.from('scoreboard_operators').update({ display_name: displayName, email: currentUser.email }).eq('id', currentUser.id);
      await renderSession(currentUser);
      showMessage(text.profileSaved);
      (profileForm.elements.namedItem('avatar') as HTMLInputElement).value = '';
    } catch (error) {
      showMessage(errorMessage(error, text.unexpected), 'error');
    } finally {
      setBusy(profileForm, false);
    }
  });

  one<HTMLButtonElement>('[data-remove-avatar]')?.addEventListener('click', async () => {
    if (!currentUser) return;
    showMessage();
    try {
      const paths = ['jpg', 'png', 'webp'].map((extension) => `${currentUser!.id}/profile.${extension}`);
      await client.storage.from('avatars').remove(paths);
      const metadata = { ...currentUser.user_metadata };
      delete metadata.avatar_url;
      const { data, error } = await client.auth.updateUser({ data: metadata });
      if (error) throw error;
      currentUser = data.user;
      await renderSession(currentUser);
      showMessage(text.profileSaved);
    } catch (error) {
      showMessage(errorMessage(error, text.unexpected), 'error');
    }
  });

  passwordForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    setBusy(passwordForm, true);
    showMessage();
    try {
      const password = (passwordForm.elements.namedItem('password') as HTMLInputElement).value;
      const confirmation = (passwordForm.elements.namedItem('confirm_password') as HTMLInputElement).value;
      if (password !== confirmation) throw new Error(text.mismatch);
      const { error } = await client.auth.updateUser({ password });
      if (error) throw error;
      flow = null;
      linkError = false;
      history.replaceState({}, '', lang === 'en' ? '/en/account' : '/cuenta');
      passwordForm.reset();
      showMessage(text.passwordSaved);
      // Workspace failures must not turn an already saved password into a failed operation.
      if (currentUser) void renderSession(currentUser);
    } catch (error) {
      showMessage(errorMessage(error, text.unexpected), 'error');
    } finally {
      setBusy(passwordForm, false);
    }
  });

  one<HTMLButtonElement>('[data-signout]')?.addEventListener('click', async () => {
    await client.auth.signOut();
    currentUser = null;
    await renderSession(null);
    showMessage(text.signedOut);
  });

  client.auth.onAuthStateChange((event, session) => {
    if (event === 'PASSWORD_RECOVERY') flow = 'recovery';
    if (event === 'TOKEN_REFRESHED' && currentUser?.id === session?.user.id) return;
    const key = session ? `${session.user.id}:${session.access_token}` : '';
    if (key === sessionKey && event !== 'PASSWORD_RECOVERY' && event !== 'USER_UPDATED') return;
    sessionKey = key;
    // Run outside Supabase's auth lock. INITIAL_SESSION also covers persisted sessions.
    window.setTimeout(() => {
      if (sessionKey === key) void renderSession(session?.user ?? null);
    }, 0);
  });
}
