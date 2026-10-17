# Live 1.0.0-beta.9 para Windows x64

Esta versión corrige el inicio del OCR cuando la captura funciona pero no
aparecen lecturas. El worker incluye los metadatos de PaddleX `ocr-core` y el
reconocedor base `en_PP-OCRv4_mobile_rec`, además de los dos especialistas
SP-OCR 0.7 y SP-SCORE 0.2. No necesita descargar modelos al iniciar el OCR.

El diagnóstico del ejecutable comprueba una inferencia real de `12:34`;
importar las librerías y cargar los especialistas no bastaba para detectar
este fallo. La prueba de instaladores en Windows exige ahora esa inferencia.

## Compilación de esta release

Desde Windows x64 con Python 3.12, Inno Setup 6 y el ZIP de modelos de
`ocr-models-v0.7-v0.2`:

```powershell
$env:PYTHONUTF8 = '1'
python -m pip install -r requirements.txt -r requirements-test.txt
python packaging/unpack_models.py secretariatpro-ocr-models-v0.7-v0.2.zip
python packaging/prepare_windows_ocr.py
python -m unittest discover -s tests
python -m PyInstaller --noconfirm --clean SecretariatPro_App.spec
python -m PyInstaller --noconfirm --clean SecretariatPro_OCR.spec
python packaging/check_worker.py
./packaging/windows-prerequisites.ps1
python packaging/assemble.py --product Live --version 1.0.0-beta.9
```

Se puede indicar una instalación alternativa de Inno Setup con `--compiler`.
El instalador y su SHA-256 se guardan en `release/`. Esta publicación contiene
solo Live para Windows; parte de la base Windows de beta.6.

`packaging/smoke-windows.ps1` instala y desinstala los productos: ejecutarlo
únicamente en un runner desechable, como indica su cabecera.
