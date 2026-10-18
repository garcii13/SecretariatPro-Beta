# SecretariatPro — Astro Website V5

Versión orientada a enseñar el producto durante la fase de desarrollo, sin precios ni captación comercial.

## Cambios
- Eliminados `/precios`, `/demo`, `/contacto` y páginas de checkout.
- Menú: Inicio / Live / Manager.
- Logo servido con `Image` de `astro:assets`.
- Galería automática de capturas reales usando `Image` de Astro.
- Vídeo de producto preparado y detectado automáticamente durante el build.
- Mantiene el diseño oscuro premium.

## Añadir capturas reales
Copia PNG, JPG, WebP o AVIF a:

`src/assets/product/`

Por ejemplo:
- `live-main.png`
- `manager-equipos.png`
- `overlay-partido.webp`

`ProductGallery.astro` las detecta automáticamente y las sirve con `Image` de Astro, responsive y optimizadas. No hace falta escribir una etiqueta `<img>` manual.

## Añadir un vídeo
Copia un MP4 a:

`public/media/secretariatpro-demo.mp4`

La web detecta el archivo al compilar. Si no existe, muestra un placeholder elegante en vez de un reproductor roto.

Recomendado: H.264, 720p/1080p, 30 fps y 30–60 segundos.

## Ejecutar
```bash
npm install
npm run dev
```

## Comprobar producción
```bash
npm run build
npm run preview
```


## V6
- Recuperado el tono/copy de las versiones anteriores.
- Eliminados todos los textos internos que explicaban cómo editar la web.
- Solo la imagen principal del hero utiliza `loading="eager"` y `fetchpriority="high"`.
- Las imágenes situadas por debajo del primer viewport utilizan `loading="lazy"` y `decoding="async"`.
- El vídeo usa `preload="none"` para no descargar contenido pesado hasta que el usuario interactúe.
- `MediaShowcase` usa `astro:assets` y `Image` con responsive widths.


## V6.2 — logo HiDPI
El logo original es 2048×2048 px. Los logos fijos ahora usan `densities={[1, 2, 3]}` y PNG para generar `srcset` específico para pantallas Retina/HiDPI.

## Descargas y entrega a Netlify (18 de octubre de 2026)

La navegación y las páginas de Inicio, Live y Manager enlazan con `/descargas`
(`/en/downloads` en inglés). La página ofrece Live y Manager para Windows x64,
Mac Apple Silicon y Mac Intel. La detección usa señales del navegador; nunca
interpreta `MacIntel` o `Intel Mac OS X` como prueba de un procesador Intel.
Si no puede distinguir la arquitectura, pide elegirla. Todos los enlaces siguen
funcionando sin JavaScript. No hay descarga automática al entrar en la página.

`src/lib/downloads.json` fija archivo, versión, tamaño y SHA-256 de seis
instaladores públicos ya publicados: Live beta 10 Windows, Live beta 8 Mac y
Manager beta 6. No publica los nuevos instaladores pendientes de aceptación.
Para actualizar versiones, cambia ese catálogo y verifica los archivos antes
de reconstruir. `npm run build` genera `public/_redirects` y lo copia a `dist`.
Las rutas `/download/<producto>/<plataforma>` hacen un 302 al archivo adjunto:
el visitante permanece en la web y el navegador inicia la descarga, sin abrir
una página de GitHub. Los binarios siguen alojados en GitHub Releases/CDN; no
se incluyen en el ZIP de la web ni pasan por un proxy con límite de tiempo.

Antes de entregar: `npm ci && npm test && npm run build && npm audit`.
Las pruebas cubren sesión de recuperación existente, rechazo de JWT con un
único reintento tras renovación, separación de invitaciones, errores reales
y respuestas tardías tras salir; también detección y elección manual de
instaladores. La comprobación de las descargas reales revisa HTTP, tamaño y
Content-Disposition sin descargar gigabytes de instaladores.

Para actualizar el sitio existente manualmente en Netlify:

1. Abre el proyecto que tiene el dominio `secretariatproapp.com` y su sección
   **Deploys**.
2. Arrastra la carpeta compilada entregada, que contiene `index.html`, `_astro`,
   `cuenta`, `descargas`, `en`, `media`, `assets` y `_redirects`. Si recibes un ZIP,
   descomprímelo primero y arrastra esa carpeta completa.
3. Espera a que el despliegue se publique. Recarga la web y comprueba
   `/descargas` y `/cuenta?type=recovery` con tu sesión, sin compartir tokens.
4. Prueba un botón de descarga. La validación de las rutas en Netlify queda
   pendiente de esta publicación; no basta con comprobar los archivos de origen.

No hay que subir `node_modules`, `.env`, ajustes de Live/Manager ni el repositorio.
Un push a la rama de trabajo conserva el código, pero no actualiza por sí solo
un sitio manual o conectado a otra rama. Para despliegues por Git, la configuración
existente es base `website`, comando `npm run build`, salida `dist` relativa a esa base.

Documentación oficial: [despliegues manuales de Netlify](https://docs.netlify.com/deploy/create-deploys/#drag-and-drop).
