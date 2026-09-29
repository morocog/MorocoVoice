@echo off
chcp 65001 >nul
REM Python no usa el code page de la consola para las tuberias: sin esto los
REM acentos del informe se corrompen al redirigir la salida a un archivo.
set "PYTHONIOENCODING=utf-8"
title MorocoVoice - Diagnostico del sistema
cd /d "%~dp0"

echo ============================================================
echo    MOROCOVOICE - DIAGNOSTICO DEL SISTEMA
echo ============================================================
echo.
echo  Comprueba audio, hardware y, sobre todo, el ENTORNO DE
echo  SEGURIDAD del que dependen el icono de bandeja y los
echo  atajos globales.
echo.
echo  Durante la prueba se envia una pulsacion inocua de SHIFT
echo  para verificar que el teclado se captura de verdad.
echo  No escribe ningun caracter ni dispara ningun atajo.
echo.
pause

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] No existe el entorno virtual .venv
  echo         Ejecuta primero run.bat para instalarlo.
  echo.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" verify_install.py
set "RC=%ERRORLEVEL%"

echo.
echo ============================================================
if "%RC%"=="0" (
  echo  RESULTADO: entorno 100%% correcto.
  echo  Si aun asi el icono no aparece junto al reloj, mira en el
  echo  cajon de desbordamiento ^^ y arrastralo hacia fuera.
) else if "%RC%"=="2" (
  echo  RESULTADO: operativo, con advertencias menores.
  echo  Revisa las ADVERTENCIAS de arriba ^(suelen ser GPU o rutas
  echo  largas^): no impiden dictar.
) else (
  echo  RESULTADO: HAY PROBLEMAS que impediran el funcionamiento.
  echo  Copia este informe completo y consulta docs\TROUBLESHOOTING.md
)
echo ============================================================
echo.
pause
exit /b %RC%
