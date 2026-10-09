@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python packaging\prepare_windows_ocr.py
if errorlevel 1 exit /b 1
python -m PyInstaller SecretariatPro_App.spec --noconfirm --clean
if errorlevel 1 (
  echo.
  echo ERROR al construir SecretariatPro.
  pause
  exit /b 1
)
echo.
python -m PyInstaller SecretariatPro_OCR.spec --noconfirm --clean
if errorlevel 1 exit /b 1
python packaging\check_worker.py
if errorlevel 1 exit /b 1
copy /Y "dist\SecretariatPro_OCR.exe" "dist\SecretariatPro Live\SecretariatPro_OCR.exe"
if errorlevel 1 exit /b 1
echo Aplicacion creada en "dist\SecretariatPro Live\SecretariatPro Live.exe"
pause
