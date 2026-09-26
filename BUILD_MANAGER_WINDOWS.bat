@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m PyInstaller SecretariatPro_Manager.spec --noconfirm --clean
if errorlevel 1 (
  echo.
  echo ERROR al construir SecretariatPro Manager.
  pause
  exit /b 1
)
echo.
echo Aplicacion creada en "dist\SecretariatPro Manager"
pause
