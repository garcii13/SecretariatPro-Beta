#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ -x ".venv/bin/python" ]; then
  exec .venv/bin/python run_app.py
fi
echo "Aviso: no existe .venv. Ejecuta PREPARAR_MAC_BETA.command para usar el entorno OCR estable."
exec python3 run_app.py
