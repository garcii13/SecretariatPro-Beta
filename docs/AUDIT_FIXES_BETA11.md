# Correcciones de la auditoría — beta 11

18 de octubre de 2026. El OCR Lab queda excluido: no se han modificado sus fuentes, modelos, datos ni entorno.

## Resultado por hallazgo

| Auditoría | Corrección y estado |
| --- | --- |
| A01 · orden de respuestas | Corregido. Una lectura acotada en curso, arranque compartido, cancelación por timeout y descarte de revisiones antiguas. Los errores conservan el último marcador válido. |
| A02 · acceso local | Corregido en Live y Manager. Host/puerto y Origin verificados antes de ejecutar rutas; rechazo de orígenes cruzados y `null`; sesión de navegador HttpOnly/SameSite Strict propia de cada producto. También cubre WebSocket. |
| A03 · invitaciones | Desplegado y probado en Supabase real. RPC idempotente, ruta legacy corregida y triggers contra escalada/alteración del propietario; 12 controles con RLS y datos sintéticos revertidos. HTTP sin JWT o con JWT inválido devuelve 401. |
| A04 · dependencias Python | Actualizadas y auditadas en este Mac: cero avisos conocidos, sin incompatibilidades declaradas. OCR nuevo comparado con el anterior; Windows/Intel requieren sus builds nativos. |
| A05 · dependencias web | Lockfile actualizado, Astro 7.4.0 y Sharp 0.35.5. Instalación limpia, auditoría cero y 16 páginas compiladas. Renderer y pruebas SQL también tienen auditoría en CI. |
| A06 · aceptación instalada | Publicación protegida: exige evidencias ligadas al commit y SHA-256 de cada instalador, con recorridos reales de hardware y cloud. Las comprobaciones instaladas nativas y el replay desde fuentes con cámara interna/virtual ya pasan. Siguen pendientes la revisión visual, OCR de un marcador real, DPI real y la aceptación cloud que se detalla abajo. |
| A07 · reproducibilidad | Fuentes, assets, tests y documentación se registran juntos; copia ejecutable y checkout sincronizados. Se comprueba un clon local limpio. El remoto de publicación accesible es `installers`; `origin` se conserva, sin cambiar sus permisos o URL. |
| A08 · transporte y deuda visual | Transporte aislado en `OverlayPoller`; una petición por frame en la API actual, con estado, contexto, revisión y TXT juntos. Se mantiene respaldo para servidores antiguos. El CSS heredado continúa como deuda para una migración por paneles, conservando las funcionalidades. |
| A09 · Lab | Excluido por petición del usuario. |
| A10 · operación cloud | Inventario real, tres migraciones aplicadas y Edge v4 desplegada. RLS/roles/invitaciones comprobados con fixtures sintéticos. Siguen pendientes concurrencia real, recuperación por correo y restauración de copia. |

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

El worker actualizado supera inferencia real `12:34`, carga de ambos modelos y diagnóstico de runtime de cámara/OpenCV. Esto no prueba una cámara física ni un ejecutable congelado. `packaging/check_worker.py` exige ahora inferencia real también en los builds Mac, además de Windows. Se han solicitado instaladores de comprobación nativos en CI; no se han distribuido releases nuevos.

La comparación puede repetirse en Mac con:

```sh
.venv/bin/python packaging/benchmark_ocr_runtime.py \
  --reference docs/audits/2026-10-18/fixes/ocr-baseline.json \
  --output /tmp/secretariat-ocr-check.json
```

La referencia usa Arial del sistema de Mac y las imágenes públicas indicadas. Las evidencias no contienen muestras del Lab ni datos de clientes.

## Despliegue y comprobación real de Supabase

Proyecto verificado: SecretariatPRO (`yjiegitbskiolwkglcfl`). Se aplicaron:

1. `20261018081649 · audit_idempotent_workspace_invitations`, desde `SUPABASE_AUDIT_INVITATIONS.sql`.
2. Edge `invite-member` versión 4, con SDK fijado, autenticación propia mediante `auth.getUser` y RPC con el JWT del solicitante. La fuente recuperada coincide con la local. `verify_jwt=false` conserva la configuración existente; no elimina la comprobación de sesión del código.
3. `20261018082205 · audit_membership_guards_and_legacy_rpc`, desde `SUPABASE_AUDIT_MEMBERSHIP_GUARDS.sql`.
4. `20261018085458 · audit_restore_canonical_owner_roles`, desde `SUPABASE_AUDIT_REPAIR_OWNER_ROLE.sql`.

La revisión del esquema real encontró una ruta legacy con upsert y permisos directos que permitían evitar la protección de la interfaz. La segunda migración convierte esa ruta en idempotente, protege identidad y rol del propietario, impide autoasignarse owner o transferirlo y reserva el cambio de deporte al propietario. Conserva las ediciones legítimas de otros miembros y las cascadas de eliminación de cuenta/espacio. Restringe RPC anónimos ajenos al Lab y fija search_path en cuatro funciones existentes.

