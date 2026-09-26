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
