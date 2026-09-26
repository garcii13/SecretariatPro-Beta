# Auditoría de beta · 18 de septiembre de 2026

Estado: **candidata a beta privada**. La versión local `71.0.0-beta-rc` supera 294 pruebas y las comprobaciones sintácticas de Python/JavaScript. Esta iteración de Secretariat Pro Live y Secretariat Pro Manager se entrega como código local, sin regenerar sus instaladores.

## Funciones incluidas

- Tamaño y tipografía independientes para marcador, goles/avisos, ficha de jugador, previa, descanso, alineaciones, goleadores, clasificación y penaltis.
- Identidad general o asociada a competición, publicada exclusivamente por propietario o gestor. La API recompone la identidad publicada y evita que el realizador la modifique.
- Comprobación previa de directo cerrable. OBS, monitor de Programa, tablet, logotipos e identidad incompleta generan avisos; solo membresía, partido y una fuente de marcador válida bloquean la salida.
- Monitor fluido de la escena Program obtenido exclusivamente por OBS WebSocket, sin capturar el escritorio ni otras aplicaciones.
- Cola de gráficos con nombre, vista previa fuera de emisión, reordenación, retirada manual o temporizada y protección frente a temporizadores antiguos.
- Replays multicámara mediante el plugin nativo 0.5.0: marcas manuales y automáticas en goles, composición rápida por cámara, duración y velocidad, retorno automático al directo y vídeo de highlights cronológico. Emitir una composición siempre la guarda antes en la biblioteca.
- En los goles, el marcador se oculta y reaparece junto al cartel del goleador. Con plugin espera al final de la repetición; sin plugin usa una espera definida por el Manager. El Manager también define cuánto permanece visible el cartel.
- Secuencias personales de grafismos para cada realizador, con duración de cada elemento e intervalo entre apariciones.
- Los highlights se normalizan a 1920 × 1080 y 30 fps; cámaras de menor resolución rellenan el cuadro mediante escalado y recorte centrado, sin barras laterales.
- Indicador opcional de periodo bajo el reloj, con entre 1 y 12 secciones y etiquetas definidas por el Manager. El realizador solo selecciona el periodo activo.
- QR temporal y de un solo uso para tablet, sesiones individuales revocables y lista cerrada de operaciones LAN.
- Idioma inicial derivado del sistema (`es`, `en`, `sv`, `cs`, `fi`, `de`), con inglés como respaldo.
- Invitaciones desde Manager a cuentas existentes o nuevas, aceptación automática por correo dentro del espacio y portal bilingüe dentro de la web oficial para contraseña, nombre, avatar y membresías.
- Copia del enlace de `overlay.html` mediante el portapapeles nativo de macOS/Windows, con respaldo del navegador.

## Seguridad y datos

- `competition_standings` utiliza `security_invoker=true`; `anon` no tiene lectura y `authenticated` conserva el acceso sujeto a RLS de las tablas base.
- `invite-member` valida el JWT dentro de la función y exige rol `owner` o `competition_manager` mediante `sp_has_workspace_role`. La clave `service_role` permanece únicamente en Supabase.
- `sp_accept_my_invitations()` solo permite al usuario autenticado aceptar invitaciones que coinciden con su propio correo.
- La configuración pública contiene URL, clave publicable y URL del portal. `.env`, credenciales OBS, sesiones, partidos locales, muestras OCR y datos de usuario quedan fuera del repositorio y de los instaladores.
- El endpoint de portapapeles solo admite clientes loopback; la tablet no puede invocarlo.
- La web se actualizó a Astro 7.3.2 y Sharp 0.35.4; `npm audit` informa de cero vulnerabilidades.

## Repositorio y construcción

- Se retiró la documentación histórica por fases, los paquetes fuente multipart y utilidades de restauración antiguas.
- Los únicos modelos activos son SP-OCR v0.7 y SP-SCORE v0.2. GitHub Actions los obtiene del release privado `ocr-models-v0.7-v0.2` y verifica los SHA-256 declarados en `models/MANIFEST_SP_OCR.json`.
- El workflow genera Windows x64, macOS ARM64 y macOS Intel, registra dependencias resueltas y publica instalador más SHA-256 como artefactos de 30 días.
- El workflow de web ejecuta `npm ci`, auditoría de seguridad y compilación estática, y conserva el resultado como artefacto verificable.
- Windows y macOS todavía carecen de firma comercial/notarización. macOS utiliza firma ad hoc.

## Validación automática

- 294 pruebas unitarias y de integración: aprobadas.
- `node --check` para aplicación, Manager y overlay: aprobado.
- Revisión visual a 1280 × 800 y al tamaño mínimo 860 × 580: sin desbordamiento horizontal ni solapamientos en Producción, cola, replays e identidad del Manager.
- `pip check`: aprobado.
- Paquete OCR del release: extracción y SHA-256 aprobados localmente.
- Astro: 16 rutas estáticas compiladas y revisión visual ES/EN aprobada.
- Dependencias web: cero vulnerabilidades conocidas en `npm audit`.

## Bloqueos antes de distribuir

1. Publicar la web Astro en `https://secretariatproapp.com` y verificar `/cuenta` y `/en/account` sobre HTTPS.
2. Configurar y probar el SMTP personalizado de Supabase con `noreply@secretariatproapp.com`, incluida una invitación real y la creación de contraseña en el portal.
3. Ejecutar el [protocolo de aceptación](BETA_VALIDATION.md) en instalaciones limpias: login, OBS, cámara/ventana, OCR, enlace del overlay, tablet, publicación de identidad y cierre de partido.
4. Probar con cuentas reales de propietario, gestor y realizador, incluidos dos gestores publicando a la vez.
5. Validar la descarga o advertencia del sistema operativo causada por la ausencia de firma comercial antes de entregar la beta a terceros.
6. Ejecutar el protocolo de replay con hardware real: dos o más cámaras, marca de gol, composición al 50 %, retorno automático, cartel del goleador y exportación de highlights.

## Revisión de realización y replay — septiembre 2026

Flujo y comprobaciones detallados en [REPLAY_WORKFLOW.md](REPLAY_WORKFLOW.md). El marcador sigue usando OCR; el contador interno pertenece a los gráficos de gol. Constructor integrado en SecretariatDeck, biblioteca local persistente, cuatro velocidades, vuelta a directo confirmada, periodo dentro del reloj y contraste corregido en modo claro. Live/Manager se entregan como archivos locales; el plugin requiere la versión 0.6.0 para lanzar vídeos de la biblioteca.
