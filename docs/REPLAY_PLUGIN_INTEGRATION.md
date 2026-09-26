# Integración de replay

SecretariatPro controla `SecretariatPro Multicam Replay` mediante obs-websocket v5. Cada marca guarda simultáneamente todos los ángulos configurados, los registra con los metadatos del partido y permite usar el ángulo principal en el vídeo de highlights.

## Contrato visual

- Salida final: 1920 × 1080, 30 fps.
- Fuentes con una resolución inferior: escalado proporcional hasta cubrir el lienzo completo.
- Si cambia la relación de aspecto: recorte centrado del sobrante, sin bandas negras y sin deformación.
- Los clips se montan por orden cronológico.

## Integración v0.4

- El plugin registra atajos nativos para activar el búfer, marcar, lanzar, volver a directo y cambiar de cámara.
- La aplicación usa la petición estándar `TriggerHotkeyByName` de OBS WebSocket, aunque no haya una tecla asignada.
- El plugin publica de forma atómica `secretariatpro-bridge.json` en su carpeta de configuración de OBS.
- El puente incluye estado del búfer y reproducción, cámara activa, número de cámaras, serie del evento, errores y rutas de todos los clips ISO.
- SecretariatPro conserva cada ángulo en la biblioteca y ofrece un enlace independiente para CAM 1, CAM 2, etc.
- Si el plugin no está instalado, la aplicación conserva el búfer nativo de OBS como alternativa.

No se abre ningún puerto adicional. El archivo solo se comparte en el mismo ordenador y los controles viajan por la conexión OBS WebSocket ya configurada.

## Escalado de cámara

El plugin calcula un ajuste `cover` contra el lienzo base activo de OBS. Una cámara 1280×720 se amplía a 1920×1080; una cámara 4:3 o vertical también llena el lienzo y recorta de forma centrada el sobrante. Las pruebas independientes de layout cubren los tres casos.
