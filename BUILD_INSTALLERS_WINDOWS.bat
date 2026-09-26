@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt -r requirements-test.txt
if errorlevel 1 goto failure
python -m unittest discover -s tests
if errorlevel 1 goto failure
python -m PyInstaller --noconfirm --clean SecretariatPro_App.spec
if errorlevel 1 goto failure
python -m PyInstaller --noconfirm --clean SecretariatPro_Manager.spec
if errorlevel 1 goto failure
python -m PyInstaller --noconfirm --clean SecretariatPro_OCR.spec
if errorlevel 1 goto failure
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\windows-prerequisites.ps1
if errorlevel 1 goto failure
python packaging\assemble.py
if errorlevel 1 goto failure
echo Instaladores creados en la carpeta release.
pause
exit /b 0
:failure
echo ERROR: no se han completado los instaladores. Revisa el mensaje anterior.
pause
exit /b 1
