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
| Gol animado | Idioma de Live, color del equipo, ceremonia de 2,2 s y transición de 640 ms al goleador; duración del goleador intacta; cancelación segura | Pruebas BroadcastFlow y presentación JavaScript |

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

## Suavizado y transición de gol

435 pruebas Python sin fallos (dos Win32 omitidas) y 25 pruebas JavaScript. Se
comprueba la fase GOAL_REVEAL, su cancelación, el tiempo completo del goleador,
la continuidad al invertir una animación, goles consecutivos y la sincronización
de clientes que reciben tarde una fase. La revisión visual permanece pendiente.

## Nueva presentación Svelte/SVG/GSAP

`BROADCAST_STUDIO.md` documenta la migración de todos los paneles, el adaptador
compartido con la referencia y el nuevo motor de movimiento. La URL habitual
`/overlay.html` sirve la presentación nueva; `?renderer=legacy` conserva la
referencia y la recuperación automática. Las preferencias y publicaciones de
Manager mantienen sus contratos. Se conservan OCR, manual, periodos, cuentas,
competiciones, colas, replay, multicámara, plantillas, biblioteca y exportación.

Verificación local: 438 pruebas Python sin fallos (dos exclusivas de Win32
omitidas), 25 pruebas JavaScript previas y 14 pruebas del nuevo bundle compilado.
Svelte/TypeScript: cero errores y cero avisos. Se comprueban la equivalencia de
contenido en seis idiomas y dos deportes, estilos publicados, banderas,
previsualización de cola, fases/cancelación de GOL y powerplays (ambos equipos,
sanciones simultáneas, reloj detenido, aviso final, salida/recuperación y FIFO
cuando se modifica una cola durante una animación). No se retira cobertura previa.

Ejecutar `npm ci --prefix broadcast_renderer` y
`npm run verify --prefix broadcast_renderer` antes de las comprobaciones Python.
Los assets y su manifiesto de hashes quedan versionados y empaquetados, sin Node
ni CDN en el equipo del usuario. Se exige la misma compilación/verificación en CI.
La revisión visual, Windows nativo y la sesión real con OBS/cámaras/aplicación
instalada siguen pendientes antes de distribuir; estas pruebas DOM no las sustituyen.

## Continuidad de bloques y movimiento

Bottom y perfil comparten una superficie continua; marcador y bottoms animan el
contenido sin desplazar sus fondos internos. Se suavizan aceleración/frenado y
se reduce el recorrido/desfase de las piezas. El GOL conserva su posición al
pasar a GOAL_REVEAL; la máscara supera el reset de la geometría anterior y el
modo de movimiento reducido utiliza un fundido. Manager conserva todos sus
colores, tamaños y tipografías, incluidos los colores propios de la raíz del bottom.

438 pruebas Python sin fallos, dos Win32 omitidas; 25 JavaScript previas y 17 del
renderer correctas, con Svelte/TypeScript sin errores ni avisos. Powerplays,
sanciones simultáneas, reloj detenido, EMPTY NET y orden/cancelación de las colas
siguen incluidos. Revisión visual y sesión real OBS/Windows pendientes.

## Texto fijo y desplazamiento superior del marcador

El marcador completo entra desde arriba y sale hacia arriba, con textos siempre
visibles y sin animación independiente al cambiar el resultado. La distancia
incluye reloj y colas de powerplays/EMPTY NET actuales. Se mantiene la escala de
Manager. El bottom se desvanece sin desplazarse al salir y conserva los detalles
si se cancela o invierte una entrada en curso.

438 pruebas Python sin fallos (dos Win32 omitidas), 25 JavaScript existentes y
20 del renderer correctas; Svelte/TypeScript sin errores ni avisos. Continúan
pendientes revisión visual, Windows nativo y sesión real OBS antes de distribuir.

## Nombres completos y ajuste de previa

El contexto mantiene abreviatura para marcador y nombre completo para previa y
descanso, con recuperación desde alineaciones en estados anteriores. Cambiar de
partido sustituye ambos nombres. La previa comparte columnas entre tarjetas y
cajas de pabellón/inicio, también en el formato estrecho. El marcador conserva
su texto visible y movimiento superior con entrada/frenado y salida acelerada.

440 pruebas Python sin fallos (dos Win32 omitidas); 26 JavaScript anteriores y
21 del renderer correctas, Svelte/TypeScript sin errores ni avisos. Revisión
visual/OBS y ejecución nativa Windows pendientes antes de distribuir.

## Descanso responsive y simétrico

Ancho intrínseco automático del panel de descanso, con límite del 94 % del
viewport y columnas de equipo iguales según el mayor espacio necesario. Logo
centrado y composición compacta para pantallas estrechas, sin configuración nueva
en Manager. Se conservan nombres completos, personalización, eventos y colas.
Validación: 440 Python sin fallos (dos Win32 omitidas), 26 JavaScript y 21 del
renderer correctas, sin errores/avisos Svelte/TypeScript. Revisión visual pendiente.

## Correcciones de auditoría (18 de octubre)

`AUDIT_FIXES_BETA11.md` detalla transporte ordenado, resultados conservados ante
fallos, protección Host/Origin/sesión local, invitaciones idempotentes, nuevas
auditorías de dependencias y aceptación obligatoria antes de publicar. El Lab
queda excluido. El runtime Mac mantiene la API OCR 2.x con Paddle 3.0.0,
PaddleOCR 2.10.0 y OpenCV 4.10.0; 67 lecturas comparadas idénticas, modelos y
CPU/PIR preservados. Windows conserva sus requisitos propios.

445 pruebas Python (dos Win32 omitidas), 27 Node y 24 del renderer correctas;
SQL de invitación probado en PostgreSQL local. Svelte sin errores/avisos,
auditorías Python/web/renderer sin avisos y Astro compila 16 páginas. Pendientes
Windows/Intel nativos, instalación/OBS/cámaras, revisión visual y despliegue cloud;
la publicación exige evidencias para esos recorridos, vinculadas a commit y hash.
