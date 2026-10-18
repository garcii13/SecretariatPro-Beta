# Broadcast Studio: Svelte, TypeScript, SVG y GSAP

La nueva presentación local se sirve en la misma URL de OBS: `/overlay.html`.
`/overlay-studio.html` abre la misma presentación. La referencia anterior permanece
en `/overlay.html?renderer=legacy`; ambos aceptan `cue` para las vistas de la cola.
No se han generado ni publicado instaladores.

## Arquitectura y conservación

- `broadcast_renderer/src/components/`: marcador y estados/powerplays, GOL,
  perfil, previa, descanso, alineaciones de ambos equipos, máximos puntuadores,
  clasificación y tanda de penaltis. Todos los IDs y los puntos de personalización
  de la presentación de referencia permanecen disponibles.
- `broadcast_renderer/src/motion.ts`: entradas, salidas, detalles, cambios de
  resultado y sanciones mediante GSAP. Cada raíz tiene una generación para
  invalidar trabajo interrumpido. Los estados de sanción usan tokens propios.
- `GoalArtwork.svelte`: trazos, eco tipográfico, diagonales y luz vectorial.
  La línea de tiempo sigue la fase y el tiempo transcurrido de BroadcastFlow;
  no manda órdenes al partido ni decide cuándo volver de replay a directo.
- `script.js` es el adaptador de datos compartido con la referencia. Mantiene
  polling JSON/TXT, idiomas, identidad, publicación de Manager, rosters,
  formación por deporte, estadísticas y listas. Arranca una sola vez cuando
  los componentes ya están montados. Las listas son islas DOM del adaptador;
  esta entrega no reescribe esa lógica como estado reactivo Svelte duplicado.
- `styles.css` conserva la geometría compatible, incluyendo formación, plantilla
  dinámica, posición y dimensiones de las banderas. `src/studio.css` define el
  nuevo acabado; evita ejecutar los keyframes antiguos del GOL al mismo tiempo.
  Se conserva la hoja de geometría histórica para evitar alterar dimensiones
  funcionales durante esta migración.

Los colores, fuentes y escalas siguen llegando de Manager mediante las mismas
variables y selectores. La miniatura de Manager mantiene sus controles y aproxima
el acabado nuevo; la presentación real es la que sirve Live a OBS.

Se conservan el motor Python y sus funciones: OCR/modelos/captura/perspectiva/
confianza/reloj, modo manual, periodos, cuentas/competiciones, publicación,
importaciones, colas, OBS, multicámara/replay, plantillas, biblioteca y exportación.
No se migran datos privados, credenciales ni ajustes de ejecución al repositorio.

## Powerplays y banderas

Los powerplays siguen recibiendo `remaining_seconds` desde Python. El navegador
no descuenta tiempo por su cuenta. Se conservan las sanciones simultáneas de
ambos equipos, dorsales, aviso de últimos segundos, orden y EMPTY NET.
Si cambia la cola durante una salida, su callback usa el orden más reciente.
Una sanción que reaparece cancela la salida y su callback no puede borrarla.

Las banderas originales se usan sin recorte ni deformación, con ancho visible
común, máximo de 1,5 veces la altura y reducción conjunta si lo requiere alguna
proporción. Se mantiene la altura del marcador y los escudos guardados aparte.

## GOL

Replay/vuelta confirmada a directo o demora configurada → GOAL_INTRO (2,2 s) →
GOAL_REVEAL (640 ms) → GOAL_BOTTOM (duración configurada completa) → ocultación →
restauración del marcador. Las fases pertenecen a BroadcastFlow.

El texto del GOL, trazos y luz entran coordinados. La cortina de color se retira
sobre los nombres durante la transición. Se sincronizan clientes que llegan tarde
mediante el tiempo de la fase. La cancelación congela la cortina durante la salida;
una generación nueva reconstruye la animación. Se respeta movimiento reducido.

## Compilación e instalación