`packaging/cloud_membership_probe.sql` ejecutó **12 controles sobre PostgreSQL desplegado**, con roles authenticated, JWT local y RLS reales: aislamiento de espacios, propietario reinvitado por ambas rutas, suspensión conservada, invitación a espacio ajeno, autoescalada, suspensión/borrado/transferencia del propietario, cambio de deporte por manager, invitación por producer y cambio legítimo por owner. Todo se revirtió con ROLLBACK y no quedaron usuarios de prueba. Las sondas no enviaron correos ni modificaron cuentas de clientes. Después se detectó una membresía histórica de propietario rebajada a competition_manager y se restauró exclusivamente su rol, tomando owner_user_id como autoridad. Se conservan propietario, estado y resto de miembros; el SQL excluye suspendidos, invitados y espacios borrados. La comprobación posterior encuentra cero discrepancias y cero filas temporales.

La función desplegada responde **401 sin JWT y con JWT inválido**, y **405 a GET**. Esto comprueba el endpoint real y no equivale a un login completo o entrega SMTP.

Dos sesiones de publicación de temas produjeron versiones 1 y 2 y una única identidad activa. Aunque se solicitaron en paralelo, sus transacciones no se solaparon: el conector las serializó. **No se considera una prueba de concurrencia real.** Los dos usuarios, el espacio y los temas temporales se eliminaron y se comprobó que no quedaban fixtures.

