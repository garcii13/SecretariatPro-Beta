# Auditoría del ecosistema SecretariatPro

Fecha: 18 de octubre de 2026 · Revisión de código, pruebas locales y metadatos remotos.

**Dictamen: la base funcional tiene buena cobertura automática, pero la beta 11 actual todavía no está preparada para distribuirse.** Hay un fallo reproducible de orden de respuestas en emisión, una carencia reproducible de validación del origen del WebSocket, dependencias con avisos y validación instalada/Windows/OBS pendiente.

No se ha modificado código de aplicación, publicado instaladores, enviado correos, ejecutado migraciones ni accedido a datos de clientes. Se han generado este informe y sus evidencias. Las compilaciones de comprobación solo han escrito resultados locales ignorados por Git. El análisis de dependencias Python se hizo con una herramienta instalada en un entorno temporal separado.

## Alcance y límites

Se revisaron Live, Manager, adaptación de gráficos y renderer Svelte, BroadcastFlow, OCR/captura, tablet, puente de replay/OBS, almacenamiento local, cliente Supabase, SQL y función de invitaciones, portal Astro, CI y publicación. Se inspeccionó también el OCR Lab interno en su carpeta independiente.

No se ha auditado el estado desplegado de RLS, triggers, funciones, SMTP o copias de seguridad de Supabase. Tampoco se ha comprobado una sesión real de cámara/OBS, el rendimiento de fotogramas, una instalación limpia o Windows nativo. La revisión visual sigue pendiente por el bloqueo persistente del origen local en el navegador integrado; no se ha utilizado una vía alternativa para eludirlo.

Las antiguas carpetas de Descargas `secretariatpro-astro-v4` y `SecretariatPro_Multicam_Replay-4` ya no existen en las rutas proporcionadas. La web se revisó desde `website/`; del plugin nativo se revisaron su contrato y puente en Live, no su código C++ ni sus binarios instalados.

## Estado real del ecosistema

| Componente | Estado comprobado | Límite de la comprobación |
| --- | --- | --- |
| Live local | Base unificada Mac beta 8 + Windows beta 10, con correcciones OCR posteriores; código beta 11 | No equivale a un instalador publicado |
| Manager | Roles, ámbitos, importaciones, rosters e identidad con cobertura automática | Función de invitación presenta el riesgo A03; no se verificó la BD desplegada |
| Gráficos | Svelte + TypeScript + SVG + GSAP, assets locales, adaptador compartido y respaldo legacy | Migración parcial; composición visual y fluidez real sin medir |
| Goles | BroadcastFlow centraliza replay/directo, intro, transición, duración y cancelación | El transporte puede reaplicar estados antiguos: A01 |
| Powerplays | Cobertura de ambos equipos, varias sanciones, reloj detenido, FIFO, recuperación y EMPTY NET | Hardware y emisión prolongada pendientes |
| Banderas | Pruebas de ancho común, límite 1,5×altura, proporción y conservación de escudos | Composición en OBS pendiente |
| OCR | SP-OCR 0.7 / SP-SCORE 0.2, modelos con hashes; Mac mantiene Paddle 2.6.2/OCR 2.7.3 | Riesgo de dependencias A04; no se ha vuelto a medir precisión con vídeo real |
| OBS / replay | Biblioteca, plantillas, exportación, confirmaciones y cancelación con pruebas | Falta auditar el plugin nativo y una sesión multicámara real |
| Tablet | Emparejamiento de un uso, expiración, revocación y lista cerrada de acciones | Tráfico LAN HTTP y prueba física pendientes |
| Web / cuenta | Astro compila 16 páginas; `/cuenta` y `/en/account` responden HTTP 200 tras redirección HTTPS | No se probó login, recuperación ni invitación real |
| OCR Lab | Fuente interna 1.0.6, servicio loopback y credenciales fuera del bundle | Sin Git local; pipeline distinto del modelo híbrido distribuido |
| Distribución | Releases independientes y checksums en GitHub | La nueva base unificada no tiene instaladores validados |

