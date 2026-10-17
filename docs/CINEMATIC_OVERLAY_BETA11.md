# Acabado y movimiento de emisión · beta 11

El acabado conserva la geometría actual, escudos/banderas, fuentes, escala y
paletas publicadas. Añade profundidad mediante bordes de luz, sombras suaves y
superficies derivadas de los colores elegidos en Manager; no sustituye la
personalización por una paleta fija.

## Movimiento

| Gráfico | Entrada | Datos | Salida |
| --- | --- | --- | --- |
| Marcador | Descenso corto de 12 px y aparición de 760 ms | Centro, nombres, escudos/banderas y reloj en capas; reflejo único de entrada | 320 ms hacia arriba |
| Gol / avisos | Ascenso corto de 18 px | Ceremonia de GOL de 2,2 s y transición de 640 ms que descubre goleador/asistente; conserva toda su duración de lectura | 320 ms hacia abajo |
| Ficha | Ascenso corto de 18 px | Identidad, detalles y estadísticas escalonados | 320 ms |
| Previa / descanso | Aparición de 760 ms con desplazamiento corto | Cabecera, selecciones/equipos y filas de datos escalonados | 320 ms |
| Alineaciones | Aparición de 760 ms | Cabecera y titulares; transición a convocados en el mismo momento que antes | 320 ms, conservando la fase y el tamaño hasta ocultarse |
| Goleadores / clasificación | Aparición de 760 ms | Tarjetas y filas escalonadas | 320 ms |
| Penaltis | Aparición de 760 ms | Equipos en dos tiempos; intentos y resultado conservados | 320 ms |
| Sanciones / portería vacía | Entrada breve de 460 ms | Reloj vinculado al estado existente | 300 ms con colapso y cancelación segura |

Los cambios de resultado reciben un acento de 420 ms. El reloj no se anima en
cada lectura. Las actualizaciones periódicas no reinician las entradas. No hay
animaciones decorativas continuas ni fondos que oscurezcan la señal.

`overlay_motion.js` se limita a la presentación. BroadcastFlow conserva el
control del replay, la intro, el tiempo del goleador y el regreso del marcador.
Cada transición usa una generación para impedir que una salida antigua o una
entrada encolada altere un gráfico nuevo. La preferencia de movimiento reducido
asienta las transiciones en curso y evita las coreografías.

## Manager

En Identidad visual, «Reproducir animación» permite probar la vista previa con
los colores, tamaños y tipografías elegidos, antes de guardar/publicar. Los
controles y el formato de las identidades existentes se mantienen.

## Validación

- Pruebas de interrupción, reaparición, actualización repetida, movimiento
  reducido, disponibilidad de Web Animations y cambios de resultado.
- Comprobación de las rutas y del empaquetado de los nuevos recursos.
- Suite completa Python y sintaxis/pruebas JavaScript.

La inspección visual del navegador integrado sigue pendiente: el permiso
persistente del origen local continúa denegado, incluso después de la
nueva autorización del usuario. No se ha utilizado otra vía de navegador para
sortearlo. Compilación y publicación quedan pendientes de esa revisión y de las
comprobaciones operativas de la base común.

## Continuidad del gol

La ceremonia combina el texto principal, una repetición de contorno al fondo,
líneas de acento y un barrido de luz con los colores del equipo. La nueva fase
`GOAL_REVEAL` retira esa superficie durante 640 ms, revelando la identidad y
los nombres debajo. `GOAL_BOTTOM` comienza después y conserva la duración
completa configurada en Manager. Las duraciones y la hora de cada fase viajan
con el estado para que una actualización tardía pueda situarse en el momento
correcto de la transición.

Las inversiones de mostrar/ocultar parten de la posición y opacidad visibles
en ese momento. Cancelar durante la ceremonia mantiene la capa de GOL durante
la salida para no descubrir por un instante un goleador que se ha cancelado.
La vista previa de Manager utiliza el mismo reparto temporal.

Comprobaciones actuales: 435 pruebas Python sin fallos (dos exclusivas Win32
omitidas) y 25 pruebas JavaScript correctas. Sigue pendiente la revisión visual
por el bloqueo guardado del navegador integrado.
