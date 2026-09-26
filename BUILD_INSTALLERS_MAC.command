#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then ./PREPARAR_MAC_BETA.command; fi
.venv/bin/python -m pip install -r requirements.txt -r requirements-test.txt -c constraints-macos.txt
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m PyInstaller --noconfirm --clean SecretariatPro_App.spec
.venv/bin/python -m PyInstaller --noconfirm --clean SecretariatPro_Manager.spec
.venv/bin/python -m PyInstaller --noconfirm --clean SecretariatPro_OCR.spec
.venv/bin/python packaging/assemble.py
echo "Instaladores creados en la carpeta release."
