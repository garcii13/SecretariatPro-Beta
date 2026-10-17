# Base común Mac + Windows

Fecha: 17 de octubre de 2026. Rama: `feature/unified-international-goals`.

- Mac más reciente publicado: beta 8, `4ac82def73a5be1d7510d210b7c2061da8fd3ac5`.
- Windows beta 10: `3d4c10ae4f2be62633120cbd8938015db0fef1a5`.
- Unión de código verificada: `84c45c4`; ascendencia de ambas ramas registrada en
  `5b528be`. Se conservaron además las mejoras locales de consenso temporal OCR
  y el diagnóstico con inferencia real, posteriores a la publicación de Mac.
- Próxima versión de código: `1.0.0-beta.11`. No se han reemplazado los releases
  publicados ni compilado nuevos instaladores durante esta integración.

## Matriz de conservación

| Área | Contrato que se conserva | Cobertura y aceptación |
| --- | --- | --- |
| Captura Windows | Preview y worker usan los mismos píxeles físicos; al guardar regiones cambia el lector activo; los procesos sustituidos no escriben lecturas | `test_ocr_region_alignment.py`, ejecución nativa en Windows |
| Captura Mac | Ventana por ID sin sustituirla por el escritorio; cámaras con arranque único; errores y selección de preview persistentes | `test_window_capture.py`, `test_camera_startup.py`, `ocr_preview.test.cjs` y comprobación instalada |
| OCR | SP-OCR/SP-SCORE, perspectiva, regiones, confianza, envío al Lab y progreso del reloj; dependencias diferenciadas por plataforma | Pruebas OCR, consenso, reloj, muestreo y diagnósticos del worker empaquetado |
| Emisión | Resultado OCR separado del resultado gráfico, modo manual, periodos, sanciones, penaltis, goles y asistencias | Pruebas core, operaciones, goles, powerplay y reconciliación |
| OBS y replay | Vuelta confirmada a directo, cancelación, multicámara, velocidades, secuencias, biblioteca, miniaturas y exportación | `test_replay_workflow.py`, `test_beta6_replay_sequences.py`; sesión real con OBS y cámaras |
| Manager | Cuentas, invitaciones, ámbitos, equipos, jugadores, rosters, importación y publicación visual | Pruebas de identidad, permisos, importaciones y perfiles |
| Banderas | Subida original por selección; publicación por identidad; escudos conservados; ancho común limitado y altura dentro del marcador | `test_international_identity.py`, `overlay_presentation.test.cjs`, `manager_identity.test.cjs` |
| Gol animado | Idioma de Live, color del equipo, 1,6 s antes del goleador; duración del goleador intacta; cancelación segura | Pruebas BroadcastFlow y presentación JavaScript |

## Comprobación de cada cambio

```sh
python packaging/run_regressions.py
node --check overlay_motion.js
node --check script.js
node --check webapp/app.js
node --check manager_app/app.js
node --test tests/ocr_preview.test.cjs tests/overlay_presentation.test.cjs tests/manager_identity.test.cjs tests/overlay_motion.test.cjs
```

`Shared feature regressions` prepara la ejecución en Windows x64, Mac arm64 y
Mac Intel en pushes/PR. `Beta installers` repite estas comprobaciones, valida el
worker congelado y abre aplicaciones instaladas antes de permitir la publicación.
Los instaladores deben proceder del mismo código y pasar sus comprobaciones.

La base antes de las funciones nuevas pasó 424 pruebas Python en este Mac,
con dos pruebas Win32 omitidas. La entrega añade pruebas de banderas, idiomas,
subida de imágenes y fases del gol. Una suite local no garantiza ausencia de
fallos de hardware: faltan la ejecución nativa en Windows, la revisión visual y
una sesión de emisión real antes de declarar lista la distribución.

## Resultado local final

431 pruebas Python ejecutadas, sin fallos; dos pruebas exclusivas Win32
omitidas en este Mac. Once pruebas JavaScript correctas y sintaxis validada
para las tres interfaces. La copia local y el checkout de Git contienen el mismo
código. Se conservaron asimismo los scripts SQL locales de diagnóstico y
reparación de acceso a partidos; no se ejecutó ninguna migración.

La apertura de la vista de prueba en el navegador integrado no recibió permiso
de acceso al servidor local. No se realizó la comprobación visual ni se intentó
otra vía de navegador tras ese bloqueo.

## Actualización de movimiento

El acabado cinematográfico se describe en `CINEMATIC_OVERLAY_BETA11.md`. Se
conservan las fases de BroadcastFlow y la duración del goleador. La entrega
añade cobertura de interrupciones y de recursos estáticos: 433 pruebas Python
sin fallos (dos Win32 omitidas) y 20 pruebas JavaScript correctas. El navegador
integrado mantiene bloqueado el origen de prueba por un permiso persistente,
aunque el usuario autorizó de nuevo su apertura. La revisión visual sigue
pendiente y no se han lanzado compilaciones ni publicado la nueva versión.
