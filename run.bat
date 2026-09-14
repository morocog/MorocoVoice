@echo off
setlocal enabledelayedexpansion
title MorocoVoice Launcher

cd /d "%~dp0"

echo ======================================================
echo             MorocoVoice v3.5.0
echo   Suite de Dictado y Reescritura por Voz en Windows
echo ======================================================
echo.

:: 1. Verificacion y Creacion Automatica del Entorno Virtual (Zero-Touch)
if not exist ".venv\Scripts\python.exe" (
    echo [*] Primer inicio detectado: Configurando entorno para MorocoVoice...
    echo [*] Verificando instalador de Python en el sistema...

    python --version >nul 2>&1
    if errorlevel 1 (
        py -3 --version >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] No se detecto Python en el sistema.
            echo Por favor descarga e instala Python 3.10 o 3.11 desde:
            echo   https://www.python.org/downloads/
            echo IMPORTANTE: Marca la casilla "Add Python to PATH" al instalar.
            echo.
            pause
            exit /b 1
        ) else (
            set "PY_CMD=py -3"
        )
    ) else (
        set "PY_CMD=python"
    )

    echo [*] Creando entorno virtual aislado (.venv)...
    !PY_CMD! -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )

    echo [*] Instalando dependencias industriales (ONNX Runtime, Groq, CTranslate2)...
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip --quiet
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Ocurrio un fallo instalando requirements.txt.
        pause
        exit /b 1
    )

    if not exist ".env" (
        if exist ".env.example" (
            copy .env.example .env >nul
            echo [*] Archivo de configuracion .env generado desde plantilla.
        )
    )
    echo [*] Entorno de MorocoVoice inicializado con exito!
    echo.
)

:: 2. Limpieza de Procesos Previos para Evitar Conflictos de Mutex
echo * Verificando y cerrando instancias huerfanas de MorocoVoice...
powershell -NoProfile -Command "Get-Process python*, pythonw* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*MorocoVoice*' -or $_.Path -like '*VoiceFlow-Win*' } | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1

:: 3. Arranque en Segundo Plano
echo * Lanzando MorocoVoice en la bandeja del sistema...
echo * Atajo de Dictado: Win + Space
echo * Atajo de Reescritura: Ctrl + Shift + Space
echo.

start "" ".venv\Scripts\pythonw.exe" -m app.main
exit /b 0
