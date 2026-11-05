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

REM 1. Verificación y Creación Automática del Entorno Virtual (Zero-Touch)
if exist ".venv\Scripts\python.exe" goto :RUN_APP

echo [*] Primer inicio detectado: Configurando entorno para MorocoVoice...
echo [*] Verificando instalador de Python 3.13 / 3.11+ en el sistema...

set "PY_CMD="
REM Priorizar Python 3.13 como estándar canónico de la estación
py -3.13 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3.13"
    goto :CREATE_VENV
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; sys.exit(0 if sys.hexversion >= 0x030B0000 else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -3"
        goto :CREATE_VENV
    )
)

python --version >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.hexversion >= 0x030B0000 else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
        goto :CREATE_VENV
    )
)

echo [ERROR] No se detectó una instalación válida de Python 3.13 o 3.11+.
echo MorocoVoice requiere Python con soporte moderno de tipado y subprocesos.
echo Por favor descarga e instala Python 3.13 desde https://www.python.org/downloads/
echo IMPORTANTE: Marca la casilla "Add Python to PATH" durante la instalación.
echo.
pause
exit /b 1

:CREATE_VENV
echo [*] Creando entorno virtual aislado (.venv) con %PY_CMD%...
%PY_CMD% -m venv .venv
if errorlevel 1 (
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
)

echo [*] Instalando dependencias industriales (ONNX Runtime, Groq, Whisper, SoundDevice)...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Ocurrió un fallo instalando requirements.txt.
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [*] Archivo de configuración .env generado desde plantilla.
    )
)

if not exist "config.json" (
    if exist "config.example.json" (
        copy config.example.json config.json >nul
        echo [*] Archivo config.json generado desde plantilla.
    )
)

echo [*] Entorno de MorocoVoice inicializado con éxito!
echo.

:RUN_APP
REM 1.1 Asegurar acceso directo en el Escritorio con icono oficial si no existe
if not exist "%USERPROFILE%\Desktop\Moroco Voice.lnk" (
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Moroco Voice.lnk')); $s.TargetPath = '%~dp0run.bat'; $s.WorkingDirectory = '%~dp0'; if (Test-Path '%~dp0morocovoice.ico') { $s.IconLocation = '%~dp0morocovoice.ico,0' }; $s.Description = 'MorocoVoice - Suite de Dictado y Reescritura por Voz'; $s.WindowStyle = 7; $s.Save()" >nul 2>&1
)

REM 1.2 Asegurar inicio automático con Windows en shell:startup
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if not exist "%STARTUP_FOLDER%\Moroco Voice.lnk" (
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine('%STARTUP_FOLDER%', 'Moroco Voice.lnk')); $s.TargetPath = '%~dp0run.bat'; $s.WorkingDirectory = '%~dp0'; if (Test-Path '%~dp0morocovoice.ico') { $s.IconLocation = '%~dp0morocovoice.ico,0' }; $s.Description = 'MorocoVoice - Suite de Dictado y Reescritura por Voz'; $s.WindowStyle = 7; $s.Save()" >nul 2>&1
)

REM 2. Guardia de integridad: si el proceso corre en Low, Windows denegará el
REM    icono de bandeja y el hook de teclado no verá ninguna tecla.
set "MV_INTEGRITY="
for /f "delims=" %%i in ('whoami /groups ^| findstr /i "Mandatory Level"') do set "MV_INTEGRITY=%%i"
echo %MV_INTEGRITY% | findstr /i /c:"Low Mandatory" >nul
if not errorlevel 1 (
  echo.
  echo ************************************************************
  echo  AVISO: ENTORNO RESTRINGIDO ^(integridad Low^)
  echo ************************************************************
  echo  Esta carpeta tiene etiqueta de integridad Low, así que Windows
  echo  denegará el icono de bandeja y el hook de teclado.
  echo.
  echo  Solución: ejecuta en PowerShell o CMD:
  echo    icacls "%~dp0." /setintegritylevel Medium /T /C
  echo.
  echo  Detalles en docs\TROUBLESHOOTING.md
  echo ************************************************************
  echo.
  pause
)

REM 3. Limpieza de Procesos Previos para Evitar Conflictos de Mutex
echo [*] Verificando y cerrando instancias previas de MorocoVoice...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*app.main*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Start-Sleep -Milliseconds 600" >nul 2>&1

REM 4. Arranque en Pantalla y Segundo Plano
echo [*] Lanzando MorocoVoice en segundo plano...

start "" /d "%~dp0" "%~dp0.venv\Scripts\pythonw.exe" -m app.main

REM 5. Verificación de Salud Post-Arranque (Evita Fallas Silenciosas)
powershell -NoProfile -Command "Start-Sleep -Milliseconds 1500; $proc = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*app.main*' }; if ($proc) { exit 0 } else { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo.
    echo ======================================================
    echo  [ERROR] MorocoVoice no pudo iniciar o se cerró al arrancar.
    echo ======================================================
    echo Mostrando las últimas líneas de morocovoice.log:
    echo.
    if exist "morocovoice.log" (
        powershell -NoProfile -Command "Get-Content morocovoice.log -Tail 15"
    ) else (
        echo [!] No se encontró morocovoice.log.
    )
    echo.
    echo Presiona cualquier tecla para salir...
    pause >nul
    exit /b 1
)

echo [✓] MorocoVoice iniciado con éxito.
echo [✓] Icono disponible en la bandeja del sistema (junto al reloj).
echo [✓] Doble clic en el icono para abrir Configuración.
powershell -NoProfile -Command "Start-Sleep -Milliseconds 1200" >nul 2>&1
exit /b 0
