# Solución de Problemas (Troubleshooting) — MorocoVoice

Guía de diagnóstico para los fallos que **no** son culpa del código de MorocoVoice,
sino del entorno de Windows desde el que se lanza. Está escrita a partir de un caso
real reproducido y verificado de principio a fin.

---

## ⚡ Triaje rápido

Ejecuta primero **`diagnostico.bat`** (doble clic). Analiza audio, hardware y entorno
de seguridad, y te dice exactamente qué falla. Si prefieres ir directo al síntoma:

| Síntoma | Causa más probable | Sección |
| :--- | :--- | :--- |
| El HUD aparece y desaparece, pero **no hay icono junto al reloj** y **ningún atajo funciona** | La app corre en integridad **Low** | [1](#1-el-icono-no-aparece-y-ningún-atajo-funciona-integridad-low) |
| El icono existe pero está escondido en el cajón `^` | Política de bandeja de Windows 11 | [2](#2-el-icono-existe-pero-windows-lo-esconde-en-el-cajón-) |
| `Win+Space` **cambia el idioma del teclado** en vez de dictar | Conflicto con el atajo nativo de Windows | [3](#3-winspace-cambia-el-idioma-del-teclado-en-vez-de-dictar) |
| Sale el HUD y dice «Escuchando», pero **no se escribe nada** | La ventana destino es elevada (UIPI) | [4](#4-sale-el-hud-pero-no-se-escribe-nada) |
| Sale el HUD «Admin Activo (Ejecuta como Admin)» | Ventana destino elevada | [4](#4-sale-el-hud-pero-no-se-escribe-nada) |
| «Error de Micrófono» | Permiso de micrófono o dispositivo ocupado | [5](#5-error-de-micrófono) |

---

## 1. El icono no aparece y ningún atajo funciona (integridad Low)

**Este es el caso más confuso y el más importante.** La aplicación arranca, muestra la
cápsula flotante *«MorocoVoice Activo»*, no registra ni un solo error… y sin embargo:

- No aparece ningún icono junto al reloj → **no hay acceso a Configuración**.
- Pulsar `Win+Space` no hace nada (el idioma del teclado sí cambia: eso lo hace Windows).
- En `morocovoice.log` **no hay ninguna línea** de `Dictation hotkey triggered`.

### Por qué ocurre

MorocoVoice necesita dos capacidades que Windows **solo concede a procesos con
integridad Medium o superior**:

1. Publicar un icono en la bandeja del sistema → `Shell_NotifyIcon(NIM_ADD)`
2. Recibir pulsaciones globales → `SetWindowsHookEx(WH_KEYBOARD_LL)`

Cuando el proceso corre en integridad **Low**, ambas se deniegan **en silencio**:

| Llamada | Resultado real en Low |
| :--- | :--- |
| `Shell_NotifyIcon(NIM_ADD)` | Falla con `ERROR_ACCESS_DENIED` (WinError 5) |
| `SetWindowsHookEx(WH_KEYBOARD_LL)` | **Se instala bien** y el hilo queda vivo… pero UIPI descarta todos los eventos |
| `ChangeWindowMessageFilterEx` | Falla con `ERROR_ACCESS_DENIED` |

La trampa es la segunda fila: el hook *parece* correcto (el hilo está vivo, la app
registra «listener activo») mientras recibe **cero** pulsaciones. Por eso el fallo es
tan difícil de ver.

### De dónde sale la integridad Low

La integridad del proceso es **el mínimo entre la del proceso padre y la etiqueta del
ejecutable**:

```
integridad_proceso = min( integridad_del_padre , etiqueta_del_archivo.exe )
```

Si la carpeta de la aplicación (o **cualquier carpeta padre**) lleva una etiqueta de
integridad `Low`, **todos los ejecutables dentro se lanzan en Low** — da igual que los
abras con doble clic desde el Escritorio.

¿Quién pone esa etiqueta? Muy habitualmente el **sandbox de un agente de IA**: los
sandboxes de espacio de trabajo etiquetan su carpeta raíz como Low para confinar lo que
escriben sus procesos. Esa etiqueta es **heredable** y, en varios productos, **no se
revoca al terminar la sesión**. Si además usas Git, `Documents\GitHub` es un candidato
perfecto.

> Este fue exactamente el caso real: `C:\Users\...\Documents\GitHub` estaba etiquetada
> `Mandatory Label\Low Mandatory Level:(OI)(CI)(NW)`, y `.venv\Scripts\pythonw.exe`
> heredaba esa etiqueta.

### Cómo confirmarlo

**Opción A — con la propia herramienta:**

```cmd
diagnostico.bat
```

Debe aparecer un **ERROR CRÍTICO** en la sección `ENTORNO DE SEGURIDAD`, indicando la
integridad detectada y el comando exacto para arreglarlo.

**Opción B — a mano:**

```cmd
whoami /groups | findstr /i "Mandatory Level"
```

- `Mandatory Label\Medium Mandatory Level` → correcto.
- `Mandatory Label\Low Mandatory Level` → **esto es el problema**.

Y para ver la etiqueta de la carpeta:

```cmd
icacls "C:\ruta\a\MorocoVoice"
```

Busca una línea `Mandatory Label\Low Mandatory Level:...`.

### La solución

Desde un **CMD o PowerShell normal** (no hace falta ser administrador):

```cmd
icacls "C:\ruta\a\MorocoVoice" /setintegritylevel Medium /T /C
```

- `/T` aplica el cambio a toda la carpeta de forma recursiva.
- `/C` continúa aunque algún archivo falle.
- Si la etiqueta está en una **carpeta padre** (p. ej. todo `Documents\GitHub`), aplícalo
  también ahí, o directamente sobre la carpeta padre para no dejar la aplicación dentro
  de un árbol etiquetado.

Después **cierra y vuelve a lanzar MorocoVoice** (`run.bat`). El proceso nuevo ya
arrancará en Medium y recuperará el icono y los atajos.

Verificación rápida: el log debe mostrar ahora

```
Security context: integrity=Medium (0x2000), app_container=False, elevated=False
```

y, si sigue estando en Low, un bloque `ENTORNO RESTRINGIDO DETECTADO: ...` explicando el
comando.

### Cómo evitar que vuelva a pasar

La etiqueta **reaparecerá** cada vez que el sandbox de turno vuelva a provisionar esa
carpeta. Tres opciones, de mejor a peor:

1. **Saca MorocoVoice fuera de la carpeta que el sandbox etiqueta.** Por ejemplo
   `C:\Users\<tu-usuario>\Apps\MorocoVoice`. Es la solución definitiva.
2. Ejecuta el agente/sandbox en modo sin confinamiento (`danger-full-access` o
   equivalente) sobre esa carpeta, para que no aplique etiquetas.
3. Vuelve a aplicar el comando `icacls` cuando el problema reaparezca.

---

## 2. El icono existe pero Windows lo esconde en el cajón `^`

Windows 11 **no coloca los iconos nuevos junto al reloj**: los manda al cajón de
desbordamiento (la flechita `^`). Mucha gente lo interpreta como «el icono no aparece».

**Comprobación:** `diagnostico.bat` lo detecta y lo dice explícitamente.

**Solución:**

- Haz clic en `^` y **arrastra** el icono de MorocoVoice a la zona junto al reloj.
- O bien: **Configuración → Personalización → Barra de tareas → Otros iconos de la
  bandeja del sistema** y activa la entrada (puede figurar como `pythonw.exe`).

Internamente esto equivale a poner `IsPromoted = 1` en
`HKCU\Control Panel\NotifyIconSettings\<hash>`.

### Y si el icono no está ni en el cajón

Entonces Windows lo **rechazó**, no lo escondió. El log lo dirá con estas palabras:

```
Shell_NotifyIcon(NIM_ADD) FAILED ([WinError 5] Acceso denegado.)
```

Eso es el caso de la [sección 1](#1-el-icono-no-aparece-y-ningún-atajo-funciona-integridad-low).

### Tranquilidad: ya no te quedas encerrado

Aunque el icono falle, **siempre** tienes una vía de teclado a Configuración:

| Atajo | Función | Por defecto |
| :--- | :--- | :--- |
| Abrir Configuración | Abre esta ventana sin tocar la bandeja | `Ctrl + Alt + S` |
| Diagnóstico (Logs) | Abre `morocovoice.log` en Notepad | `Ctrl + Shift + D` |

Ambos se pueden cambiar dentro de la propia ventana de Configuración. El atajo de
Configuración **no puede quedar vacío** por diseño: es la red de seguridad.

---

## 3. `Win+Space` cambia el idioma del teclado en vez de dictar

`Win + Space` es el atajo **nativo de Windows** para cambiar entre distribuciones de
teclado. MorocoVoice lo escucha con un hook global que **no suprime** la tecla, así que
Windows también lo recibe.

Si tienes más de un idioma instalado (`Configuración → Hora e idioma → Idioma y región`),
puedes ver dos efectos a la vez: cambia el idioma **y** (si todo está bien) empieza a
dictar.

**Recomendación:** cambia el atajo de dictado por uno que no colisione. Buenas opciones:
`Ctrl + Alt + Space`, `Ctrl + Shift + D`… o cualquier combinación libre.

- Desde la UI: clic derecho en el icono → **⚙️ Configuración…** → *Dictado Inteligente*.
- O desde el teclado: `Ctrl + Alt + S`.
- O editando `config.json`:

```json
{ "hotkey_dictation": "ctrl+alt+space" }
```

> Hay una limitación de fondo: `Win+Space` es un atajo **reservado** por el sistema.
> `RegisterHotKey` lo rechaza con `WinError 1409` (*atajo ya registrado*), así que no
> existe forma de «apropiárselo» limpiamente.

---

## 4. Sale el HUD pero no se escribe nada

Casi siempre es **UIPI** (User Interface Privilege Isolation): si la ventana en la que
quieres escribir corre **como Administrador**, un proceso normal no puede inyectarle
texto. MorocoVoice lo detecta y muestra **«Admin Activo (Ejecuta como Admin)»**.

Opciones:

1. Ejecuta MorocoVoice como Administrador (y entonces podrá escribir en ventanas
   elevadas), **o**
2. No dictes hacia aplicaciones elevadas.

En el log aparece así:

```
Target app <nombre> is elevated. UIPI prevents injection.
```

---

## 5. «Error de Micrófono»

1. **Permisos:** Configuración → Privacidad y seguridad → **Micrófono** →
   *Permitir que las aplicaciones de escritorio accedan a tu micrófono* debe estar
   **activado**.
2. **Dispositivo ocupado:** cierra Teams/Zoom/audífonos con software propio que tomen el
   micrófono en exclusiva.
3. **Dispositivo por defecto:** `diagnostico.bat` lista los dispositivos de entrada
   detectados. Si no aparece el tuyo, revisa el panel de sonido de Windows.

---

## 📄 Los registros (logs)

Ruta: **`morocovoice.log`** en la carpeta del proyecto. Rota a los 5 MB (3 copias).

Ábrelo con `Ctrl + Shift + D` o desde el menú del icono (**Abrir Logs**).

Líneas útiles:

| Línea | Significado |
| :--- | :--- |
| `Security context: integrity=...` | Contexto de seguridad del proceso (debe ser `Medium`) |
| `ENTORNO RESTRINGIDO DETECTADO:` | Windows denegará bandeja y atajos. Incluye el comando para arreglarlo |
| `Keyboard hook verified: it is receiving input` | El teclado se captura correctamente |
| `Keyboard hook is NOT receiving input` | El hook está instalado pero es ciego (integridad Low / AppContainer) |
| `Shell_NotifyIcon(NIM_ADD) FAILED` | Windows rechazó el icono de bandeja |
| `System tray icon is now visible` | El icono se publicó correctamente |
| `Unhandled thread 'X' exception ->` | Excepción en un hilo secundario (con traza completa) |
| `Dictation hotkey triggered` | El atajo de dictado llegó a la aplicación |

> **Privacidad:** por diseño, el log **nunca** registra transcripciones, prompts ni
> vocabulario. Solo latencias, nombres de procesos y códigos de error.

---

## 🧹 Restablecer la configuración

`config.json` y `.env` son de tu propiedad y **no** están versionados. Si algo queda en un
estado raro:

```cmd
copy config.example.json config.json
```

Y vuelve a introducir tu clave de Groq en la ventana de Configuración (se guarda en
`.env`, que también está excluido de Git).

---

## 🐞 Reportar un problema

Antes de abrir un *issue*, adjunta la salida de:

```cmd
diagnostico.bat
```

Es un informe completo (sin datos personales) que permite identificar el problema en
segundos en lugar de a ciegas.
