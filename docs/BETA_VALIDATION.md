# Protocolo de aceptación de la primera beta

Registrar fecha, sistema operativo, arquitectura, instalador y SHA-256 antes de cada recorrido. Usar una cuenta y un partido de pruebas; confirmar en Supabase que se aplicaron `SUPABASE_BETA_VISUAL_SCOPE.sql` y `SUPABASE_BETA_THEME_TRANSACTION.sql`.

| Recorrido | Criterio de aceptación |
| --- | --- |
| Instalación limpia | App y Manager abren sin Python instalado; inicio/cierre y segundo inicio conservan la sesión sin datos de otro ordenador. |
| Permisos | Propietario y gestor pueden publicar identidad general; identidad de competición solo si el plan lo permite. Realizador no puede publicar ni editar identidad desde API. |
| Identidad en directo | Publicar un tamaño/fuente con partido cargado: se ve en overlay en cinco segundos sin cambiar de partido. Desconectar red: se mantiene la identidad anterior. Dos gestores publicando simultáneamente dejan una sola versión activa por ámbito. |
| OBS y fuente | Conectar WebSocket; elegir escena de Programa y proyector. Copiar `overlay.html` desde Directo, pegarlo como fuente de navegador 1920 × 1080 y comprobar que el gráfico coincide con el estado. |
| Marcador | Probar cámara y ventana OCR, tres regiones y lectura fresca. Detener OCR: preflight debe avisar. Pasar a manual, corregir resultado y volver a OCR sin salto inesperado. |
| Cola | Preparar dos gráficos: la vista previa muestra el primero sin alterar Programa; lanzar en orden, retirar otro y cargar nuevo partido: la cola queda vacía. |
| Tablet | QR de cinco minutos y un uso; escanear desde LAN, accionar un gráfico y revocar desde PC. La tablet revocada no puede leer estado ni controlar OBS. Los endpoints de cuenta/configuración devuelven 403 incluso emparejada. |
| Cierre | Registrar un gol y una expulsión, finalizar con resultado confirmado; comprobar acta, clasificación y reinicio seguro sin gráficos anteriores activos. |

Completar estos recorridos al menos en Windows x64, macOS Apple Silicon y macOS Intel si se van a ofrecer las tres arquitecturas. Un fallo en instalación, acceso remoto, identidad o emisión bloquea distribución; registrar reproducción y solución antes de repetir el recorrido.