Repositorio examinado: `.publish-repo`, rama `feature/unified-international-goals`, HEAD `499d0ccc38112370fea2eca6d51da3f06666734a`, con cambios locales posteriores. Al inicio se compararon **335 archivos** versionados o pendientes de añadir: ninguno faltaba ni difería entre checkout y copia ejecutable. No había archivos privados de runtime entre las rutas versionadas examinadas. Esto no es un escaneo exhaustivo de secretos del historial Git.

Releases verificados mediante API de GitHub:

- [Live Windows beta 10](https://github.com/garcii13/SecretariatPro-Beta/releases/tag/live-v1.0.0-beta.10): commit `3d4c10ae4f2be62633120cbd8938015db0fef1a5`, instalador Windows y checksum.
- [Live Mac beta 8](https://github.com/garcii13/SecretariatPro-Beta/releases/tag/live-v1.0.0-beta.8): commit `4ac82def73a5be1d7510d210b7c2061da8fd3ac5`, DMG ARM64 e Intel y checksums.
- Último Manager listado: `manager-v1.0.0-beta.6`, publicado el 29 de septiembre.
- No había release beta 11 en la lista consultada. El último run de instaladores listado para el commit Mac beta 8 estaba fallido; existen assets publicados posteriores, de modo que ese run aislado no demuestra que esos assets estén defectuosos. Tampoco valida el código local actual.
- El remoto `installers` es accesible. La consulta de Actions al remoto `origin` respondió 404 con la cuenta actual: puede ser un problema de acceso o ruta; no demuestra que el repositorio haya sido eliminado.

## Hallazgos prioritarios

P1: resolver o cerrar con evidencia antes de distribuir. P2: deuda o control que conviene abordar en la siguiente estabilización. La prioridad expresa impacto en este producto; no sustituye la severidad CVSS de una dependencia.

### A01 · P1 · Una respuesta antigua puede volver a mostrar un gráfico ocultado

**Confirmado mediante reproducción sobre el bundle compilado.**

`script.js:1535` inicia peticiones cada 250 ms sin esperar la anterior, identificar una revisión ni descartar respuestas obsoletas. La carga inicial utiliza el mismo mecanismo sin una barrera de orden. Esto afecta también al renderer Svelte porque incorpora ese adaptador.

Se retuvieron dos respuestas sintéticas y se entregó primero la nueva con el marcador oculto, y después la anterior con el marcador visible:

```text
Respuesta nueva: NUEVO scoreboard-wrapper hidden
Respuesta anterior retrasada: ANTERIOR scoreboard-wrapper visible
```

Consecuencia: bajo retrasos de red o carga del backend pueden retroceder nombres, estado de paneles y datos. La generación de BroadcastFlow evita tareas antiguas en el servidor, pero no impide que el cliente reaplique una instantánea antigua ya enviada.

Además, en `script.js:1547` un error de lectura TXT se convierte en cadena vacía y puede borrar el resultado/reloj; no se comprueba `response.ok` en esas tres lecturas. Esta segunda observación procede de inspección de código.

**Cierre propuesto:** secuencia/revisión monotónica y contexto de partido en las instantáneas; descartar respuestas antiguas y conservar el último TXT válido ante errores. Probar respuestas invertidas, carga inicial tardía, errores HTTP, cambio de partido y cancelación de gol. Después evaluar un único transporte de instantáneas coherentes.

### A02 · P1 · El WebSocket confía en loopback sin validar el origen

**Confirmado en TestClient, con estado sintético y acceso de producción simulado.**

En `secretariat_api/main.py:541`, un cliente loopback con `Origin: https://audit.invalid` fue aceptado y recibió la instantánea sintética. No hay token propio del cliente ni comprobación del origen en ese endpoint. La protección de origen HTTP de `subscription_gate` solo se aplica a clientes remotos, y no cubre WebSockets. El Manager tampoco rechaza un `Host` ajeno (`manager_api/main.py:204`); la lectura sintética devolvió 200.

Consecuencia: falta una barrera de aplicación frente a páginas ajenas que intenten conectar al servicio local. La viabilidad desde un navegador concreto depende de sus protecciones de acceso a red local; aquí se ha demostrado la aceptación del servidor, no una explotación completa en un navegador. El caso de Host requiere además condiciones como DNS rebinding; no se ha reproducido ese ataque.

**Cierre propuesto:** validar Host y Origin para HTTP y WS, con los orígenes locales/OBS necesarios y el acceso tablet previsto; añadir credencial de sesión local para operaciones y conexiones sensibles. Probar rechazo de orígenes ajenos y compatibilidad con pywebview, OBS y tablet. No basta con configurar CORS.

### A03 · P1 · La invitación puede sobrescribir una membresía ya existente

**Confirmado por inspección del código; efecto en la base desplegada no comprobado.**

`supabase/functions/invite-member/index.ts:80` ejecuta con el cliente administrador un `upsert` por `workspace_id,user_id` que escribe el rol solicitado y el estado. Antes no consulta la membresía existente ni protege al propietario o una suspensión. La función admite llamadas de `competition_manager`.

La edición normal sí impide modificar al propietario (`supabase_client.py:1055`). Esa protección no aparece en la ruta de invitación. Reinvitar a un miembro puede cambiar su rol o reactivarlo; el resultado real puede estar condicionado por triggers desplegados que no se han inspeccionado.

**Cierre propuesto:** tratar una invitación existente como operación idempotente, proteger propietario y suspensión dentro de la función/BD y separar cambios de permisos de las invitaciones. Validar con propietario, gestor y realizador en un entorno de pruebas; no modificar cuentas reales para reproducirlo.

### A04 · P1 · Ocho paquetes Python instalados tienen avisos conocidos

**Confirmado con pip-audit sobre las 144 versiones instaladas en la venv local.** Se obtuvieron 27 registros en ocho paquetes; hay duplicados e identificadores que describen el mismo problema, por lo que no deben anunciarse como 27 fallos distintos del producto.

| Paquete instalado | Registros | Correcciones indicadas por la herramienta |
| --- | ---: | --- |
| imgaug 0.4.0 | 2 | Sin versión correctora indicada |
| multidict 6.7.1 | 1 | 6.9.1 |
| opencv-contrib-python 4.6.0.66 | 2 | 4.8.1.78 |
| opencv-python 4.6.0.66 | 2 | 4.8.1.78 |
| paddlepaddle 2.6.2 | 2 | 3.0.0b0 según catálogo; no es una recomendación de migración |
| PyJWT 2.13.0 | 14 | Varios a 2.14.0 / 2.15.0; uno sin corrección indicada |
| urllib3 2.7.0 | 3 | 2.8.0 |
| Werkzeug 3.1.8 | 1 | 3.1.9 |

No se ha demostrado que todos esos caminos vulnerables sean alcanzables desde SecretariatPro. El resultado describe la venv de este Mac; no se debe extrapolar a las dependencias resueltas de los instaladores publicados ni a Windows.

El bloqueo relevante es estructural: `constraints-macos.txt:1` y `requirements.txt` conservan OpenCV 4.6/Paddle antiguo por compatibilidad OCR. Una actualización indiscriminada puede romper captura o inferencia. Los dos proveedores de `cv2` están instalados por ese stack heredado.

**Cierre propuesto:** clasificar exposición real por aviso, actualizar primero dependencias auxiliares compatibles y preparar una migración aislada del runtime OCR Mac. Medir precisión, latencia, captura, perspectiva, confianza y consenso del reloj con los mismos modelos/dataset antes de sustituirlo. Auditar también las versiones resueltas del instalador Windows y cada arquitectura Mac.

### A05 · P1 · La auditoría de dependencias web ya no está limpia

**Confirmado con npm audit y npm ls.** El lockfile tiene seis paquetes afectados: cinco de severidad alta y uno moderado. `npm audit --audit-level=high`, usado por `.github/workflows/website.yml`, falla con este estado aunque la compilación Astro termine bien.

| Paquete resuelto | Severidad de npm |
| --- | --- |
| devalue 5.9.2 | Alta |
| http-cache-semantics 4.2.0 | Alta |
| sharp 0.35.4 | Alta |
| smol-toml 1.8.0 | Moderada |
| source-map-js 1.2.1 | Alta |
| undici 8.10.0 | Alta |

La web es estática: la presencia de un paquete vulnerable de Node no demuestra que el visitante pueda explotar el sitio publicado. Parte de la exposición se concentra en construcción y herramientas. El [aviso del mantenedor de Sharp](https://github.com/lovell/sharp/security/advisories/GHSA-wq5f-xc86-pv6w) identifica la corrección desde 0.35.5 y condiciones concretas para librsvg/Linux; no se ha demostrado explotación en este proyecto.

**Cierre propuesto:** actualizar el lockfile dentro de versiones compatibles, instalar de cero, repetir auditoría/compilación y probar portal ES/EN. El renderer nuevo tiene **cero avisos npm** en la consulta realizada. Añadir su auditoría al CI, que hoy usa `--no-audit` y no ejecuta una auditoría posterior.

### A06 · P1 · Falta aceptación del producto que se pretende distribuir

**Brecha de validación, no fallo de hardware demostrado.** La nueva presentación no tiene comprobación visual del navegador/OBS, pruebas nativas Windows, instalación limpia de esta revisión ni sesión multicámara real. Los tests DOM no calculan geometría real, composición o FPS.

Esto afecta especialmente al descanso responsive con nombres completos, escalas de Manager, salida superior del marcador con varias sanciones y continuidad GOL → goleador. Los tests protegen contratos y cancelaciones, pero no acreditan el acabado final.

**Cierre propuesto:** ejecutar la matriz de `BASELINE_COMPATIBILITY.md` y `BETA_VALIDATION.md` sobre un commit congelado, con evidencias de Windows x64, Mac ARM64 e Intel si se distribuyen las tres arquitecturas. Registrar instalador/hash, prueba visual, cámara/ventana OCR, doble cámara, powerplays, pérdida de conexión, exportación y cierre de partido.

### A07 · P2 · La versión actual depende de archivos aún sin registrar

**Confirmado por git status.** Hay 11 archivos versionados modificados y fuentes/assets/tests nuevos sin seguimiento, incluyendo `broadcast_renderer/`, `overlay_studio/`, `overlay-studio.html` y sus cambios de rutas/packaging.

La sincronización de ambas copias es correcta hoy, pero un clon de HEAD no reproduce la presentación actual. Los dos remotos y el 404 del remoto origin añaden incertidumbre operativa sobre cuál es la fuente recuperable.

**Cierre propuesto:** revisar y registrar el conjunto completo, fijar el remoto canónico y validar un clon limpio con hashes de assets y CI. Mantener fuera runtime y credenciales. No se ha hecho commit ni push durante esta auditoría.

### A08 · P2 · La migración visual sigue apoyada en el adaptador y CSS históricos

**Deuda comprobada, no razón para reescribir todo de golpe.** Svelte monta componentes, GSAP aporta movimiento y el adaptador `script.js` conserva la lógica DOM. Siguen activos 1.610 líneas de adaptador y 5.003 de CSS base, además de los nuevos estilos y reglas prioritarias. Live y Manager contienen 4.467 y 2.019 líneas de JavaScript respectivamente.

El overlay inicia cuatro lecturas cada 250 ms: aproximadamente 16 peticiones/s por instancia, más ajustes cada 1,2 s. Con varias fuentes/previews el trabajo se multiplica. No se ha medido saturación ni pérdida de FPS; el defecto probado es A01, no una afirmación de rendimiento insuficiente.

**Cierre propuesto:** tras estabilizar, separar transporte, estado, presentación y tipado del contrato. Migrar panel por panel conservando las pruebas de equivalencia, colores y fuentes de Manager, powerplays y BroadcastFlow. Medir en OBS antes de optimizar efectos o elegir otra tecnología. No hace falta otro cambio de lenguaje para corregir los riesgos actuales.

### A09 · P2 · El OCR Lab y el modelo distribuido necesitan una trazabilidad común

**Confirmado por inspección.** El Lab no es un repositorio Git en la carpeta examinada y no se encontró suite propia en su árbol de fuentes. Su documentación/pipeline de aprobación genera modelos Paddle en `models/ocr_active`; Live distribuye los especialistas híbridos joblib declarados en `models/MANIFEST_SP_OCR.json`. Son circuitos distintos, no una prueba de que el OCR distribuido esté mal entrenado.

`training/prepare_dataset.py:47` reparte filas aleatoriamente y no agrupa por partido/cámara/pabellón ni deduplica por contenido. `training/approve_model.py:19` compara porcentajes pero no exige igualdad de dataset, denominadores ni hashes de benchmark. Puede aceptarse una mejora aparente con validación contaminada o no comparable. No se analizaron datasets reales para afirmar que eso ya haya ocurrido.

**Cierre propuesto:** versionar fuentes del Lab sin secretos/muestras privadas; identificar el pipeline que produjo cada especialista activo; añadir split por sesión/partido, deduplicación y dataset congelado. Exigir hashes y tamaños comparables al aprobar. Preservar la separación de la service role respecto al producto. El servidor del Lab es loopback, pero también conviene aplicar validación de Host/Origin y sesión local por sus operaciones administrativas.

### A10 · P2 · Falta consolidar la evidencia de seguridad y operación cloud

El código SQL incluye RLS, `security_invoker`, permisos explícitos y publicación transaccional con bloqueo por ámbito. La función de invitación valida JWT y rol antes de crear el cliente administrador. Son controles positivos, pero la existencia del archivo SQL no prueba su despliegue.

No se verificaron políticas de buckets, funciones efectivas, migraciones aplicadas, recuperación de copias, SMTP o concurrencia real entre gestores. El informe anterior `BETA_AUDIT.md` contiene resultados de septiembre que ya no describen las dependencias actuales.

**Cierre propuesto:** inventario de migraciones/versiones desplegadas y pruebas con dos workspaces y los tres roles. Registrar rechazo de acceso cruzado, publicación concurrente, invitación repetida, suspensión, recuperación de cuenta y restauración. Separar la disponibilidad HTTP del portal, que sí se comprobó, del funcionamiento de sus operaciones autenticadas.

## Verificación ejecutada en esta auditoría

| Comprobación | Resultado |
| --- | --- |
| `packaging/run_regressions.py` | 440 casos registrados; 438 correctos y 2 Win32 omitidos |
| Suite Node OCR/presentación/Manager/movimiento | 26 correctos |
| Suite del bundle Svelte | 21 correctos |
| Svelte/TypeScript | 0 errores, 0 avisos |
| Sintaxis de script.js, overlay_motion.js, webapp/app.js, manager_app/app.js | Correcta |
| `pip check` | Sin incompatibilidades declaradas |
| `npm audit` renderer | 0 avisos |
| `npm audit` web | 6 paquetes afectados; auditoría con umbral alto fallida |
| `pip-audit` venv local | 27 registros en 8 paquetes; requiere triage de alcance |
| `npm run build --prefix website` | 16 páginas; correcto |
| Paridad copia ejecutable / checkout | 335 archivos iguales al inicio |
| Hashes fuentes/assets Studio | Correctos en tests de assets |
| `git diff --check` | Correcto |
| Reordenación de respuestas de estado | Fallo A01 reproducido con datos sintéticos |
| Origin/Host no confiables | A02 reproducido en servidor con estado sintético |
| HTTPS portal ES/EN | 200 tras redirección a barra final; HSTS presente |

`pip check` solo comprueba compatibilidad declarada y no sustituye una auditoría de seguridad. Las suites no equivalen a cobertura exhaustiva de todas las funcionalidades ni garantizan ausencia de errores. Se observó una advertencia de deprecación de TestClient/httpx: mantenimiento menor, sin fallos de pruebas.

No se recompiló el renderer para esta auditoría: se comprobó el bundle existente, su manifiesto y sus tests. Tampoco se generaron nuevos instaladores.

## Orden de trabajo recomendado

1. Corregir A01 y A02 con pruebas de regresión concretas; cerrar la protección de membresías A03.
2. Resolver la auditoría web y clasificar/mitigar los avisos Python preservando el runtime OCR validado.
3. Registrar una revisión completa y reproducible; comprobar clon limpio y CI de las plataformas.
4. Ejecutar revisión visual y sesión instalada con OBS/cámara/multicámara/powerplays sobre esa revisión.
5. Verificar aislamiento y operación cloud en entorno de pruebas; después preparar instaladores de beta 11.
6. Abordar por etapas la deuda del adaptador/CSS y la trazabilidad del Lab, sin sustituir funcionalidades ya cubiertas.

Evidencias resumidas, registros de pruebas y sondas reproducibles: [carpeta de auditoría](audits/2026-10-18/). Las sondas usan exclusivamente datos sintéticos y mocks; no se conectan a una aplicación en directo ni a Supabase.