```sh
npm ci --prefix broadcast_renderer --no-fund --no-audit
npm run verify --prefix broadcast_renderer
python packaging/run_regressions.py
node --check script.js
node --check overlay_motion.js
node --check webapp/app.js
node --check manager_app/app.js
node --test tests/ocr_preview.test.cjs tests/overlay_presentation.test.cjs tests/manager_identity.test.cjs tests/overlay_motion.test.cjs
```

Node se usa para desarrollar/compilar; el usuario instalado no lo necesita.
`overlay_studio/` contiene JS/CSS compilados y un manifiesto de hashes de fuentes
y artefactos. Se empaqueta en PyInstaller junto a la página de entrada. No hay
CDN ni servidor Node. El adaptador está incluido en el bundle y no se carga dos
veces. Si el bundle falla o falta, el arranque conserva la URL/cola y vuelve a la
referencia. Las pruebas Python detectan un bundle desactualizado.

Ambos workflows de Mac/Windows compilan, comprueban TypeScript/Svelte y ejecutan
las pruebas de equivalencia y movimiento antes de preparar instaladores.

## Validación y límites

Pruebas DOM sobre el bundle compilado y la referencia, con los mismos datos:
IDs, contenido, seis idiomas, floorball/balonmano, formación/convocados/entrenador,
clasificación, máximos puntuadores, eventos, penaltis, marcador TXT/manual,
instantánea del resultado del GOL, personalización/publicación, banderas,
previsualización de cola y ocultación de todos los paneles.

Se prueban interrupciones, inversión desde la posición actual, cancelación antes
del primer frame, reducción de movimiento, fases de GOL y powerplays (reloj
pausado, ambos equipos, cola cambiante durante una salida y sanción recuperada).
Estas pruebas DOM no miden composición visual ni rendimiento de emisión.

La revisión visual sigue pendiente: el origen local permanecía bloqueado por
el permiso persistente del navegador integrado, pese a la autorización del usuario.
No se ha intentado otra vía para eludirlo. Antes de distribuir: revisión visual,
pruebas nativas Windows y sesión real con OBS/cámaras/aplicación instalada.

Resultado local de esta entrega: 438 pruebas Python sin fallos, dos Win32 omitidas;
25 pruebas JavaScript existentes y 14 nuevas sobre el bundle compilado correctas.
Svelte/TypeScript sin errores ni avisos; sintaxis de las interfaces comprobada.

## Continuidad y fluidez de los bloques

El bottom y la ficha de jugador comparten ahora una superficie pintada en su
raíz: fondo con mezcla gradual, contorno y acento continuos. Sus divisiones
internas quedan transparentes, sin sombras o bordes de tarjetas separadas. Los
colores de cuerpo y zona central siguen llegando de Manager; se publican también
en la raíz del bottom para superar los valores locales de la geometría anterior.
La miniatura de Manager refleja el fondo continuo.

Las entradas/salidas usan una curva suave de aceleración y frenado, con recorridos
más cortos. En marcador y bottoms se animan los textos y emblemas, manteniendo
fijos los fondos. Se reduce el desfase entre contenidos para que se lean como una
misma pieza. Las cancelaciones, escala y tipografía conservan sus contratos.

GOAL_REVEAL conserva la posición visible de texto, eco y trazos de GOAL_INTRO
para el mismo evento. Una generación distinta no hereda esa posición. La cortina
se controla mediante una variable dentro de una máscara CSS prioritaria, evitando
que el reset histórico de `clip-path` anule el barrido. Con movimiento reducido
se sustituye por un fundido. La duración completa del goleador y la propiedad de
BroadcastFlow sobre las fases se mantienen.

Validación de esta revisión: 438 pruebas Python sin fallos (dos Win32 omitidas),
25 JavaScript existentes y 17 del renderer; cero errores/avisos Svelte/TypeScript.
Se añaden comprobaciones del fondo inmóvil durante las entradas, continuidad
entre las fases del GOL, fundido accesible y publicación de colores en el bottom.
Los powerplays, sus colas/cancelaciones, idiomas y deportes mantienen su cobertura.
La comprobación visual y la sesión real OBS/Windows continúan pendientes.

## Marcador completo y salida estable del bottom

