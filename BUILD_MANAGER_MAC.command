#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
python3 -m PyInstaller SecretariatPro_Manager.spec --noconfirm --clean
echo "Aplicación creada en dist/SecretariatPro Manager.app"
