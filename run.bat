@echo off
setlocal
title MorocoVoice Launcher

cd /d "%~dp0"

echo ======================================================
echo             MorocoVoice v1.0.0
echo   Suite de Dictado y Reescritura por Voz en Windows
echo ======================================================
echo.

REM 1. Verificacion y Creacion Automatica del Entorno Virtual (Zero-Touch)
if exist ".venv\Scripts\python.exe" goto :RUN_APP

echo [*] Primer inicio detectado: Configurando entorno para MorocoVoice...
echo [*] Verificando instalador de Python en el sistema...

python --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :CREATE_VENV
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
    goto :CREATE_VENV
)

echo [ERROR] No se detecto Python instalado en el sistema.
echo Por favor descarga e instala Python 3.10 o 3.11 desde:
echo   https://www.python.org/downloads/
echo IMPORTANTE: Marca la casilla "Add Python to PATH" durante la instalacion.
echo.
pause
exit /b 1

:CREATE_VENV
echo [*] Creando entorno virtual aislado (.venv)...
%PY_CMD% -m venv .venv
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

:RUN_APP
REM 2. Limpieza de Procesos Previos para Evitar Conflictos de Mutex
echo * Verificando y cerrando instancias previas de MorocoVoice...
powershell -NoProfile -Command "Get-Process python*, pythonw* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*MorocoVoice*' -or $_.Path -like '*VoiceFlow-Win*' } | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1

REM 3. Arranque en Pantalla y Segundo Plano
echo * Lanzando MorocoVoice...
echo * Atajo de Dictado: Win + Space
echo * Atajo de Reescritura: Ctrl + Shift + Space
echo.

start "" ".venv\Scripts\pythonw.exe" -m app.main
exit /b 0
