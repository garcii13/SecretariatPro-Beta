# SecretariatPro Live / SecretariatPro Manager · beta.5

Se generan instaladores independientes para cada aplicación:

- Windows x64: `SecretariatPro-Live-1.0.0-beta.5-windows-x64-setup.exe` y equivalente Manager.
- macOS Apple Silicon e Intel: un DMG de cada aplicación por arquitectura. Arrastrar la aplicación a Applications.

Windows instala por usuario, sin requerir Python, con accesos en Inicio, acceso opcional en el escritorio y desinstalación independiente. El asistente incluye WebView2 Evergreen x64 para instalarlo sin descargarlo durante la instalación si falta; se verifica la firma Microsoft al preparar el paquete. No se eliminan cuentas, ajustes ni vídeos del usuario al desinstalar. El antiguo instalador conjunto tiene otra identidad: se puede desinstalar por separado.

El workflow `Beta installers` admite todas las plataformas o una sola. Los modelos privados se descargan de la release `ocr-models-v0.7-v0.2` del mismo repositorio y se verifican con el manifiesto SHA-256. Las compilaciones pasan las pruebas y las comprobaciones de JavaScript. En Windows se prueba además la instalación silenciosa, el backend, la ventana nativa y la desinstalación de cada instalador en el runner.

Construcción local: `BUILD_INSTALLERS_WINDOWS.bat` o `BUILD_INSTALLERS_MAC.command`, con los modelos verificados presentes en `models/` y Python 3.12 instalado. Windows requiere Inno Setup 6 (el script de prerrequisitos puede instalarlo mediante Chocolatey). Los archivos se escriben en `release/` con sus SHA-256.

Los ejecutables Windows no tienen certificado de editor y macOS usa firma ad hoc, sin notarización Apple. La prueba de arranque automatizada no sustituye probar cámara, OCR, OBS y emparejamiento en equipos físicos.

Referencia de WebView2: https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution
