# Revisión local de rendimiento · 28/09/2026

Estado: cambios locales para pruebas. No se han creado instaladores, publicado
releases, instalado el plugin nuevo, cambiado ajustes de OBS ni modificado
Supabase. DistroAV y NDI Runtime se conservan.

## Lo que muestran los registros

Equipo: MacBook Air M1, CPU de 8 núcleos, GPU de 7 núcleos y 8 GB de memoria
unificada. Durante el diagnóstico, `vm.swapusage` indicó 0 MB utilizados.
Esto no permite reconstruir la presión de memoria durante el partido.

Los registros de OBS disponibles son del 27/09. No están los de los dos partidos
anteriores que funcionaron bien. No se puede atribuir el fallo a un cambio
accidental concreto ni asegurar una causa única.

- Las primeras sesiones usaron 1920×1080 a 60 FPS, con NDI Main y Preview.
- Hubo retraso de codificación antes de arrancar los búferes multicámara.
- Durante la tarde cambiaron los ajustes a 1080p30, 720p30 y una configuración
  de salida 1024×576. El encoder de las 15:52 figura de nuevo como 1280×720.
- En `2026-09-27 15-30-16.txt`, a las 16:19:48, las dos cámaras de repetición
  arrancaron con `obs_x264`, a 12.000 kbps por cámara. Al parar, registraron
  98,5 % y 98,7 % de fotogramas omitidos por retraso de codificación. La emisión
  registró 14,1 %. Los porcentajes corresponden a intervalos distintos.
- La emisión utilizaba Apple VT por hardware: cambiar solo su codificador no
  cambia el codificador independiente de las repeticiones.
- Hay dos muestras OCR pendientes en los datos de la aplicación instalada,
  ambas con `403: new row violates row-level security policy` de Storage.
  Se han conservado sin modificación.

El conjunto es compatible con sobrecarga de la producción: salidas adicionales,
codificación de las cámaras por CPU y trabajo redundante en Secretariat. Los
registros no prueban que NDI por sí solo causara el fallo ni descartan factores
de red, temperatura o memoria.

## Cambios implementados

| Área | Cambio local |
|---|---|
| Cámara | Comprueba secuencia antes de copiar un fotograma; deja de copiar imágenes repetidas continuamente. Mantiene el tamaño del puente OCR existente, hasta 1920 píxeles de ancho, y la captura nativa. |
| Cámara congelada | Rechaza imágenes de más de un segundo; no presenta un archivo antiguo como una captura nueva. |
| LED y OCR | La ráfaga espera fotogramas nuevos, conservando perspectiva, color, fusión LED, consenso, PaddleOCR, SP-OCR y SP-SCORE. OpenCV usa un hilo para evitar competir con los demás procesos. |
| Marcadores | No reescribe ni sincroniza a disco los valores que no han cambiado. Sigue detectando modificaciones externas. |
| Directo y tablet | Los cambios únicamente de marcador usan un mensaje ligero; mantienen la actualización completa para cambios del partido/configuración. |
| Monitor OBS | Máximo de 8 capturas JPEG/s, compartidas entre clientes; conserva 960 píxeles de ancho. Este límite solo afecta al monitor interno, no a los FPS de emisión, grabación o cámara OCR. |
| Repeticiones | Selección automática H.264 por hardware entre encoders registrados. En Mac migra una vez el antiguo valor predeterminado x264. Sigue disponible la selección manual; no recae silenciosamente en CPU si falla el hardware. |
| Lab | Guarda atómicamente el recorte antes de intentar enviarlo; un único trabajador de red; conserva la muestra hasta recibir un ID; no borra la imagen tras un timeout de metadatos. Las colas de otros espacios y los archivos dañados no bloquean las muestras válidas. |
| Muestras | Envía el recorte fusionado que realmente recibió el OCR; limita también los intentos de codificar imágenes duplicadas. El diagnóstico de entrega se actualiza en Configuración cada 5 s. |

