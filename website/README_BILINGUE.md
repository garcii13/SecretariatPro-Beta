# SecretariatPro — versión bilingüe ES / EN

Este paquete está preparado para copiarse **encima de tu proyecto Astro actual**.

## Importante

No sustituye ni elimina:

- `src/assets/`
- `public/media/`
- tus páginas españolas actuales
- `src/styles/global.css`

Por tanto, conserva exactamente las capturas, logos y vídeos que ya tienes.

## Qué añade o sustituye

Copia el contenido de este ZIP en la raíz del proyecto y permite sobrescribir:

- `astro.config.mjs`
- `src/components/Header.astro`
- `src/components/Footer.astro`
- `src/layouts/BaseLayout.astro`

Añade:

- `src/lib/i18n.ts`
- `src/styles/i18n.css`
- `src/pages/en/index.astro`
- `src/pages/en/live.astro`
- `src/pages/en/manager.astro`
- `src/pages/en/legal-notice.astro`
- `src/pages/en/privacy.astro`
- `src/pages/en/cookies.astro`
- `src/pages/en/terms.astro`

## Rutas

### Español
- `/`
- `/live`
- `/manager`
- `/aviso-legal`
- `/privacidad`
- `/cookies`
- `/condiciones`

### English
- `/en/`
- `/en/live`
- `/en/manager`
- `/en/legal-notice`
- `/en/privacy`
- `/en/cookies`
- `/en/terms`

## Selector de idioma

El header muestra:

`ES / EN`

y conserva la página equivalente:

- `/live` ↔ `/en/live`
- `/manager` ↔ `/en/manager`
- `/privacidad` ↔ `/en/privacy`
- etc.

## SEO

`BaseLayout.astro` incluye:

- `<html lang="es">` o `<html lang="en">`
- canonical
- `hreflang="es"`
- `hreflang="en"`
- `hreflang="x-default"`
- `og:locale`

## Imágenes y vídeos

Las páginas inglesas reutilizan **los mismos archivos** que las españolas.
No dupliques imágenes ni vídeos.

Por ejemplo:

`src/assets/livecaptura.png`

se utiliza tanto en `/live` como en `/en/live`.

El vídeo sigue usando:

`public/media/videomuestra.mp4`

## Ejecutar

```bash
npm install
npm run dev
```

Después prueba:

- http://localhost:4321/
- http://localhost:4321/en/
- http://localhost:4321/live
- http://localhost:4321/en/live

## Nota sobre el dominio

El proyecto bilingüe usa como `site`:

`https://secretariatproapp.com`

porque es el dominio indicado en los Astro españoles suministrados.
