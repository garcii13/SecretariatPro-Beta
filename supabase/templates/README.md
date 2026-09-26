# Plantillas de autenticación

Copiar estas plantillas en Supabase > Authentication > Emails > Templates después de habilitar el SMTP personalizado.

- **Invite user**
  - Asunto: `Tu invitación a SecretariatPro · Your SecretariatPro invitation`
  - Contenido: `invite.html`
- **Reset password**
  - Asunto: `Restablece tu contraseña de SecretariatPro · Reset your SecretariatPro password`
  - Contenido: `recovery.html`

Ambas plantillas usan `{{ .ConfirmationURL }}`, generado y validado por Supabase. No añadir enlaces de seguimiento ni sustituir esta variable por una URL fija.
