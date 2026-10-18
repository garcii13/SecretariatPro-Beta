# Evidencias de auditoría — 18/10/2026

Resultados locales del estado descrito en `../../AUDITORIA_ECOSISTEMA_2026-10-18.md`.
No son una certificación de los instaladores publicados ni del servicio cloud.
Los avisos de dependencias son una consulta puntual al catálogo, no prueba de explotación.

Desde la copia ejecutable, reproducir con:

```sh
node docs/audits/2026-10-18/probe_transport.mjs
.venv/bin/python docs/audits/2026-10-18/probe_local_origin.py
```

Las sondas imprimen el comportamiento observado; no deben interpretarse como tests que pasan.
La de transporte necesita `broadcast_renderer/node_modules`, presente en la copia ejecutable.
`evidence.json` recoge versiones y resultados. Los `.log` se excluyen por la regla global de Git,
pero se incluyen en esta carpeta local de entrega; el resumen JSON conserva los resultados principales.


## Estado posterior

El informe inicial conserva la fotografía anterior. `fixes/` contiene la
comparación OCR y las auditorías posteriores. Las sondas originales reflejan el
fallo previo y pueden dejar de completarse al rechazarse las conexiones/peticiones;
las regresiones actuales (`transport.test.mjs`, `test_local_access.py` y las
pruebas PostgreSQL) verifican expresamente su corrección.
