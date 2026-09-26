#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  ./PREPARAR_MAC_BETA.command
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m PyInstaller SecretariatPro_App.spec --noconfirm --clean
.venv/bin/python -m PyInstaller SecretariatPro_OCR.spec --noconfirm --clean
cp dist/SecretariatPro_OCR "dist/SecretariatPro Live.app/Contents/MacOS/SecretariatPro_OCR"
codesign --force --deep --sign - "dist/SecretariatPro Live.app"
echo "Aplicación creada en dist/SecretariatPro Live.app"
