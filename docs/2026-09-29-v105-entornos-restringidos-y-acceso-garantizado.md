# MorocoVoice v1.0.5 — Entornos restringidos y acceso garantizado a Configuración

**Fecha:** 2026-09-29
**Tipo:** Corrección de robustez y diagnóstico (sin cambios de arquitectura)

---

## 1. Resumen

Se investigó un fallo reportado como *«la aplicación se apaga y ya no me deja las
opciones junto al reloj, y el hotkey tampoco funciona»*. La conclusión es que **el código
de MorocoVoice era correcto**: el problema estaba en el **contexto de seguridad de
Windows** desde el que se lanzaba el proceso. Esa causa era **invisible** porque, al
ejecutarse con `pythonw.exe`, `sys.stdout` y `sys.stderr` son `None` y **toda excepción de
un hilo secundario se descartaba sin dejar rastro**.

Esta versión no solo corrige el efecto, sino que **hace visible la causa** para que no
vuelva a ocurrir a nadie más.

---

## 2. Causa raíz (evidencia verificada)

La carpeta `C:\Users\<usuario>\Documents\GitHub` tenía una etiqueta de integridad
heredable:

```
Mandatory Label\Low Mandatory Level:(OI)(CI)(NW)
```

Al ser **heredable**, la heredaban todos los archivos dentro, incluido
`.venv\Scripts\pythonw.exe`. Y como la integridad del proceso es
`min(integridad_del_padre, etiqueta_del_ejecutable)`, **el proceso arrancaba en Low**
aunque el usuario lo lanzara con doble clic desde el Escritorio.

Consecuencias medidas en ese estado:

| Llamada Win32 | Resultado observado |
| :--- | :--- |
| `Shell_NotifyIcon(NIM_ADD)` | `FAILED` → `[WinError 5] Acceso denegado` |
| `SetWindowsHookEx(WH_KEYBOARD_LL)` | Se instala, **hilo vivo**, y recibe **0 eventos** en 25 s |
| `ChangeWindowMessageFilterEx` | `[WinError 5] Acceso denegado` |
| `GetAsyncKeyState` (sonda propia) | No detecta ni las pulsaciones inyectadas por el propio proceso |

El origen de la etiqueta fue el **sandbox de espacio de trabajo de un agente de IA**, que
la aplica de forma *standing* (no se revoca al terminar la sesión) para confinar la
escritura de sus procesos hijos. Se confirmó en la documentación del propio sandbox:

> *"Security descriptor edits are standing directory mutations … never revoked"*
> *"A standing Low label outlives [the tool] … the workspace's inheritable label survives the session"*

### Experimento de confirmación (antes / después)

| | Antes | Después de `icacls … /setintegritylevel Medium /T /C` |
| :--- | :--- | :--- |
| Integridad del proceso | `0x1000` (Low) | `0x2000` (Medium) |
| `Shell_NotifyIcon(NIM_ADD)` | Acceso denegado | **Aceptado**, sin errores |
| Captura de teclado (autoprueba) | **0 eventos** | **Evento observado** |
| Icono en la bandeja | Rechazado por el shell | Publicado (`visible=True`) |
| Atajo `Win+Space` | Mudo | `Dictation hotkey triggered` |

Mismo equipo, misma sesión, mismo binario: **lo único que cambió fue la etiqueta del
archivo**.

---

## 3. Cambios

### 3.1 Nuevo: sonda de contexto de seguridad

`app/platform/environment.py` (nuevo) inspecciona el token del proceso y clasifica el
entorno:

- Nivel de integridad (leído del SID de la etiqueta obligatoria).
- Si el proceso corre dentro de un **AppContainer**.
- Si está elevado.

`SecurityContext.supports_tray_and_hooks` responde a la única pregunta que importa:
*¿puede Windows concederme bandeja y atajos globales?* Si la consulta del token falla,
**nunca** se declara un entorno sano (evita falsos positivos).

### 3.2 Arranque: el fallo deja de ser invisible

- `app/main.py` ejecuta la sonda antes de arrancar los subsistemas y registra
  `Security context: integrity=…`. Si el entorno es restrictivo, escribe un bloque
  **`ENTORNO RESTRINGIDO DETECTADO`** con causa, consecuencia y **el comando exacto** para
  arreglarlo, y avisa en el HUD.
- `app/logging_setup.py` instala hooks de excepción para `sys.excepthook` y
  `threading.excepthook` que **escriben las trazas en el log**. Además deja de añadir un
  `StreamHandler(None)` cuando no hay consola (`pythonw.exe`).

### 3.3 El hook de teclado se verifica de verdad