El inventario posterior ya no detecta search_path mutable ni funciones SECURITY DEFINER anónimas fuera del Lab. Permanecen los RPC autenticados previstos con comprobaciones internas. El Lab queda intacto, incluidos sus avisos. La protección de contraseñas filtradas sigue desactivada; no se ha cambiado la configuración de Auth ni contratado un plan. [Configuración de protección de contraseñas](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

Evidencia resumida sin secretos: `docs/audits/2026-10-18/fixes/deployed-validation.json` y `edge-http-validation.json`. Continúan pendientes concurrencia efectiva, recuperación Auth/SMTP y restauración de copias; no se han marcado como aceptadas.

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

- 451 pruebas Python en Mac tras la corrección adicional del puente de replay, con dos Win32 omitidas; sin fallos. La revisión anterior de 447 casos también pasa en Windows e Intel nativos.
- 27 pruebas Node de OCR/presentación/Manager/movimiento y 24 del bundle compilado; correctas.
- Dos pruebas SQL sobre PostgreSQL local correctas, incluidos triggers y RLS; auditoría npm sin avisos. Se añaden los controles reales descritos arriba.
- Svelte/TypeScript y la función de invitación comprobada con Deno: sin errores; sintaxis de las interfaces correcta.
- Auditorías Python, web y renderer sin vulnerabilidades conocidas en la consulta actual; `pip check` correcto.
- Astro: 16 páginas compiladas tras instalación limpia.
- Inferencia real del worker, especialistas y runtime de cámara correctos; 67 lecturas comparadas sin diferencias.
- Fuentes y assets sincronizados; hashes del bundle comprobados. Clon limpio y estado Git registrados al cerrar el trabajo.

El código final de aplicación `f98ef98` supera regresiones e instaladores en Windows x64, Mac ARM64 y Mac Intel. Pasan arranque de Live/Manager e inferencia OCR instalada; Windows incluye instalación/desinstalación y Mac montaje/copia desde DMG y comprobación de firma local. La omisión de módulos compilados de chardet se corrigió en `100702d` con un hook exclusivo de Windows para Live, Manager y OCR. OBS 32.2.2 supera los recorridos sintético e interna/virtual descritos abajo; no se activó streaming ni grabación general. Continúan pendientes OCR sobre marcador real, captura de ventana con DPI real, revisión visual y la parte de aceptación cloud indicada arriba. La prueba OBS interna/virtual desde fuentes sí está completada. La ausencia de avisos del catálogo no garantiza ausencia de vulnerabilidades. Las evidencias actuales están en `docs/audits/2026-10-18/fixes/`.


## Recuperación desde Git

Se verificó el commit de implementación `1101ae3` mediante un clon limpio local,
restaurando únicamente los dos modelos del manifiesto con SHA-256 comprobado.
`npm ci` y la recompilación reproducen exactamente los assets versionados: Git
permanece limpio después del build. El clon supera 445 casos Python (dos Win32
omitidos), 27 Node, 24 del renderer y la prueba PostgreSQL de invitaciones. Las
pruebas Python usan la venv Mac ya verificada; esto no equivale a instalar en
un Mac Intel o Windows nuevo. La rama completa está subida a `installers`; no se han publicado releases. La evidencia del clon corresponde a esa revisión inicial y no sustituye el CI de los commits posteriores.

## Temporización y portabilidad Windows

La primera ejecución nativa encontró lecturas de tests dependientes de cp1252, una comparación de rutas Mac simuladas en Windows y el despertar anticipado de asyncio por la resolución del reloj Windows. Se fijó UTF-8 explícito, se normalizó la ruta del intérprete y BroadcastFlow espera ahora una fecha límite de perf_counter para intro, transición, goleador y retraso configurado. Dos casos nuevos prueban despertares anticipados y cancelación; no se redujo la cobertura ni la duración esperada del goleador.

- [Regresiones de la revisión 8d3d274](https://github.com/garcii13/SecretariatPro-Beta/actions/runs/39111429484).
- [Instaladores de comprobación de la misma revisión](https://github.com/garcii13/SecretariatPro-Beta/actions/runs/39111579906).

Las compilaciones son artefactos de comprobación. El control de publicación sigue exigiendo aceptación instalada, visual, hardware y cloud antes de distribuir.

## Verificación nativa de replay y corrección adicional

Se abrió OBS 32.2.2 y se comprobó el puente WebSocket 5.7.4 con el plugin instalado **0.6.0**. Se creó una colección de prueba aparte con dos fuentes sintéticas roja/azul. El plugin guardó dos clips distintos a 1920×1080, con 398 fotogramas cada uno; ambos se decodifican y conservan sus colores. Pasaron composición de dos planos, reproducción, cambio manual de ángulo, vuelta al directo y parada de búfer. La colección original quedó activa y no hubo streaming ni grabación general.

Esta sesión descubrió que `_wait_for` rechazaba una activación válida al leer el error de la orden anterior antes de la confirmación asíncrona de OBS. `f98ef98` conserva ese error solo como referencia: espera confirmación, informa de errores nuevos inmediatamente y conserva el error persistente al vencer el plazo. Cuatro tests nuevos cubren activación, salida, reproducción, cambio de cámara y fracaso persistente; 451 casos Python pasan.

Las pruebas C++ de timeline, layout y selección de codificador también pasan con clang++ C++17 y avisos como errores. Corresponden al checkout del plugin `0b289db`; no se afirma que sea el mismo código del binario 0.6.0 instalado.

Tras desbloquear el Mac se repitió el recorrido con **FaceTime HD Camera y OBS Virtual Camera**. Se guardaron y decodificaron dos vídeos 1080p de 394 fotogramas; la interna aporta imagen y la virtual recibe el programa azul sintético de OBS. Pasaron composición, reproducción, cambio de cámara, vuelta al directo, reproducción desde biblioteca y ausencia de reaparición después de detener. Se probó el código actual del puente con OBS real, no la interfaz de Live instalada. Esto no equivale a dos cámaras físicas ni a OCR de un marcador real.

La colección, escena y selectores originales CAMARA_1/Browser 2 están restaurados. Búfer y cámara virtual quedaron detenidos y OBS se cerró, como estaba al inicio. No quedan los cuatro clips temporales de prueba ni imágenes privadas en las evidencias; se conservan solo métricas. Evidencias: `native-replay-validation.json` y `camera-replay-validation.json`.

La revisión visual local sigue bloqueada: tras comunicar el usuario un cambio de permisos, el navegador volvió a rechazar el origen por un permiso guardado o política administrada. No se ha intentado eludirlo con Chrome, capturas indirectas o CDP.

[Regresiones del código final de replay](https://github.com/garcii13/SecretariatPro-Beta/actions/runs/39112856875) · [Instaladores de esa revisión](https://github.com/garcii13/SecretariatPro-Beta/actions/runs/39112885674). La revisión final f98ef98 supera 451 casos Python, 27 Node, 24 del renderer y la frontera SQL en las tres plataformas nativas. La compilación final de instaladores f98ef98 también está **completada y correcta en las tres plataformas**, con Live y Manager. El commit posterior `0a391d4` solo añade la reparación SQL de propietario y sus casos de seguridad: también pasa su CI en las tres plataformas. Las evidencias completas están en `native-ci-validation.json`. No se han publicado releases ni firmado una aceptación visual/hardware inexistente.

## Recuperación de cuenta y pendientes externos

Con autorización del usuario se solicitó **un único correo de recuperación** para una cuenta existente, usando el mismo redirect que el portal: `https://secretariatproapp.com/cuenta?type=recovery`. La API real responde HTTP 200. La dirección de correo y cualquier token quedan fuera de las evidencias y de Git. El usuario confirmó la recepción y apertura del enlace con sesión iniciada, pero también un aviso genérico de error. No ha confirmado un cambio de contraseña y no se ha cambiado ninguna desde las herramientas. El bundle de cuenta desplegado coincide byte a byte con el compilado anterior: no era simplemente un push pendiente. Los logs de la web muestran un rechazo HTTP 401/PGRST303 en la aceptación de invitaciones y peticiones posteriores correctas. Se prepara una corrección del portal con recuperación separada de invitaciones, renovación de JWT y un solo reintento, errores acotados a organizaciones y protección frente a respuestas tardías. Su publicación en Netlify y comprobación final con el usuario siguen pendientes. `recovery-validation.json` distingue solicitud aceptada de entrega confirmada.

Quedan pendientes la revisión visual por el bloqueo guardado del navegador, OCR con un marcador real y captura física a DPI alto, concurrencia efectiva de publicación y restauración de una copia en un entorno separado. La protección contra contraseñas filtradas continúa desactivada. El control de publicación conserva esos límites; no se han marcado pruebas pendientes como aprobadas.
