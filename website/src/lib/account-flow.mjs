export function accountFlow(location) {
  const type = new URLSearchParams(location.hash.replace(/^#/, '')).get('type')
    || new URLSearchParams(location.search).get('type');
  return type === 'recovery' || type === 'invite' ? type : null;
}

export function errorMessage(error, fallback) {
  return typeof error?.message === 'string' && error.message.trim() ? error.message : fallback;
}

export function hasAuthLinkError(location) {
  return [location.search, location.hash.replace(/^#/, '')].some((part) => {
    const params = new URLSearchParams(part);
    return params.has('error') || params.has('error_code');
  });
}

// The invitation RPC is idempotent and the other callers only read memberships.
// Retry once after refreshing a rejected JWT; never retry permission or SQL errors.
export async function retrySessionRequest(auth, request) {
  const result = await request();
  if (!['PGRST301', 'PGRST303'].includes(result.error?.code)) return result;
  const refreshed = await auth.refreshSession();
  if (refreshed.error || !refreshed.data.session) {
    return { data: null, error: refreshed.error || result.error };
  }
  return request();
}
