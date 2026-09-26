# Realización: goles, marcas y biblioteca

Implementación local de septiembre de 2026. Mantiene los motores OCR, OBS WebSocket, capturas multicámara, atajos y temas publicados desde Manager.

## Resultado: dos fuentes separadas

En modo OCR, el marcador principal sigue leyendo los TXT originales del OCR. Registrar un gol NO modifica esos archivos. El resultado interno se guarda en `scores/reconciliation.json` y se utiliza en los bottoms y gráficos de resultado, incluido el descanso. Una lectura atrasada no reduce este contador; al alcanzar el resultado confirmado deja de estar pendiente sin volver a sumar. La corrección manual reemplaza su referencia y cargar otro partido reinicia la reconciliación. En modo manual, registrar un gol sí actualiza el resultado manual.

El cliente conserva una referencia del resultado al comenzar el registro y una clave por operación para impedir duplicados por doble pulsación o reintento durante la sesión. El registro oficial continúa usando el sistema de eventos existente de Supabase.

## SecretariatDeck

GOL conserva goleador/asistente y, con el plugin activo, abre directamente el constructor. MARCAR muestra etiquetas iniciales y permite escribir una propia. Ambos sustituyen todo el espacio de botones del deck por cada paso: cámara → segundos → velocidad → otro plano → LANZAR + GUARDAR / SIN REPETICIÓN. Las plantillas personales permiten precargar, modificar, duplicar, eliminar y elegir una predeterminada; se guardan con la cuenta del realizador.

Se conserva el límite de seis planos del plugin. Se permiten valores de 1 a 60 segundos por plano y velocidades 100/75/50/25 %. La suma del material solicitado debe caber en el evento capturado: el plugin rechaza una composición que exceda ese material, sin truncarla silenciosamente. Cada plano continúa la línea de tiempo desde el final del anterior.

## Presentación

`BroadcastFlow` es el propietario del marcador y del bottom mientras dura el evento. GOL: marcador oculto → replay (o espera de Manager) → vuelta confirmada a directo → bottom durante el tiempo de Manager → bottom fuera → marcador dentro. No detiene reloj, OCR ni periodo. Si se pierde el plugin, mantiene ocultos los gráficos hasta recuperar confirmación de directo. Limpiar emisión cancela el flujo.

El plugin 0.6.0 confirma reproducción y espera a que termine la transición de OBS al devolver el directo. El cliente no deduce el final sumando las duraciones de los planos.

## REPETICIONES

Un único botón abre los eventos locales terminados, incluidos los de otros partidos. Tarjetas con miniatura, etiqueta, nombre, periodo, reloj, duración y número de planos. Búsqueda, filtro, preview con controles de vídeo, descarga y apertura de carpeta. El preview nunca controla OBS. Lanzar un vídeo anterior oculta y restaura el marcador, sin mostrar su bottom original.

Los vídeos se guardan en `.runtime/replays/videos` y sus metadatos en `.runtime/replays/library.json`. Cada evento produce un MP4 independiente con toda su composición. Al cerrar, se limpian las cámaras temporales del compositor y el búfer del plugin; se conservan los vídeos terminados y las miniaturas. Importación, exportación y miniaturas se procesan fuera del hilo de la API; FFmpeg limita los hilos de codificación para reducir competencia con OBS.

## Periodo y apariencia

Manager puede mostrar el número dentro del mismo reloj (`2 · 12:34`) además del indicador inferior existente. La selección de periodo sigue activa con el marcador oculto. El tema claro del deck tiene una paleta específica para botones, dorsales, sanciones, goles, cancelación y estados activos. Los textos nuevos disponen de traducción a español, inglés, sueco, checo, finés y alemán.

## Comprobaciones

- 302 pruebas Python, incluyendo separación OCR/gráficos, varios goles, sincronización, corrección, persistencia, cancelación y orden del flujo.
- Pruebas nativas de línea de tiempo y ajuste de imagen, incluidas las cuatro velocidades.
- Compilación Xcode para arm64 y x86_64; sintaxis JavaScript validada.
- Exportación real desde vídeo 640×360 con audio: MP4 1920×1080, cuatro velocidades, miniatura y persistencia tras limpiar el compositor.
- Recorrido visual en navegador local con datos de prueba: pasos a pantalla completa dentro del deck, retorno al panel y contraste en tema claro.

Pendiente de validación operativa: una emisión real con OBS, cámaras y OCR físico. Las pruebas de interfaz usaron datos locales simulados y no enviaron señal a un directo.
