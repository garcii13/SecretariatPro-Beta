import { flushSync, mount } from 'svelte';
import App from './App.svelte';
import { BroadcastMotion } from './motion';
import './studio.css';
// Keep the proven state/data/identity adapter shared with the reference renderer.
// Display ownership belongs to the components; dynamic lists are adapter islands.
import '../../script.js';

try {
  const target = document.getElementById('broadcast-root');
  if (!target) throw new Error('Missing broadcast root');
  window.SPBroadcastMotion = BroadcastMotion;
  mount(App, { target });
  flushSync();
  document.body.classList.add('broadcast-studio');
  window.startSecretariatOverlay();
  window.secretariatStudioReady = true;
  window.dispatchEvent(new Event('secretariat:studio-ready'));
} catch (error) {
  // Preserve cue previews and every query parameter if boot fails.
  console.error('Broadcast renderer startup failed', error);
  const fallback = new URL('/overlay.html', location.href);
  fallback.search = location.search;
  fallback.searchParams.set('renderer', 'legacy');
  location.replace(fallback);
}
