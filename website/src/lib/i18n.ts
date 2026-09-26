export type Lang = 'es' | 'en';

const esToEn: Record<string, string> = {
  '/': '/en/',
  '/live': '/en/live',
  '/manager': '/en/manager',
  '/cuenta': '/en/account',
  '/aviso-legal': '/en/legal-notice',
  '/privacidad': '/en/privacy',
  '/cookies': '/en/cookies',
  '/condiciones': '/en/terms'
};

const enToEs: Record<string, string> = Object.fromEntries(
  Object.entries(esToEn).map(([es, en]) => [en.replace(/\/$/, '') || '/', es])
);

export function normalisePath(pathname: string): string {
  if (pathname === '/') return '/';
  return pathname.replace(/\/$/, '');
}

export function getLang(pathname: string): Lang {
  const path = normalisePath(pathname);
  return path === '/en' || path.startsWith('/en/') ? 'en' : 'es';
}

export function switchLanguagePath(pathname: string, target: Lang): string {
  const path = normalisePath(pathname);

  if (target === 'en') {
    return esToEn[path] ?? `/en${path === '/' ? '/' : path}`;
  }

  const exact = enToEs[path];
  if (exact) return exact;

  const withoutPrefix = path.replace(/^\/en(?=\/|$)/, '');
  return withoutPrefix || '/';
}

export function getAlternates(pathname: string) {
  const lang = getLang(pathname);

  if (lang === 'es') {
    return {
      es: normalisePath(pathname),
      en: switchLanguagePath(pathname, 'en')
    };
  }

  return {
    es: switchLanguagePath(pathname, 'es'),
    en: normalisePath(pathname)
  };
}
