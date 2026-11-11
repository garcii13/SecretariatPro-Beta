# Validación beta 12 · 9 de noviembre de 2026

Estado: candidata de Live y Manager, pendiente de aceptación instalada.
Base: `7af1cf2` con federaciones e idiomas. Se conserva la matriz de
`BASELINE_COMPATIBILITY.md` y no se ha modificado OCR Lab.

## Comprobaciones completadas

- Python: 513 pruebas ejecutadas, cero fallos, dos pruebas Win32 omitidas en Mac.
- JavaScript: sintaxis de script.js, overlay_motion.js, webapp/app.js,
  manager_app/app.js y tablet/tablet.js; 33 pruebas de OCR preview, presentación,
  identidad de Manager, movimiento y federaciones/idiomas.
- Renderer: `npm ci` y `npm run verify`, 25 pruebas; recursos y manifiesto local
  generados de nuevo, sin depender de Node en la aplicación instalada.
- Seguridad: `npm ci` y `npm test` en security_tests; cuatro pruebas PostgreSQL
  (PGlite), incluidas asignaciones, transacciones de gol/asistencia, reintentos,
  correcciones, anulaciones y resultados atómicos de Manager.
- Base de datos real: migración `live_event_integrity_and_assignments` aplicada.
  `packaging/cloud_live_events_probe.sql` pasó con usuarios/partidos sintéticos,
  sin emails y con todas las inserciones revertidas. Los avisos del asesor de
  seguridad no aumentaron respecto de la situación previa.
- Navegador contra API local con datos sintéticos: corregir un gol de local a
  visitante cambió 2–1 a 1–2; anularlo dejó 1–1. Manager guardó la corrección de
  tiempo y mostró la fila actualizada. Se verificaron espacios en formularios,
  botones y tablas, incluyendo 600 px de ancho sin desbordamiento horizontal.
- Overlay real del navegador: bottom en `on`, `exiting` y `off`, sin transición
  CSS adicional; al terminar quedó `display:none`.
- Disco lleno simulado: respuestas de estado, reloj TXT y overlay disponibles;
  contador y reloj en memoria, posterior recuperación a disco; vídeos y eventos
  pendientes conservados. Pruebas de biblioteca existentes preservadas y
  aislamiento explícito de espacio disponible en sus fixtures.

## Seguimiento de la candidata compilada

La compilación final de `1af1d69` pasó auditoría, regresiones, OCR empaquetado y
arranque instalado en Windows, Mac ARM e Intel:
[run 42633686603](https://github.com/garcii13/SecretariatPro-Beta/actions/runs/42633686603).
En este Mac se probó OBS con la cámara integrada: preview fija de beta 12 a
20,2 fps frente a 6,6 fps del bucle anterior; captura de dos fuentes, composición,
vuelta a directo y exportación decodificada de seis segundos. La Sony configurada
no estaba conectada. No se sustituyó la aplicación instalada del usuario.

La aceptación operativa completa, incluido Stream Deck físico y hardware de cada
plataforma, sigue pendiente. La publicación conserva el control de evidencia por
hash/commit en `packaging/verify_acceptance.py`.

Con autorización del usuario se liberaron 10,48 GiB de cachés regenerables de
Spotify, npm y pip. No se borraron documentos, grabaciones ni modelos OCR.

Los cambios locales posteriores de preview adaptativa y textos se documentan en
[LOCAL_ADAPTIVE_PREVIEW_AND_TEXT.md](LOCAL_ADAPTIVE_PREVIEW_AND_TEXT.md); no están
incluidos en los instaladores de ese run.

## Dependencia de certificados HTTPS

La primera compilación de Windows y Apple Silicon de `b2dcfb4` pasó regresiones,
OCR empaquetado y arranque instalado. Intel se detuvo al auditar la copia
preinstalada de `certifi==2026.7.22`. Se añadió el mínimo `certifi>=2026.10.23`
para todas las plataformas, sin excepciones en el auditor. La causa está
publicada por el mantenedor en
[GHSA-6q48-6c7w-9gw2](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2).
Los tres destinos finalizaron correctamente con la dependencia corregida.
