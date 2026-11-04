# Validación de la versión 2.3 local

- Astro Check y compilación Node: sin errores; se conserva el aviso existente de tamaño del bundle.
- 40 pruebas de la web: permisos, cuentas, rosters, actas, firmas, scopes, duplicados, CloudEvents, revisiones y sustitución de proveedor sin borrar recibos.
- 130 comprobaciones HTTP contra el servidor compilado de AEUF.
- 27 comprobaciones cruzadas por HTTP: cliente nativo Python de SecretariatPro ↔ servidor Astro compilado. Gol durante el partido, asistencia, corrección, confirmación local, validación oficial, cola sin red y reapertura. Base temporal y transporte Supabase simulado.
- SecretariatPro: 468 pruebas Python correctas, con dos exclusivas Win32 omitidas en este Mac; 29 pruebas JavaScript correctas y sintaxis de las tres interfaces validada.
- Seguridad de SecretariatPro: tres pruebas de RLS/invitaciones/ámbitos sobre PostgreSQL local correctas. No se retira cobertura anterior.
- Emisión con `assigned_to=null` comprobada en creación y edición; cadenas vacías se normalizan a null. No se amplía el acceso de un realizador limitado a sus partidos asignados.
- Revisión visual de Manager → Federaciones con catálogo sintético e importación simulada correcta. Captura: `outputs/secretariat-federaciones.png`. Comprobación de ancho 390 px: sin desbordamiento horizontal ni imágenes rotas.
- Copia activa `127.0.0.1:4321` actualizada con respaldo previo y verificación del contrato/gestor. Se conserva la base privada y las actas creadas por el usuario.

## Límites de esta entrega

Los conectores nativos están incorporados al código local de Live/Manager, pero no se han activado con credenciales de producción ni se han construido o publicado instaladores nuevos. Las pruebas no sustituyen Windows/Intel nativos, la aplicación instalada ni una mesa real con OBS/cámaras/replay.

La base Supabase SecretariatPRO se ha consultado de forma estructural: `assigned_to` admite null y `broadcast_enabled` es independiente. No se han ejecutado migraciones ni modificado datos, RLS, usuarios o claves de esa base. La importación federativa a Supabase usa las operaciones/RLS existentes y aún requiere aceptación con una sesión real antes de activar su automatismo.

El contrato nuevo es propio, publicado con OpenAPI y CloudEvents; su autenticación implementada es HMAC por conexión, no OAuth. El catálogo materializado usa varias operaciones remotas: una importación interrumpida se revisa y reintenta, no se presenta como transacción única.

Para mesas remotas hacen falta URL accesible, HTTPS y un servidor federativo disponible. PGlite/SSE locales conservan los límites de escala documentados en Sports Exchange. SMTP real sigue sin configurarse.

