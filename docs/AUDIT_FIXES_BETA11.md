# Correcciones de la auditoría — beta 11

18 de octubre de 2026. El OCR Lab queda excluido: no se han modificado sus fuentes, modelos, datos ni entorno.

## Resultado por hallazgo

| Auditoría | Corrección y estado |
| --- | --- |
| A01 · orden de respuestas | Corregido. Una lectura acotada en curso, arranque compartido, cancelación por timeout y descarte de revisiones antiguas. Los errores conservan el último marcador válido. |
| A02 · acceso local | Corregido en Live y Manager. Host/puerto y Origin verificados antes de ejecutar rutas; rechazo de orígenes cruzados y `null`; sesión de navegador HttpOnly/SameSite Strict propia de cada producto. También cubre WebSocket. |
| A03 · invitaciones | Corregido en fuentes y probado en PostgreSQL local. RPC autenticado e inserción atómica que conserva íntegramente una membresía existente, incluido propietario o suspensión. Pendiente desplegar RPC y función en Supabase. |
| A04 · dependencias Python | Actualizadas y auditadas en este Mac: cero avisos conocidos, sin incompatibilidades declaradas. OCR nuevo comparado con el anterior; Windows/Intel requieren sus builds nativos. |
| A05 · dependencias web | Lockfile actualizado, Astro 7.4.0 y Sharp 0.35.5. Instalación limpia, auditoría cero y 16 páginas compiladas. Renderer y pruebas SQL también tienen auditoría en CI. |
| A06 · aceptación instalada | Publicación protegida: exige evidencias ligadas al commit y SHA-256 de cada instalador, con recorridos reales de hardware y cloud. Esos recorridos siguen pendientes; no se han dado por aprobados. |
| A07 · reproducibilidad | Fuentes, assets, tests y documentación se registran juntos; copia ejecutable y checkout sincronizados. Se comprueba un clon local limpio. El remoto de publicación accesible es `installers`; `origin` se conserva, sin cambiar sus permisos o URL. |
| A08 · transporte y deuda visual | Transporte aislado en `OverlayPoller`; una petición por frame en la API actual, con estado, contexto, revisión y TXT juntos. Se mantiene respaldo para servidores antiguos. El CSS heredado continúa como deuda para una migración por paneles, conservando las funcionalidades. |
| A09 · Lab | Excluido por petición del usuario. |
| A10 · operación cloud | Inventario SQL de solo lectura y aceptación cloud obligatoria antes de publicar. No hay conexión administrativa disponible para desplegar ni certificar RLS, SMTP o restauraciones reales. |

## Emisión y acceso local

`ApplicationRuntime.overlay_snapshot()` toma estado, resultado bruto y resultado gráfico bajo el contexto de partido. La API adjunta época de proceso y revisión creciente sin escribir esa información en los datos guardados. La previsualización de cola usa el mismo contrato, sin alterar Programa.

El marcador mantiene el resultado bruto OCR/manual; el gol y el descanso conservan el resultado gráfico confirmado. Los valores vacíos, errores HTTP o contenido no válido no borran el último resultado. Una petición que vence pierde el permiso para escribir en pantalla, aunque el navegador entregue su respuesta después.

Con la API nueva el overlay obtiene el frame en una petición cada 250 ms, en lugar de JSON y tres TXT por separado. Los ajustes que llegan en el estado son prioritarios; un fallback de ajustes tardío no puede sobrescribirlos. La compatibilidad JSON+TXT continúa para la referencia y APIs antiguas. El gol sigue perteneciendo a BroadcastFlow; powerplays y EMPTY NET conservan su representación y reloj del servidor.

Las páginas locales emiten una cookie de sesión distinta para Live y Manager. Los navegadores deben presentar esa sesión y el origen exacto al llamar a APIs sensibles o WebSocket. Se mantienen los clientes nativos sin Origin, la URL habitual de OBS y el emparejamiento de tablet existente. Las páginas se revalidan o se sirven sin almacenamiento para renovar la sesión al reiniciar. Host solo permite loopback, nombres/direcciones del ordenador y el puerto del servicio; no resuelve nombres enviados por el cliente.

## Runtime OCR Mac

La nueva combinación conserva la API PaddleOCR 2.x, el modelo PP-OCRv4, la CPU de un hilo y PIR/MKLDNN desactivados en el worker:

- PaddlePaddle 3.0.0; PaddleOCR 2.10.0.
- NumPy 1.26.4; ruedas OpenCV fijadas a 4.10.0.84 para mantener el mismo ABI.
- SP-OCR 0.7, SP-SCORE 0.2, joblib 1.5.3 y scikit-learn 1.8.0 conservados.
- Se elimina `imgaug`, que ya no es dependencia de PaddleOCR 2.10. Se actualizan además multidict, PyJWT, urllib3 y Werkzeug.

Primero se instaló el candidato en una venv temporal independiente. Se compararon 64 ROIs sintéticas y tres imágenes de referencia públicas del repositorio: **67 lecturas idénticas**. En las sintéticas ambos motores acertaron 60/64; no se presenta esta muestra como precisión de partidos reales. Los dos especialistas cargan y sus hashes coinciden con el manifiesto. Después se actualizó la venv de la copia ejecutable y se repitió la comparación: cero diferencias.

