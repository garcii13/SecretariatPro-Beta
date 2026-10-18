import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  build: {
    // Local, bundled assets: OBS and installed apps need no CDN or Node runtime.
    outDir: '../overlay_studio',
    emptyOutDir: true,
    target: 'chrome100',
    lib: { entry: 'src/main.ts', name: 'SecretariatBroadcast', formats: ['iife'], fileName: () => 'studio.js', cssFileName: 'studio' },
  },
});
