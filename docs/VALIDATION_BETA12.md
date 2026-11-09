# Validación beta 12 · 9 de noviembre de 2026

Estado: candidata de Live y Manager, pendiente de aceptación instalada.
Base: `7af1cf2` con federaciones e idiomas. Se conserva la matriz de
`BASELINE_COMPATIBILITY.md` y no se ha modificado OCR Lab.

## Comprobaciones completadas

- Python: 511 pruebas ejecutadas, cero fallos, dos pruebas Win32 omitidas en Mac.
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

## Pendiente antes de distribución

Compilación y pruebas nativas de instaladores en Windows, Mac ARM e Intel;
aceptación instalada y sesión real OBS/cámara/Stream Deck, multicámara y
exportación. Los 25 fps son un objetivo de programación: no hay medición de
rendimiento con OBS real para esta compilación. No se ha sustituido la versión
instalada del usuario. La publicación mantiene su control de evidencia por
hash/commit en `packaging/verify_acceptance.py`.

La unidad local tenía menos de 1 GB libre durante la revisión: no se compilan
instaladores grandes en ella ni se borran vídeos o archivos del usuario.
