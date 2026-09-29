Esta entrega actualiza únicamente SecretariatPro Live para Mac (Apple Silicon e Intel). No sustituye los instaladores de Windows ni Manager.

Corrige el arranque de cámaras: el proceso aislado utiliza el ejecutable de Live ya instalado, en lugar de descomprimir todo el motor OCR antes de abrir la cámara. Selección y previsualización comparten un único arranque, evitando que dos peticiones cierren mutuamente sus procesos.

La previsualización muestra el error real, descarta respuestas de fuentes anteriores y solo permite dibujar regiones sobre una imagen cargada. Las actualizaciones de estado no borran el error ni cambian una selección sin guardar. OCR detenido, fuente sin imagen y lectura en marcha tienen estados distintos.

Se conserva la captura exclusiva de ventanas por identificador, cámara, perspectiva, todas las regiones OCR, los modelos SP-OCR y SP-SCORE y las demás funciones de Live. La aplicación muestra la versión real y guarda los errores de captura en ~/Library/Application Support/SecretariatPro/.runtime/live.log.

Permisos de Mac: esta beta tiene firma ad hoc, no un certificado Developer ID. Si macOS deniega la captura aunque el interruptor esté activado, cierra Live, retira su entrada antigua de Grabación de pantalla y añade la copia actual de Aplicaciones. La app no modifica permisos ni evita los controles del sistema. La persistencia del permiso entre futuras compilaciones requiere una identidad de firma estable.

La entrega comprueba las pruebas de regresión, los diagnósticos empaquetados y el arranque desde los DMG. La prueba de un directo prolongado con todos los equipos sigue siendo necesaria. El permiso de Storage del OCR Lab es una corrección separada de servidor; esta actualización no aplica migraciones a Supabase.
