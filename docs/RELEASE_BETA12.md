# SecretariatPro Live y Manager · 1.0.0-beta.12

Esta versión conserva la base común Mac beta 8 + Windows beta 10, las mejoras
posteriores de OCR y BroadcastFlow y el intercambio de federaciones de Manager.

- Live mantiene el estado operativo, marcador y reloj en memoria si el disco se
  llena. Avisa de los datos pendientes y vuelve a intentar guardarlos al recuperar
  espacio. Los fallos de las repeticiones no derriban la respuesta del directo.
- Caché de Live configurable (8 GB por defecto), reserva de 2 GB y carpeta de
  caché/biblioteca en otra unidad. Se reutilizan los archivos de cámara mediante
  enlaces en el mismo volumen, evitando duplicar vídeo. Solo se retiran copias
  antiguas ya exportadas; los eventos pendientes y vídeos finales se conservan.
- Gol y asistencia se guardan en una transacción. Reintentar la misma petición
  no duplica eventos, marcador, estadísticas ni presentación. Los atajos ignoran
  la repetición de tecla y el formulario bloquea envíos simultáneos.
- Edición de equipo, jugador, asistencia, tiempo, sanción y notas en Live y Manager.
  Anular un gol cancela su asistencia. El contador gráfico descuenta la corrección
  una vez y conserva los ajustes manuales previos. Manager recalcula el resultado
  del acta en la misma transacción. Editar una sanción no reinicia su reloj en curso.
- Live muestra exclusivamente los partidos asignados al usuario. La base de datos
  aplica el límite también a consultas directas de los realizadores. Manager
  conserva la administración del espacio y los partidos sin asignar.
- Preview de OBS con objetivo de 25 fps, JPEG más ligero, captura compartida y
  temporización que incluye el tiempo de respuesta de OBS. La fluidez efectiva
  depende de la carga de OBS y del equipo; no cambia los fps de emisión ni del OCR.
- Un único motor controla la salida del bottom bar. Corregir su evento cancela
  la presentación pendiente y evita que reaparezca una tarjeta obsoleta.
- Separación vertical y horizontal de campos, controles y botones en ambas
  interfaces; Manager adapta las filas a ventanas estrechas y conserva federaciones.

## Almacenamiento

El búfer de OBS ya usa memoria; guardar vídeos sigue necesitando una unidad con
espacio. El destino de Live no cambia la carpeta del plugin de OBS ni la de su
búfer nativo. No se borran grabaciones ajenas. Si no hay espacio, se pausa el
nuevo guardado de repeticiones y continúa el control del directo. Los datos
operativos pendientes en memoria requieren recuperar espacio antes de cerrar Live.

## Validación y distribución

Consulte `VALIDATION_BETA12.md` para distinguir pruebas locales, pruebas de base
de datos, compilaciones nativas y aceptación instalada. La publicación conserva
la comprobación obligatoria de evidencia por instalador; estas notas no sustituyen
una sesión de OBS/cámara ni las pruebas nativas de Windows.
