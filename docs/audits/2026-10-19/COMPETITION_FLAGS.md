# Banderas por competición y recorte común

El modo internacional se activa en **Competiciones → Editar → Particularidades
de la competición**. La ficha de cada equipo permite adjuntar **Bandera de la
selección**, independiente del escudo principal y alternativo. Los colores,
tipografías, tamaños, periodos y animaciones siguen en Identidad visual.
La selección de competición dentro de la vista previa solo elige qué datos se
previsualizan; no cambia el modo ni las banderas de la competición.

Live combina la paleta publicada con los datos de la competición y las banderas
de los equipos de su espacio. Funciona incluso sin tema publicado. Los cambios
de bandera o de modo se refrescan sin republicar una identidad visual. Cambiar
a una competición de clubes recupera los escudos. La consulta de banderas usa
paginación para conservar equipos más allá del límite de filas de la API.

El marco de las dos banderas toma el mínimo ancho y el mínimo alto de las dos
imágenes, escala a la altura del marcador y limita el ancho a 1,5 veces esa
altura. Se rellena con recorte centrado, sin estirar ni dejar márgenes. Manager
y ambos renderizadores comparten ese resultado. Las miniaturas de los adjuntos,
los originales y los otros gráficos conservan la imagen completa. Si falta una
bandera, se conserva el escudo disponible y no se le aplica el recorte de bandera.

La migración `supabase/migrations/20261019074154_competition_international_flags.sql`
fue aplicada al proyecto conectado. Añade `competitions.is_international` y
`teams.flag_url`. Recupera la identidad publicada efectiva por competición y
las banderas existentes dentro del mismo espacio, manteniendo los temas
históricos y los escudos. Conserva los permisos y las dos políticas restrictivas
de aislamiento de estas tablas. No cambia el OCR Lab.

Validación local: **457 pruebas Python** (dos casos Win32 omitidos en Mac),
**29 pruebas Node de interfaz**, **25 del renderer**, tres pruebas SQL sobre
PostgreSQL local. La migración comprueba originales, repetición, ámbito y
roles. La sonda real `packaging/cloud_competition_flags_probe.sql` supera nueve
controles de lectura, escritura, permisos y conservación del escudo; utiliza
fixtures sintéticos, revierte todos sus datos y no envía correos.

Los avisos cloud previos de funciones del Lab y protección de contraseñas
filtradas no cambian. Referencias: [linter de funciones](https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable)
y [protección de contraseñas filtradas](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
No se ha marcado una aceptación instalada o visual inexistente como aprobada.
Los instaladores beta 11 del run `39112885674` son anteriores a estos cambios;
los nuevos artefactos deben proceder de esta revisión.
