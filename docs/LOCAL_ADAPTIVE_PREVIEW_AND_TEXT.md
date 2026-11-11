# Candidata local · preview adaptativa y textos · 10 de noviembre de 2026

Estos cambios están en el código local, posteriores al instalador beta 12 de
`1af1d69`. No se han generado instaladores nuevos. Las dos copias de las fuentes
se mantienen sincronizadas y se conservan los requisitos de aceptación nativa.

## Preview y prioridad del directo

- Techo de 60 fps, limitado además por los fps configurados en OBS y la latencia
  media de captura. Arranca a 15 fps; sube por escalones tras cinco segundos de
  margen estable. Un retraso aislado de captura no divide la fluidez por dos.
- Una muestra por segundo: CPU del equipo y de OBS, memoria disponible, salidas
  a swap, tiempo de render y nuevos fotogramas omitidos al renderizar/codificar.
  Los contadores históricos y los reinicios de OBS no se tratan como pérdidas nuevas.
- Reduce rápidamente ante carga y pausa capturas con presión crítica; después
  exige cinco segundos de recuperación y vuelve desde 5 fps. Si no dispone de
  telemetría, limita a 8 fps y no reanuda una pausa sin evidencia de recuperación.
- Captura y telemetría usan la conexión secundaria de monitor; no bloquean el
  socket de goles/escenas. No cambia los ajustes de emisión, grabación ni OCR.
- Un único JPEG compartido, límite defensivo de 4 MiB y ninguna escritura de
  fotogramas en disco. Desconectar el último visor libera el JPEG y la conexión
  de monitor; ocultar la vista cancela imagen, reintentos y consultas de estado.
- El indicador AUTO muestra el límite actual, no una promesa de fps efectivos.
  Una preview siempre consume recursos: el control reduce el riesgo, no puede
  garantizar impacto cero en todo hardware ni controlar el swap del sistema.

Protocolo de referencia:
[OBS GetStats](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#getstats).

## Textos de los gráficos

- El pabellón ajusta su tamaño a la anchura disponible; los nombres excepcionales
  pueden usar varias líneas dentro de su caja, sin puntos suspensivos.
- La convocatoria conserva dos columnas y amplía el panel según los nombres y
  posiciones. La posición tiene su propia anchura natural y 12 px de separación.
  Al llegar al margen de pantalla, se ajusta la tipografía de los nombres.
- Se recalcula al cambiar texto, fuente, tamaño de ventana o fase de alineaciones,
  no en cada tick del reloj. Se reserva espacio para el entrenador a 720p.
- Mismo adaptador en el renderer Studio y el legacy; originales, banderas,
  identidad publicada y secuencia de entrada/salida se conservan.

## Validación

- Python: 528 pruebas, cero fallos, dos pruebas Win32 omitidas en Mac.
- JavaScript: sintaxis de script.js, webapp/app.js y manager_app/app.js; 35 pruebas
  incluyendo la cancelación del monitor y respuestas tardías de estado.
- Renderer: npm ci y npm run verify; 25 pruebas y manifiesto regenerado.
- OBS real, cámara integrada y API local aislada: la protección suspendió capturas
  al simular CPU al 99%, reanudó de forma gradual y dejó cero clientes/cero bytes
  de JPEG al cerrar la conexión. La simulación no cargó artificialmente el equipo.
  Evidencia local: release/Beta12-validation/adaptive-preview-recovery.json.
- No se presenta la prueba de recuperación bajo carga como medición de fps máximos.
  Los 60 fps están cubiertos por pruebas de la política, no por una emisión física
  a 60 fps en este Mac. Queda pendiente la aceptación nativa de estos cambios.
- Navegador: nombres de pabellón y jugadores largos, 20 convocados, posición
  reservada, Studio y legacy a 1080p y revisión de espacio a 720p.
  Evidencia visual local: release/Beta12-validation/venue-fit.jpg, lineups-fit.jpg
  y lineups-720p.jpg; medidas de la última prueba en lineups-720p.json.
