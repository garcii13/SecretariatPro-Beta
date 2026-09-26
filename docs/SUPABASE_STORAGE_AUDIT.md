# Auditoría de espacio en Supabase

Fecha: 2026-09-16

## Uso observado

- Base de datos completa: 17.067.155 bytes (16,3 MiB).
- `ocr-training-samples`: 595 objetos, 2.248.403 bytes.
- `workspace-assets`: 5 objetos, 560.202 bytes.
- `avatars`: 1 objeto, 40.077 bytes.
- `sp_ocr_samples`: 351 filas y 925.696 bytes incluyendo índices.
- No hay sesiones activas antiguas, sesiones de tablet expiradas ni trabajos de importación acumulados.

## Hallazgos

- 244 objetos OCR (1.716.412 bytes) no tienen una fila asociada en `sp_ocr_samples`.
- Un logotipo de equipo (106.393 bytes) ya no está referenciado.
- No hay avatares huérfanos ni filas OCR cuyo archivo haya desaparecido.

La causa principal era el orden del flujo OCR: se subía una imagen con un UUID nuevo y después el RPC resolvía el duplicado mediante `ON CONFLICT`. La fila existente se conservaba, pero el nuevo objeto quedaba sin referencia.

## Corrección

- `sp_find_ocr_sample` comprueba el hash antes de subir el archivo sin exponer la tabla privada.
- Las nuevas rutas OCR son deterministas por workspace, campo, modelo y SHA-256.
- Storage utiliza `upsert` en esa ruta determinista para cubrir envíos simultáneos.
- La eliminación de los 245 objetos existentes queda separada de la migración para requerir una autorización expresa, ya que borra datos en la nube.