El worker actualizado supera inferencia real `12:34`, carga de ambos modelos y diagnóstico de runtime de cámara/OpenCV. Esto no prueba una cámara física ni un ejecutable congelado. `packaging/check_worker.py` exige ahora inferencia real también en los builds Mac, además de Windows. No se han fabricado ni distribuido instaladores nuevos.

La comparación puede repetirse en Mac con:

```sh
.venv/bin/python packaging/benchmark_ocr_runtime.py \
  --reference docs/audits/2026-10-18/fixes/ocr-baseline.json \
  --output /tmp/secretariat-ocr-check.json
```

La referencia usa Arial del sistema de Mac y las imágenes públicas indicadas. Las evidencias no contienen muestras del Lab ni datos de clientes.

## Despliegue pendiente en Supabase

Orden necesario, con una conexión administrativa al proyecto correcto:

1. Ejecutar `SUPABASE_AUDIT_INVITATIONS.sql`. Crea el RPC, valida JWT/rol/ámbito y limita EXECUTE a authenticated. No cambia membresías existentes.
2. Desplegar `supabase/functions/invite-member/index.ts`. La función verifica al solicitante y llama al RPC con su JWT. No utiliza service role para sobrescribir membresías. El directorio legacy solo inserta si falta el usuario; no pisa su workspace o perfil anterior.
3. Ejecutar `SUPABASE_AUDIT_VERIFY.sql` y guardar el inventario de RLS, políticas, permisos, versiones de funciones y buckets. Es de solo lectura.
4. Ejecutar el protocolo con cuentas y partidos de prueba: dos workspaces, owner/manager/producer, miembro suspendido, invitación repetida, publicación concurrente, recuperación y restauración.

La función nueva requiere el RPC: no desplegarla antes del SQL. Si la migración falta, la operación devuelve error; no vuelve al upsert inseguro. La prueba local ejecuta el SQL real en PostgreSQL/WASM con el esquema de membresías y verifica propietario, suspensión, idempotencia, roles, ámbito, usuario confirmado/no confirmado y permisos de ejecución. No simula los triggers o las políticas del proyecto desplegado.

No se han buscado ni utilizado credenciales del Lab. No se dispone de token administrativo, service role o conexión SQL del producto en este entorno, por lo que el despliegue remoto permanece pendiente.

## Publicación y evidencias de aceptación

El workflow de publicación requiere `acceptance_json`; el publicador valida su contenido antes de crear o editar releases. Debe corresponder a los commits de los builds seleccionados y a todos los instaladores que se publicarán. No basta con que la compilación termine bien.

Formato de referencia, **incompleto deliberadamente** hasta hacer las pruebas:

```json
{
  "version": "1.0.0-beta.11",
  "reviewer": "",
  "checked_at": "",
  "cloud": {
    "tenant_isolation": false,
    "roles": false,
    "invitations": false,
    "concurrent_theme_publication": false,
    "account_recovery": false,
    "backup_restore": false
  },
  "platforms": {
    "windows-2022": {
      "commit": "SHA completo del build",
      "artifacts": {"nombre exacto del instalador": "SHA-256"},
      "installed": false,
      "visual": false,
      "camera_ocr": false,
      "obs_multicam": false,
      "powerplays": false,
      "export_and_finish": false
    }
  }
}
```

Añadir `macos-15` y `macos-15-intel` si se publican esas plataformas, con sus propias evidencias. En publicación completa, `artifacts` de cada plataforma incluye tanto Live como Manager. El modo Mac Live acepta únicamente sus DMG. La evidencia válida requiere todos los recorridos aplicables a true, responsable, fecha, commits y hashes coincidentes. No se han rellenado aprobaciones inexistentes.

## Comprobaciones locales

- 445 pruebas Python, con dos Win32 omitidas; sin fallos.
- 27 pruebas Node de OCR/presentación/Manager/movimiento y 24 del bundle compilado; correctas.
- Prueba SQL sobre PostgreSQL local correcta; auditoría npm de ese proyecto sin avisos.
- Svelte/TypeScript sin errores ni avisos; sintaxis de las interfaces correcta.
- Auditorías Python, web y renderer sin vulnerabilidades conocidas en la consulta actual; `pip check` correcto.
- Astro: 16 páginas compiladas tras instalación limpia.
- Inferencia real del worker, especialistas y runtime de cámara correctos; 67 lecturas comparadas sin diferencias.
- Fuentes y assets sincronizados; hashes del bundle comprobados. Clon limpio y estado Git registrados al cerrar el trabajo.

Continúan pendientes Windows nativo, Intel nativo, aplicaciones congeladas/instaladas, sesión real OBS/cámara/multicámara, revisión visual y despliegue/aceptación cloud. La ausencia de avisos del catálogo no garantiza ausencia de vulnerabilidades. Las evidencias actuales están en `docs/audits/2026-10-18/fixes/`.
