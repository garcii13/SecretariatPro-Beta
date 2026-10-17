# Acabado y movimiento de emisión · beta 11

El acabado conserva la geometría actual, escudos/banderas, fuentes, escala y
paletas publicadas. Añade profundidad mediante bordes de luz, sombras suaves y
superficies derivadas de los colores elegidos en Manager; no sustituye la
personalización por una paleta fija.

## Movimiento

| Gráfico | Entrada | Datos | Salida |
| --- | --- | --- | --- |
| Marcador | Descenso corto de 18 px y aparición de 640 ms | Centro, nombres, escudos/banderas y reloj en capas; reflejo único de entrada | 220 ms hacia arriba |
| Gol / avisos | Ascenso corto de 26 px | Se mantiene la intro de gol de 1,6 s y después aparecen goleador/asistente; conserva toda su duración de lectura | 220 ms hacia abajo |
| Ficha | Ascenso corto de 26 px | Identidad, detalles y estadísticas escalonados | 220 ms |
| Previa / descanso | Aparición de 640 ms con desplazamiento corto | Cabecera, selecciones/equipos y filas de datos escalonados | 220 ms |
| Alineaciones | Aparición de 640 ms | Cabecera y titulares; transición a convocados en el mismo momento que antes | 220 ms, conservando la fase y el tamaño hasta ocultarse |
| Goleadores / clasificación | Aparición de 640 ms | Tarjetas y filas escalonadas | 220 ms |
| Penaltis | Aparición de 640 ms | Equipos en dos tiempos; intentos y resultado conservados | 220 ms |
| Sanciones / portería vacía | Entrada breve de 380 ms | Reloj vinculado al estado existente | 220 ms con colapso y cancelación segura |

Los cambios de resultado reciben un acento de 340 ms. El reloj no se anima en
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
