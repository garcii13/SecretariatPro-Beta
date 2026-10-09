# Live 1.0.0-beta.10 para Windows x64

Corrige la correspondencia entre las cajas dibujadas, el recorte leído por OCR
y las muestras que se envían al Lab cuando se captura una ventana.

## Causa y corrección

La vista previa y el worker son procesos distintos. Windows puede proporcionar
geometrías virtualizadas diferentes según el contexto DPI de cada hilo, aunque
se capture la misma ventana. En un monitor a 134 DPI la reproducción anterior
produjo recortes de 558×320 y 780×448 para la misma ventana de prueba.

La captura Win32 usa ahora un contexto temporal `PER_MONITOR_AWARE_V2` para
obtener tanto la geometría como el bitmap en píxeles físicos. Después restaura
el contexto del hilo. El recorte del área cliente sigue excluyendo bordes y
barra de título; las regiones continúan expresándose como fracciones del frame.

Además, guardar regiones mientras el OCR estaba activo solo modificaba la
configuración persistida: el proceso seguía leyendo las cajas anteriores.
Ahora se reinicia el lector cuando cambia su configuración. Un guardado sin
cambios no lo interrumpe. Al detenerlo se cierra también el proceso hijo del
ejecutable PyInstaller; se ignoran mensajes de procesos sustituidos.

## Actualización

Cerrar Live e instalar beta.10. Capturar una nueva vista previa y volver a
dibujar Local, Tiempo y Visitante para descartar coordenadas guardadas con la
captura anterior. Guardar las regiones antes de comprobar las lecturas.

Se conservan las correcciones y modelos sin descarga de beta.9. Para compilar,
seguir `RELEASE_WINDOWS_OCR.md` y ensamblar con:

```powershell
python packaging/assemble.py --product Live --version 1.0.0-beta.10
```

Las pruebas cubren geometría Win32 real con píxeles de prueba controlados,
igualdad de recortes entre contextos DPI, restauración del contexto, aplicación
de regiones al lector activo y cierre del árbol de procesos. El comportamiento
con un marcador deportivo real debe verificarse durante la puesta en marcha.
