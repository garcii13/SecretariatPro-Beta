#!/bin/zsh
cd "$(dirname "$0")"
echo "Iniciando SecretariatPro Manager en modo diagnostico..."
python3.12 run_manager.py --debug
status=$?
if [ $status -ne 0 ]; then
  echo
  echo "El Manager no pudo iniciar. Copia el error mostrado en esta ventana."
fi
read -n 1 -s -r -p "Pulsa una tecla para cerrar..."
