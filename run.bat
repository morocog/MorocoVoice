@echo off
setlocal
chcp 65001 >nul
title MorocoVoice Launcher

cd /d "%~dp0"

echo ======================================================
echo             MorocoVoice v1.0.5
echo   Suite de Dictado y Reescritura por Voz en Windows
echo ======================================================
echo.

REM 1. Verificacion y Creacion Automatica del Entorno Virtual (Zero-Touch)
if exist ".venv\Scripts\python.exe" goto :RUN_APP

echo [*] Primer inicio detectado: Configurando entorno para MorocoVoice...
echo [*] Verificando instalador de Python 3.11+ en el sistema...

set "PY_CMD="
python --version >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
    py -3.11 --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.11"
)

if not defined PY_CMD (
    py -3 --version >nul 2>&1
    if not errorlevel 1 (
        py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
        if not errorlevel 1 set "PY_CMD=py -3"
    )
)

if not defined PY_CMD (
    echo [ERROR] No se detecto una instalacion valida de Python 3.11 o superior.
    echo MorocoVoice requiere Python 3.11+ (con soporte StrEnum y tipado moderno).
    echo Por favor descarga e instala Python 3.11 o superior desde:
    echo   https://www.python.org/downloads/
    echo IMPORTANTE: Marca la casilla "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

:CREATE_VENV
echo [*] Creando entorno virtual aislado (.venv) con %PY_CMD%...
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

if not exist "config.json" (
    if exist "config.example.json" (
        copy config.example.json config.json >nul
        echo [*] Archivo config.json generado desde plantilla.
    )
)

echo [*] Entorno de MorocoVoice inicializado con exito!
echo.

:RUN_APP
REM 2. Guardia de integridad: si el proceso corre en Low, Windows denegara el
REM    icono de bandeja y el hook de teclado no vera ninguna tecla, asi que la
REM    app parecera viva pero sin funcionar. Avisamos ANTES de arrancar.
REM    (El nombre del nivel no se traduce: "Low Mandatory Level" es igual en
REM    cualquier idioma de Windows, por eso se busca en ingles.)
set "MV_INTEGRITY="
for /f "delims=" %%i in ('whoami /groups ^| findstr /i "Mandatory Level"') do set "MV_INTEGRITY=%%i"
REM    /c: es imprescindible: findstr trata las palabras separadas por espacio como
REM    terminos alternativos (OR), asi que "Low Mandatory" coincidiria siempre.
echo %MV_INTEGRITY% | findstr /i /c:"Low Mandatory" >nul
if not errorlevel 1 (
  echo.
  echo ************************************************************
  echo  AVISO: ENTORNO RESTRINGIDO ^(integridad Low^)
  echo ************************************************************
  echo  Esta carpeta tiene etiqueta de integridad Low, asi que la
  echo  aplicacion se lanzara en Low y Windows le denegara el icono
  echo  de bandeja ^(no aparecera junto al reloj^) y el hook de teclado
  echo  ^(ningun atajo funcionara^), aunque parezca arrancar bien.
  echo.
  echo  Solucion: cierra esta ventana y ejecuta en CMD o PowerShell:
  echo.
  echo    icacls "%~dp0." /setintegritylevel Medium /T /C
  echo.
  echo  Despues vuelve a lanzar run.bat. Detalles en docs\TROUBLESHOOTING.md
  echo ************************************************************
  echo.
  pause
)

REM 3. Limpieza de Procesos Previos para Evitar Conflictos de Mutex
REM    IMPORTANTE: .venv\Scripts\pythonw.exe es solo un lanzador (redirector).
REM    El interprete que realmente ejecuta la app vive en
REM    ...\Programs\Python\Python311\pythonw.exe y NO contiene "MorocoVoice"
REM    en su ruta, por lo que un filtro por ruta dejaba huerfanos vivos.
REM    Se filtra por linea de comandos (app.main) para cerrar AMBOS.
echo * Verificando y cerrando instancias previas de MorocoVoice...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*app.main*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Start-Sleep -Milliseconds 600" >nul 2>&1

REM 4. Arranque en Pantalla y Segundo Plano
echo * Lanzando MorocoVoice...
echo * Atajo de Dictado: Win + Space
echo * Atajo de Reescritura: Ctrl + Shift + Space
echo * Atajo de Configuracion: Ctrl + Alt + S  (util si el icono no aparece)
echo.

start "" ".venv\Scripts\pythonw.exe" -m app.main
exit /b 0