La recuperación de muestras tras falta de red está probada con un servidor
simulado. El envío real al Lab sigue pendiente: el rechazo de permisos se produce
en Supabase, no se soluciona solo aligerando la aplicación.

`SUPABASE_OCR_LAB_STORAGE_FIX_V4.sql` deja preparada una migración completa con
las RPC existentes y la política INSERT del bucket privado. Exige sesión,
membresía activa y consentimiento del espacio. No concede lectura de imágenes
a clientes y no contiene credenciales. No se ha aplicado ni validado contra el
servidor. Tras revisar/aplicar la migración, hay que verificar la subida con una
sesión normal y comprobar en el Lab tanto metadatos como imagen; usar una clave
administrativa para subir no validaría estos permisos.

## Verificación local

- 357 pruebas de `unittest`, correctas, incluidas 13 nuevas de cámara, persistencia,
  reintentos, previsualización y protocolo de actualización del panel/tablet.
- 24 pruebas adicionales existentes declaradas como funciones, correctas.
- Sintaxis JavaScript del panel, tablet y sus service workers, correcta.
- Plugin compilado para arm64 y x86_64. Tres pruebas CTest correctas: selección
  de codificador, secuencias y disposición del vídeo. No instalado en OBS.
- Prueba sintética: 200 consultas al mismo fotograma 1920×1080 BGR. Antes:
  200 imágenes devueltas/copias completas, 1.186,5 MiB de payload acumulado,
  426,7 ms de pared. Después: una imagen, 5,9 MiB, 10,6 ms. No representa
  memoria residente ni el ahorro global de una producción; mide únicamente
  el trabajo duplicado de ese caso.

## Ajustes iniciales propuestos para este ordenador

Son un punto de partida para la prueba, no una garantía de estabilidad.

| Ajuste | Propuesta |
|---|---|
| Vídeo OBS | Lienzo y salida 1280×720, 30 FPS. No volver a 1080p60 durante la primera prueba. |
| Emisión | Apple VT H264 Hardware Encoder; CBR 4.000 kbps para YouTube 720p30; intervalo de fotograma clave 2 s; perfil High si está disponible. |
| Audio | AAC, 48 kHz, estéreo, 160 kbps. |
| Grabación simultánea | Usar el codificador de emisión cuando el flujo lo permita; contenedor MKV. |
| Repeticiones | Apple VT H264 Hardware Encoder en el propio panel del plugin; empezar probando 6.000 kbps por cámara y 20 s de búfer. Confirmar las dos cámaras y sus audios. |
| OCR | Conservar resolución y regiones calibradas; comenzar con el intervalo existente de 700 ms. No reducir resolución para ahorrar CPU antes de validar los dígitos pequeños. |
| NDI | Conservar DistroAV y Runtime. Activar Main/Preview solo cuando haya un receptor que los necesite. Apagar estas salidas no elimina las fuentes NDI de entrada. |

En la instalación actual, el menú en español es **Herramientas → Ajustes de
DistroAV NDI**. Las dos casillas son **Salida de Programa** y **Salida de
Previsualización**. No se ha cambiado su estado.

