@echo off
setlocal
chcp 65001 >nul
title MorocoVoice Launcher

cd /d "%~dp0"

echo ======================================================
echo             MorocoVoice v1.0.6
echo   Suite de Dictado y Reescritura por Voz en Windows
echo ======================================================
echo.

REM ============================================================
REM 1. Entorno virtual: reutilizar, reparar o crear (Zero-Touch)
REM ============================================================
REM    El lanzador anterior solo continuaba si existian a la vez
REM    .venv\Scripts\python.exe Y .venv\.installed. Si el marcador no llegaba
REM    a escribirse -instalacion interrumpida, venv creado a mano o marcador
REM    borrado- el script se creia en el "primer inicio" y exigia un Python
REM    en el PATH. En un equipo donde Python NO esta en el PATH eso produce un
REM    error falso: el entorno virtual ya era perfectamente valido.
REM
REM    Ahora se valida el entorno real, no un fichero centinela:
REM      1. Si .venv tiene un Python 3.11+ que arranca, se reutiliza aunque
REM         falte el marcador.
REM      2. Si no hay entorno utilizable, se busca Python 3.11+ en el PATH, en
REM         el lanzador oficial py, en el registro de Windows y en las rutas de
REM         instalacion habituales de python.org.
REM      3. Con el entorno listo solo se comprueban las dependencias; si faltan
REM         se instalan con el pip del propio entorno.

if not exist ".venv\Scripts\python.exe" goto :FIND_PYTHON

call :VENV_READY
if errorlevel 1 goto :RECREATE_VENV

echo [*] Entorno virtual .venv localizado y operativo.
goto :ENSURE_DEPS

:RECREATE_VENV
echo [!] El entorno virtual .venv existe pero no arranca.
echo     Habitualmente significa que el Python base se desinstalo o se movio.
echo     Se recreara desde cero.
echo.

REM ------------------------------------------------------------
REM 2. Localizacion de un interprete Python 3.11+
REM ------------------------------------------------------------
:FIND_PYTHON
echo [*] Verificando instalador de Python 3.11+ en el sistema ...

call :TRY_PY python
if not errorlevel 1 goto :HAVE_PYTHON
call :TRY_PY py -3.11
if not errorlevel 1 goto :HAVE_PYTHON
call :TRY_PY py -3
if not errorlevel 1 goto :HAVE_PYTHON

REM El instalador de python.org en modo "solo para mi" deja Python en
REM %LOCALAPPDATA%\Programs\Python\Python3XX y NO toca el PATH salvo que se
REM marque "Add Python to PATH". El registro de Windows si sabe donde esta, de
REM modo que aqui se rescata una instalacion que el PATH ignora.
echo [*] Python no esta en el PATH. Consultando el registro de Windows ...
for /f "tokens=2,*" %%A in ('reg query "HKCU\SOFTWARE\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i /c:"ExecutablePath"') do (
    call :TRY_PY "%%~B"
    if not errorlevel 1 goto :HAVE_PYTHON
)
for /f "tokens=2,*" %%A in ('reg query "HKLM\SOFTWARE\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i /c:"ExecutablePath"') do (
    call :TRY_PY "%%~B"
    if not errorlevel 1 goto :HAVE_PYTHON
)

echo [*] Revisando rutas de instalacion habituales ...
REM De la mas nueva a la mas antigua: 3.11 es el minimo funcional, pero
REM cualquier version posterior sirve y suele ser la que el usuario instalo.
for %%D in (
    "%LOCALAPPDATA%\Programs\Python\Python314"
    "%LOCALAPPDATA%\Programs\Python\Python313"
    "%LOCALAPPDATA%\Programs\Python\Python312"
    "%LOCALAPPDATA%\Programs\Python\Python311"
    "%ProgramFiles%\Python314"
    "%ProgramFiles%\Python313"
    "%ProgramFiles%\Python312"
    "%ProgramFiles%\Python311"
    "C:\Python314"
    "C:\Python313"
    "C:\Python312"
    "C:\Python311"
) do (
    call :TRY_PY "%%~D\python.exe"
    if not errorlevel 1 goto :HAVE_PYTHON
)

goto :NO_PY

:HAVE_PYTHON
echo [*] Interprete valido encontrado: %PY_CMD%
echo.

REM ------------------------------------------------------------
REM 3. Creacion del entorno virtual aislado
REM ------------------------------------------------------------
:CREATE_VENV
if exist ".venv" (
    echo [!] Eliminando el entorno virtual anterior, que ya no es utilizable ...
    rmdir /s /q ".venv"
)

echo [*] Creando entorno virtual aislado .venv con %PY_CMD% ...
%PY_CMD% -m venv .venv
if errorlevel 1 (
    echo [ERROR] No se pudo crear el entorno virtual.
    echo         Revisa el espacio libre en disco y el antivirus.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM 4. Dependencias, configuracion y marcador de instalacion
REM ------------------------------------------------------------
:ENSURE_DEPS
set "VENV_PY=.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [ERROR] No se encontro el interprete del entorno virtual:
    echo         %CD%\%VENV_PY%
    pause
    exit /b 1
)

call :DEPS_OK
if not errorlevel 1 goto :WRITE_MARKER

echo [*] Instalando dependencias industriales: ONNX Runtime, Groq, CTranslate2 ...
"%VENV_PY%" -m pip install --upgrade pip --quiet
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Ocurrio un fallo instalando requirements.txt.
    echo         Comprueba la conexion a Internet y vuelve a intentarlo.
    pause
    exit /b 1
)
set "MV_SETUP_DONE=1"

