@echo off
setlocal
title VoiceFlow-Win Launcher

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Entorno virtual no encontrado en .venv\Scripts\python.exe
    pause
    exit /b 1
)

echo ======================================================
echo    Iniciando VoiceFlow-Win v3.4.1
echo ======================================================
echo.
echo * Abriendo ventana de configuracion en pantalla...
echo * Registrando atajo: Ctrl + Alt + Space
echo * Icono de microfono azul en la bandeja (^ junto al reloj)
echo.

start "" ".venv\Scripts\pythonw.exe" -m app.main
timeout /t 2 >nul
exit /b 0