Referencias: [rendimiento de OBS](https://obsproject.com/kb/encoding-performance-troubleshooting),
[ajustes de YouTube Live](https://support.google.com/youtube/answer/2853702?hl=en),
[memoria en macOS](https://support.apple.com/en-au/guide/activity-monitor/-actmntr1004/mac).

No hay swap que limpiar en el momento del diagnóstico. No borrar archivos de
memoria virtual ni forzar purgas. Para la prueba, cerrar aplicaciones que no se
usen, guardar el trabajo y reiniciar antes si se necesita una sesión limpia;
vigilar la presión de memoria durante la producción. No se han cerrado apps ni
reiniciado el equipo.

## Prueba pendiente antes de cualquier instalador

Ejecutar el código local con `.venv/bin/python run_app.py` desde esta carpeta;
no sustituye la aplicación instalada y utiliza los datos locales del proyecto.
El plugin compilado queda en
`SecretariatPro_Multicam_Replay/build_macos/Release/secretariatpro-multicam-replay.plugin`;
su instalación en OBS queda pendiente. Mientras tanto, el plugin instalado permite
seleccionar manualmente Apple VT H264 Hardware Encoder en su propio panel.

Hacer una prueba de 45–60 minutos con las cámaras reales, sonido, OCR y dos
búferes de repetición; incluir NDI si forma parte del flujo habitual. Comprobar:

1. Reloj y ambos resultados, cambios de minuto, pausas, perspectiva y LED;
   desconectar/reconectar la cámara y verificar el aviso y la recuperación.
2. Marcador manual, goles, sanciones, perfiles, alineaciones, cola de gráficos,
   overlay de emisión, tablet y cambio de escenas.
3. Guardar, reproducir, cambiar de cámara, cámara lenta, salir de replay,
   biblioteca, exportación y highlights.
4. Interrumpir la red, generar una muestra difícil, recuperar la conexión y
   comprobar que aparece completa en el Lab sin perder el control local.
5. Estadísticas de OBS: fotogramas omitidos por codificación/renderizado,
   pérdidas de red, carga de CPU y presión de memoria. Comparar con la misma
   configuración y fuentes, no con capturas sintéticas.

Hasta pasar esta prueba no se consideran certificadas todas las funciones en
producción ni se crea un instalador.

## Segunda revisión: acceso y resistencia a conexiones lentas

Cambios adicionales locales tras revisar la lentitud al iniciar sesión:

- `workspace_context` reutiliza la lista de membresías recién consultada:
  elimina dos consultas de red repetidas, manteniendo la validación de acceso.
- Tras validar la membresía, respeta el intervalo de cinco minutos antes de
  volver a consultarla. Antes, la primera respuesta de estado podía validarla
  inmediatamente otra vez.
- Identidad visual, consentimiento OCR y competiciones se consultan en paralelo
  después de autenticar y validar la membresía; como máximo tres solicitudes.
- Fallar al cargar competiciones ya no invalida el inicio de sesión. El usuario
  puede reintentarlo abriendo de nuevo el selector de partido.
- La sincronización de ajustes de cuenta se realiza en un único trabajador,
  en orden, tras guardarlos localmente. No bloquea el acceso ni el guardado local.
- La respuesta de acceso incluye el estado inicial y las competiciones: el
  navegador deja de pedir ambos otra vez antes de mostrar el panel.
- Botón de acceso con estado de espera y protección frente a doble envío.
  El servidor también rechaza accesos simultáneos. Cerrar sesión invalida un
  intento pendiente para que una respuesta tardía no vuelva a abrirla.
- Errores de credenciales y errores de servicio/red tienen respuestas distintas.
  Una tentativa fallida no revoca las tablets de una sesión ya existente.
- Live utiliza límites de conexión de 5 s y lectura/escritura de 15 s por
  operación de red. No son un límite total para todo el acceso. El Manager
  conserva su transporte anterior para no acortar las importaciones masivas.
- Una validación offline vigente evita consultas secundarias que volverían a
  fallar. Sin permiso offline válido no se concede acceso. Esto no habilita una
  autenticación nueva completamente sin Internet.
- La consulta periódica de identidad visual se separa del bucle local de
  marcador/tablet. Una respuesta tardía de otro espacio o competición se descarta.
- Los transportes de intentos fallidos se cierran para no acumular conexiones.

Validación acumulada de esta revisión: 369 pruebas `unittest` y 24 pruebas
adicionales declaradas como funciones, todas correctas; sintaxis JavaScript
correcta. Las 12 nuevas pruebas de acceso incluyen concurrencia de consultas,
fallos de red, recuperación de competiciones, ausencia de consultas duplicadas,
doble envío, cancelación por logout, transporte con timeout y respeto del permiso
offline. Las pruebas de acceso usan clientes simulados: no se ha iniciado sesión
con credenciales reales ni se ha medido todavía la latencia real del servidor.

Todo sigue en local, sin instalador ni publicación.
