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
echo * Cerrando instancias previas de VoiceFlow...
powershell -NoProfile -Command "Get-Process python*, pythonw* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*VoiceFlow-Win*' } | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1

echo * Abriendo aplicacion en pantalla...
echo * Atajo de Dictado: Win + Space
echo * Atajo de Reescritura: Ctrl + Shift + Space
echo.

start "" ".venv\Scripts\pythonw.exe" -m app.main
exit /b 0
