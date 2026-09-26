# Correcciones operativas — septiembre de 2026

## OCR y captura
Los modelos SP-OCR v0.7 y SP-SCORE v0.2 siguen presentes y sus hashes coinciden con el manifiesto. La lectura sintética 12:34 funciona. Se corrige la detección de versión de PaddleOCR y se aísla también la captura OpenCV/AVFoundation en un proceso hijo: un cierre nativo de cámara no debe cerrar Live. Los diagnósticos se guardan en .runtime/camera_capture.log y .runtime/ocr-worker.log. Sigue pendiente repetir el caso concreto con la cámara de iPhone del usuario.

## Operación
Gol y Marcar solicitan la captura al primer clic; la ficha del evento se completa después, sin una segunda captura. Los QR conservan el token al añadir el parámetro de caché y admiten varios códigos vigentes, cada uno de un solo uso. La tablet incluye marcas, composición guiada, biblioteca, periodos, empty net, cola y lanzamiento de secuencias.

En modo manual se ocultan el reloj del marcador y los tiempos del powerplay; se conserva la configuración de periodos del Manager. La biblioteca filtra por partido. Los vídeos acabados se guardan en Repeticiones/<id-del-partido> dentro de la carpeta de datos local, accesible con Abrir carpeta. Los vídeos antiguos se copian allí conservando los originales. Los highlights se crean a partir de vídeos seleccionados; el filtro por periodo ayuda a seleccionarlos. Un nombre repetido sustituye el MP4 solo tras terminar correctamente la nueva exportación.

## Respuesta del deck
La vista previa OBS utiliza una conexión separada de la de control. Los snapshots de las acciones reutilizan el último estado OBS; el sondeo de estado lo actualiza. Las estadísticas cargadas se muestran de inmediato y se refrescan en segundo plano. Se evita reconstruir plantillas, botones de jugadores y biblioteca cuando sus datos no han cambiado. Una tablet lenta deja de bloquear secuencialmente a las demás.

## Verificación y límites
Pruebas unitarias de múltiples QR, aislamiento de partidos, más de cinco eventos, recuperación tras errores y separación de vídeo/control. Prueba real FFmpeg de dos composiciones, montaje, sobrescritura y persistencia. Interfaz comprobada con datos sintéticos; esto no sustituye un ensayo con OBS y las cámaras reales. La reproducción de biblioteca necesita el plugin 0.6.0 o posterior.


## QR, muestras OCR y eliminación (24 septiembre)

- Selector de interfaz LAN y diagnóstico de escucha local. La respuesta local no demuestra accesibilidad desde otros dispositivos: una Wi-Fi universitaria puede aislar clientes. Comprobar con una red propia o punto de acceso móvil.
- OCR: subida INSERT, sin upsert que exige permisos adicionales. Reintento de objeto existente tras fallo de metadatos; los errores 403 siguen propagándose. No se amplían permisos de Supabase. Pendiente verificar el reenvío real de las 8 muestras en cola con una sesión activa.
- Eliminar vídeos del partido desde escritorio/tablet: traslado a Repeticiones/Papelera. Deshacer desde escritorio; restauración sin sobrescribir archivos nuevos.
- 314 pruebas unitarias pasan; API real probada para QR, emparejamiento, permisos y eliminación/restauración. No verificado en los móviles físicos ni reproducido el cierre con la cámara original.