:WRITE_MARKER
REM Marcador de cache. Se reescribe en cada arranque para que borrarlo no
REM devuelva al usuario al asistente de instalacion.
echo installed > ".venv\.installed"

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

if defined MV_SETUP_DONE (
    echo [*] Entorno de MorocoVoice inicializado con exito!
)
echo.

REM ------------------------------------------------------------
REM 5. Acceso directo, guardia de integridad y arranque
REM ------------------------------------------------------------
:RUN_APP
REM 5.1 Asegurar acceso directo en el Escritorio con icono oficial si no existe
if not exist "%USERPROFILE%\Desktop\Moroco Voice.lnk" (
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Moroco Voice.lnk')); $s.TargetPath = '%~dp0run.bat'; $s.WorkingDirectory = '%~dp0'; if (Test-Path '%~dp0morocovoice.ico') { $s.IconLocation = '%~dp0morocovoice.ico,0' }; $s.Description = 'MorocoVoice - Suite de Dictado y Reescritura por Voz'; $s.WindowStyle = 7; $s.Save()" >nul 2>&1
)
REM 5.2 Guardia de integridad: si el proceso corre en Low, Windows denegara el
REM     icono de bandeja y el hook de teclado no vera ninguna tecla, asi que la
REM     app parecera viva pero sin funcionar. Avisamos ANTES de arrancar.
REM     (El nombre del nivel no se traduce: "Low Mandatory Level" es igual en
REM     cualquier idioma de Windows, por eso se busca en ingles.)
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

REM 5.3 Limpieza de Procesos Previos para Evitar Conflictos de Mutex
REM    IMPORTANTE: .venv\Scripts\pythonw.exe es solo un lanzador (redirector).
REM    El interprete que realmente ejecuta la app vive en
REM    ...\Programs\Python\Python311\pythonw.exe y NO contiene "MorocoVoice"
REM    en su ruta, por lo que un filtro por ruta dejaba huerfanos vivos.
REM    Se filtra por linea de comandos (app.main) para cerrar AMBOS.
echo * Verificando y cerrando instancias previas de MorocoVoice...
powershell -NoProfile -Command "$root = (Get-Item '%~dp0').FullName.TrimEnd('\'); Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*app.main*' -and $_.CommandLine -like ('*' + $root + '*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Start-Sleep -Milliseconds 600" >nul 2>&1

REM 5.4 Arranque en Pantalla y Segundo Plano
echo * Lanzando MorocoVoice en segundo plano...
echo * Doble clic en icono de bandeja para abrir opciones.
echo.

start "" ".venv\Scripts\pythonw.exe" -m app.main
exit /b 0

REM ============================================================
REM Subrutinas
REM ============================================================

:NO_PY
echo.
echo [ERROR] No se detecto una instalacion valida de Python 3.11 o superior.
echo MorocoVoice requiere Python 3.11+ con soporte StrEnum y tipado moderno.
echo.
echo Se han revisado, sin exito:
echo   - el comando "python" del PATH
echo   - el lanzador oficial "py" y "py -3.11"
echo   - el registro de Windows, HKCU y HKLM PythonCore
echo   - las carpetas de instalacion habituales de python.org
echo.
echo Descarga e instala Python 3.11 o superior desde:
echo   https://www.python.org/downloads/windows/
echo.
echo IMPORTANTE: marca la casilla "Add Python to PATH" durante la instalacion.
echo.
echo Si Python ya esta instalado pero el PATH no lo ve, pega aqui la ruta
echo de su python.exe y MorocoVoice lo usara sin tocar el PATH.
echo.
set "PY_EXE="
set /p "PY_EXE=Ruta de python.exe, o pulsa Enter para salir: "
if not defined PY_EXE goto :NO_PY_EXIT
REM Se quitan comillas por si el usuario las pega; :TRY_PY ya las repone.
set "PY_EXE=%PY_EXE:"=%"
call :TRY_PY "%PY_EXE%"
if errorlevel 1 (
    echo [ERROR] Esa ruta no corresponde a un Python 3.11 o superior valido.
    goto :NO_PY_EXIT
)
goto :HAVE_PYTHON

:NO_PY_EXIT
echo.
pause
exit /b 1

:VENV_READY
REM 0 si .venv contiene un Python 3.11+ que arranca de verdad. Un venv cuyo
REM interprete base desaparecio falla aqui, que es justo lo que queremos saber.
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.hexversion >= 0x030B0000 else 1)" >nul 2>&1
exit /b %errorlevel%

:DEPS_OK
REM 0 si el entorno tiene las dependencias clave. find_spec no importa los
REM modulos, solo comprueba que estan instalados, asi que es barato.
"%VENV_PY%" -c "import importlib.util as u, sys; mods = 'numpy onnxruntime sounddevice faster_whisper pynput pystray PIL win32api groq'.split(); sys.exit(0 if sys.hexversion >= 0x030B0000 and all(u.find_spec(m) for m in mods) else 1)" >nul 2>&1
exit /b %errorlevel%

:TRY_PY
REM Uso: call :TRY_PY ^<comando^>
REM Devuelve 0 y deja el comando en PY_CMD si ese interprete arranca y es 3.11+.
%* --version >nul 2>&1
if errorlevel 1 exit /b 1
%* -c "import sys; sys.exit(0 if sys.hexversion >= 0x030B0000 else 1)" >nul 2>&1
if errorlevel 1 exit /b 1
set "PY_CMD=%*"
exit /b 0
