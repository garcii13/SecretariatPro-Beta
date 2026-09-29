Live y Manager se distribuyen como aplicaciones independientes. Windows x64 incluye dos instaladores `.exe`; Mac dispone de un DMG por aplicación para Apple Silicon y otro para Intel.

Se conservan las funciones existentes: cámara y captura de ventanas, OCR y modelos SP-OCR v0.7/SP-SCORE v0.2, gráficos, OBS, tablet, repeticiones, gestión de competiciones, importación de datos e identidad visual. Esta versión reduce trabajo repetido de vídeo, escrituras y actualizaciones de interfaz, y mejora los tiempos de espera y recuperación del inicio de sesión.

El envío de muestras OCR conserva una cola local hasta recibir confirmación del laboratorio. La corrección de permisos de Storage del servidor se prepara aparte; este instalador no aplica migraciones a Supabase.

Validación de publicación: pruebas de regresión en Windows y ambas arquitecturas Mac, carga del ejecutable empaquetado de cámara y OCR con ambos modelos, y prueba de instalación, arranque de ventana/backend y desinstalación en Windows. Los SHA-256 permiten verificar cada descarga.

El plugin OBS se instala por separado: [Multicam Replay 0.6.1 beta 3, con selección automática de codificador por hardware](https://github.com/agarciarenones-source/SecretariatPro-Multicam-Replay/releases/tag/0.6.1-beta3).

Paquetes beta sin certificado de editor Windows ni notarización Apple. Falta validar una sesión prolongada con cámaras físicas, OCR, OBS y las cuentas reales del equipo de emisión; la compilación no acredita esa prueba.
