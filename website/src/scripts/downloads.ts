import { detectInstaller, platforms } from '../lib/download-platform.mjs';

const labels: Record<string, string> = {
  'windows-x64': 'Windows · x64',
  'macos-arm64': 'macOS · Apple Silicon (M1, M2, M3, M4…)',
  'macos-x86_64': 'macOS · Intel'
};

for (const root of document.querySelectorAll<HTMLElement>('[data-downloads]')) {
  const es = root.dataset.lang === 'es';
  const cards = [...root.querySelectorAll<HTMLElement>('[data-download-card]')];
  const status = root.querySelector<HTMLElement>('[data-detection-status]');
  let manuallySelected = false;

  function choose(card: HTMLElement, platform: string) {
    const select = card.querySelector<HTMLSelectElement>('select')!;
    const main = card.querySelector<HTMLAnchorElement>('[data-download-main]')!;
    const source = card.querySelector<HTMLAnchorElement>(`[data-platform="${platform}"]`);
    select.value = platforms.includes(platform) ? platform : '';
    if (!source) {
      main.hidden = true;
      main.removeAttribute('href');
      card.querySelector<HTMLElement>('[data-download-meta]')!.textContent = '';
      return;
    }
    main.href = source.href;
    main.textContent = `${es ? 'Descargar para' : 'Download for'} ${labels[platform]}`;
    main.hidden = false;
    card.querySelector<HTMLElement>('[data-download-meta]')!.textContent = source.dataset.meta || '';
  }

  for (const card of cards) {
    card.querySelector<HTMLElement>('[data-download-picker]')!.hidden = false;
    card.querySelector<HTMLSelectElement>('select')!.addEventListener('change', (event) => {
      manuallySelected = true;
      choose(card, (event.target as HTMLSelectElement).value);
    });
  }
  // Manual links work immediately, even if the browser never resolves hints.
  void Promise.race([
    detectInstaller(navigator),
    new Promise<null>((resolve) => window.setTimeout(() => resolve(null), 1500))
  ]).then((platform) => {
    if (manuallySelected) return;
    if (platform) for (const card of cards) choose(card, platform);
    if (status) status.textContent = platform
      ? `${es ? 'Detectado' : 'Detected'}: ${labels[platform]}. ${es ? 'Puedes elegir otra versión.' : 'You can choose another version.'}`
      : (es ? 'Selecciona tu equipo. En Mac: menú Apple  → Acerca de este Mac → Chip o Procesador.'
        : 'Choose your computer. On Mac: Apple menu  → About This Mac → Chip or Processor.');
  });
}
