@echo off
cd /d "%~dp0"
echo Iniciando SecretariatPro Manager en modo diagnostico...
py -3.12 run_manager.py --debug
if errorlevel 1 (
  echo.
  echo El Manager no pudo iniciar. Copia el error mostrado en esta ventana.
)
pause