El marcador se desplaza como una única pieza desde fuera del borde superior y
vuelve a retirarse hacia arriba. Nombres, resultado, reloj y emblemas permanecen
visibles, sin introducción escalonada ni fundido. Los cambios de resultado se
actualizan en su sitio, sin atenuar ni desplazar los dígitos. Se mantiene la escala
publicada por Manager y la miniatura muestra la misma dirección de entrada.

La distancia se mide tras poblar el estado del frame, incluyendo reloj y colas
absolutas de powerplays/EMPTY NET, para que toda la pieza salga del lienzo incluso
con varias sanciones. Se conservan cancelación, inversión y movimiento reducido.

El bottom (y el perfil) se desvanece en su posición al salir. Si se oculta durante
la entrada, los detalles se congelan hasta quedar ocultos, sin recolocarse antes
del fundido. Una reaparición durante la salida continúa la posición conservada.
El contenido se limpia después de ocultar la raíz. Las fases y duraciones de
BroadcastFlow se mantienen.

Validación: 438 pruebas Python sin fallos, dos Win32 omitidas; 25 pruebas
JavaScript previas y 20 del renderer correctas, Svelte/TypeScript sin errores ni
avisos. Se comprueban explícitamente el texto opaco durante todo el recorrido,
la salida completa con colas, el bottom sin desplazamiento de salida y su
recuperación a mitad de animación. La revisión visual/OBS permanece pendiente.

## Dinamismo, alineación de previa y nombres completos

El recorrido del marcador mantiene todos sus textos visibles. La entrada tiene
un impulso inicial más decidido y frenado progresivo (640 ms), y la salida
acelera hacia arriba (420 ms), sin rebote ni piezas independientes. Se mantienen
la distancia completa de salida de reloj/powerplays y la salida fija del bottom.

Las tarjetas superiores de la previa y sus cajas inferiores comparten columnas
y separaciones: pabellón queda debajo del equipo local e inicio debajo del
visitante. Se elimina el padding horizontal adicional del footer. En el formato
estrecho ambas filas usan dos columnas y el logo de competición queda centrado
abajo, sin desplazar los bordes de las cajas.

El contexto conserva `team.name` como abreviatura y añade `team.full_name` desde
el nombre original de Manager. Previa y descanso usan el nombre completo; en
partidos guardados anteriores se recupera el nombre de las alineaciones y, si
falta, el nombre disponible. Los nombres pueden ocupar varias líneas, sin
elipsis. Un cambio de partido reemplaza los nombres anteriores, sin migración
de base de datos. No cambia la identidad ni el nombre corto del marcador.

Validación: 440 pruebas Python sin fallos (dos Win32 omitidas), 26 pruebas
JavaScript existentes y 21 del renderer correctas. Svelte/TypeScript sin errores
ni avisos. Se comprueban nombre completo frente a abreviatura, partidos antiguos,
cambio de nombre y de partido, idiomas, powerplays y cancelaciones. Alineación y
acabado quedan pendientes de revisión visual/OBS, además de Windows nativo antes
de distribuir instaladores.

## Ancho responsive del descanso

El descanso determina su ancho por el contenido, limitado al 94 % del viewport.
Se elimina el tope de 1180 px y se conserva ese tamaño como mínimo de referencia
cuando cabe en pantalla. Las dos columnas de equipo usan la misma fracción: su
ancho intrínseco común atiende al lado que más espacio necesita, manteniendo el
logo de competición centrado. Las tarjetas también comparten altura.

En pantallas estrechas la cabecera conserva columnas simétricas; por debajo de
640 px, la competición pasa a una fila central y los nombres ocupan una fila
completa dentro de cada equipo. Se mantienen nombres completos, sin elipsis.
No se añade ningún control ni preferencia de ancho a Manager: el ajuste es
automático al cambiar contenido, tipografía o tamaño del lienzo.

Validación automática: Svelte/TypeScript, build local, 21 pruebas del renderer,
26 JavaScript existentes y 440 Python sin fallos (dos Win32 omitidas). El acabado
y las medidas visuales siguen pendientes de comprobación real en navegador/OBS.
