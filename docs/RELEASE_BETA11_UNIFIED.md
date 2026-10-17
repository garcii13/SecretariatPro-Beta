# SecretariatPro 1.0.0-beta.11 · base común

Integra las correcciones de Mac beta 8 y Windows beta 10: arranque de cámaras y
captura exclusiva de ventanas en Mac; coordenadas físicas DPI y aplicación de
regiones guardadas al OCR activo en Windows. Conserva las mejoras locales del
consenso temporal del reloj. Las dependencias OCR mantienen sus versiones
específicas para cada plataforma.

Manager → Identidad visual → Competiciones de selecciones permite activar
«Competición internacional · usar banderas» y adjuntar una imagen por selección.
Se guardan en la identidad publicada, separadas de los escudos originales.
Aparecen en marcador, bottoms, ficha, previa, descanso, alineaciones, goleadores
y penaltis. La clasificación existente sigue mostrando sus nombres y datos.
No hace falta migrar la base de datos: la configuración vive en el JSON de la
identidad y los archivos en el almacenamiento de recursos del espacio.

En el marcador ambas banderas comparten ancho visible. El máximo es 1,5 veces
su altura: 141 px con el diseño de 94 px de alto, antes de aplicar la escala
publicada. Las proporciones se conservan y no se recorta ninguna imagen. Si
una bandera es cuadrada o vertical, se reduce el ancho de ambas para respetar
la altura. El límite se calcula con las dos imágenes cargadas.

Los goles incorporan una animación de 1,6 segundos de derecha a izquierda con
el color del equipo: GOL / GOAL / MÅL / GÓL / MAALI / TOR según el idioma de Live.
Se muestra tras la vuelta confirmada del replay o la espera configurada. Luego
el goleador y la asistencia permanecen todo el tiempo configurado en Manager;
al retirar el bottom vuelve el marcador. Limpiar emisión cancela la secuencia.

Estado de esta entrega: implementación de código local y pruebas automatizadas.
No se han generado ni publicado instaladores nuevos. Pendientes la validación
nativa en Windows, la revisión visual y la prueba real con OBS/cámaras.