Antes bastaba con comprobar que el hilo del listener estaba vivo, lo que **no detecta el
fallo real** (el hilo vive y no recibe nada). Ahora `HotkeyListener._verify_capture()`
**inyecta una pulsación inocua de `Shift`** con `SendInput` y exige que el hook la
observe. Un `Shift` solo, sin más teclas, no produce carácter, no dispara atajos y no
cambia ningún estado, pero recorre toda la ruta de entrada.

La lógica es sólida incluso ante falsos positivos: cualquier evento observado —incluida
una pulsación real del usuario— **demuestra** que el hook recibe entrada.

### 3.4 Acceso a Configuración garantizado

**Este era el defecto de diseño de fondo.** La única vía documentada a la ventana de
Configuración era el icono de la bandeja. Si ese icono falla, el usuario queda encerrado
sin poder cambiar nada.

- Nuevo ajuste `hotkey_settings` con valor por defecto **`Ctrl + Alt + S`**.
- Expuesto en la ventana de Configuración, que además **exige que no quede vacío** (es la
  red de seguridad).
- El log de fallo de bandeja ahora indica qué tecla pulsar para abrir Configuración.

**Bug corregido de paso:** `settings_window.py` ejecutaba
`cfg_dict.pop("hotkey_shutdown")` y `cfg_dict.pop("hotkey_diagnostics")` al guardar, lo
que **borraba silenciosamente** esos ajustes en cada guardado y los dejaba inservibles.
Ahora se persisten, y `hotkey_diagnostics` (`Ctrl + Shift + D`) también es editable.

### 3.5 Bandeja: los fallos silenciosos de pystray, instrumentados

- `ChangeWindowMessageFilterEx` puede fallar con acceso denegado. pystray no lo protege,
  así que **mataba el hilo de la bandeja entero**. Su fallo ahora es una advertencia.
- `Shell_NotifyIcon` estaba declarado **sin `errcheck`**: si Windows rechazaba el icono,
  fallaba en silencio mientras `icon.visible` seguía diciendo `True`. Ahora se reporta.
- Corregido un detalle de `pystray`: si se pasa un callback `setup` propio, la librería
  **no** publica el icono por ti. Ahora se hace explícitamente.

### 3.6 Lanzadores y diagnóstico

- **`diagnostico.bat`** (nuevo): informe de un clic con audio, hardware y **entorno de
  seguridad**, con veredicto y salida en español.
- **`verify_install.py`**: añade comprobación de contexto de seguridad, **autoprueba real
  de captura de teclado** y lectura de la política de bandeja de Windows 11
  (`IsPromoted`). La cabecera ya no tiene la versión escrita a mano (decía v1.0.3).
- **`run.bat`**: avisa **antes de arrancar** si detecta integridad Low, con el comando de
  solución. Corrige el cierre de instancias previas: antes mataba solo el lanzador
  `.venv\Scripts\pythonw.exe` y dejaba huérfano el intérprete real
  (`Programs\Python\Python311\pythonw.exe`), que no coincide con el filtro por ruta.
- `chcp 65001` en los `.bat` para que los acentos se muestren correctamente.

### 3.7 Documentación

- **`docs/TROUBLESHOOTING.md`** (nuevo): guía de triaje con el caso de integridad Low,
  el icono escondido en el cajón `^`, el conflicto de `Win+Space` con el conmutador de
  idioma de Windows, UIPI y micrófono.
- `README.md`: sección de solución de problemas, atajo de Configuración y estructura
  actualizada.

---

## 4. Pruebas

- **43 tests** (antes 33). Nuevos: `tests/test_environment.py` (clasificación del
  contexto, formato e idempotencia del comando de solución) y los de despacho del atajo
  de Configuración en `tests/test_hotkey.py`.
- `ruff check app tests` limpio.
- Verificación manual extremo a extremo: antes/después de la etiqueta, con evidencia de
  las cuatro llamadas Win32 y del icono publicado.

---

## 5. Nota de compatibilidad

- Sin cambios en el formato de `config.json`. Los ajustes nuevos tienen valores por
  defecto sensatos, así que las configuraciones existentes siguen funcionando.
- `Win + Space` se mantiene como atajo de dictado por defecto (compatibilidad con el
  comportamiento previo), pero **se recomienda cambiarlo** en equipos con más de un
  idioma de teclado instalado. Ver `docs/TROUBLESHOOTING.md`, sección 3.
- Si tu instalación ya arrastraba la etiqueta Low, el arreglo es de una sola línea:

```cmd
icacls "C:\ruta\a\MorocoVoice" /setintegritylevel Medium /T /C
```
