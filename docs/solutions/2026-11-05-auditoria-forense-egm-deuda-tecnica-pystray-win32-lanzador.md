# Auditoría forense EGM y resolución de deuda técnica profunda en MorocoVoice

Ficha de ingeniería sobre la investigación forense bajo el modelo elefante-pez dorado (EGM), corrección de intercepción Win32 en pystray, barra de título oscura nativa DWM y blindaje del lanzador de producción.

---

## 1. Contexto y diagnóstico forense EGM (Elephant-Goldfish Model)

El modelo elefante-pez dorado (EGM) distingue dos posturas técnicas ante fallos en producción:
- **Enfoque pez dorado (reactivo / horizonte corto):** Responde a síntomas aislados ("el botón no guarda", "no veo el icono") con parches cosméticos rápidos en una sola línea, sin auditar las dependencias cruzadas, la arquitectura de procesos en Windows, ni las suposiciones tácitas del sistema.
- **Enfoque elefante (gobernanza sistémica y memoria profunda):** Traza los síntomas a sus causas raíz a través de todo el ciclo de vida del sistema, cuestiona qué más está roto o es frágil aunque el usuario aún no lo haya reportado, y resuelve la deuda técnica estructural para garantizar estabilidad duradera en producción.

Durante esta sesión se identificaron cuatro brechas críticas de deuda técnica que impedían el funcionamiento perfecto del sistema en el entorno de Ricardo García:

```
+----------------------------------------------------------------------------------------------------+
|                                    AUDITORÍA FORENSE EGM                                           |
+------------------------------------+-----------------------------------+---------------------------+
| Dominio                            | Causa raíz identificada           | Impacto operativo         |
+------------------------------------+-----------------------------------+---------------------------+
| Intercepción de doble clic bandeja | `pystray._util.win32` sin clase   | El parche de doble clic   |
|                                    | `Icon`. La clase reside en        | fallaba silenciosamente   |
|                                    | `pystray._win32`.                 | con AttributeError.       |
|                                    |                                   |                           |
| Estética de ventana y UI Spotify   | Falta de `DwmSetWindowAttribute`  | Ventana con cuerpo oscuro |
|                                    | con `DWMWA_USE_IMMERSIVE_DARK_    | pero barra de título      |
|                                    | MODE` en el HWND raíz.            | blanco/gris Windows 95.   |
|                                    |                                   |                           |
| Lanzador de producción (run.bat)   | Arranque ciego con `pythonw.exe`  | Si Python fallaba al      |
|                                    | sin verificación de vida          | arrancar, la consola se   |
|                                    | post-lanzamiento.                 | cerraba sin dejar rastro. |
|                                    |                                   |                           |
| Aislamiento de sesiones/escritorios| Procesos lanzados desde sandbox   | Confusión entre ejecución |
|                                    | CLI corren en `Desktop: exebox-*` | en entorno CLI y bandeja  |
|                                    | donde no existe taskbar explorer. | del escritorio interactivo|
+------------------------------------+-----------------------------------+---------------------------+
```

---

## 2. Anatomía de las causas raíz y soluciones implementadas

### 2.1. El fallo de intercepción de doble clic en `pystray`
- **Diagnóstico:** En la implementación previa, se intentó parchear `Icon._on_notify` importando `from pystray._util import win32 as pystray_win32`. Sin embargo, en la arquitectura de `pystray`, `_util.win32` es un módulo puramente C-types con constantes de Win32, mientras que la clase `Icon` vive en `pystray._win32`. El llamado `getattr(pystray_win32.Icon, ...)` generaba un `AttributeError` capturado por el bloque defensivo `try/except`, impidiendo que el parche se aplicara. Además, se intentaba leer `pystray_win32.win32.WM_RBUTTONUP`, lo que habría quebrado el menú de clic derecho.
- **Solución implementada:** Se corrigió el destino del mono-parche a `pystray._win32.Icon._on_notify`, enrutando tanto `WM_LBUTTONUP` (0x0202) como `WM_LBUTTONDBLCLK` (0x0203) a la acción predeterminada (`self_icon()`), y delegando limpiamente cualquier otro mensaje al método original sin alterar el menú contextual. Se agregó además un antirrebote de 350 ms en `_on_settings_clicked` para evitar que la combinación rápida de eventos genere ventanas superpuestas.

### 2.2. Barra de título oscura nativa DWM en Windows 11/10
- **Diagnóstico:** Aunque la ventana de configuración contaba con la paleta oscura estilo Spotify (`#121212`, `#181818`), el marco de la ventana superior (la barra de título del sistema operativo) continuaba pintándose de color gris claro o blanco, dando una apariencia anticuada tipo años 90.
- **Solución implementada:** Se integró la función `_apply_dark_title_bar` que obtiene el HWND canónico de Windows mediante `ctypes.windll.user32.GetAncestor(window.winfo_id(), 2)` (donde `GA_ROOT = 2`), e invoca la API Desktop Window Manager (`DwmSetWindowAttribute`) con el atributo `DWMWA_USE_IMMERSIVE_DARK_MODE = 20` (con respaldo a `19` para versiones anteriores de Windows 10). Se asignó además el icono oficial `morocovoice.ico` a la barra de título mediante `iconbitmap`.

### 2.3. Blindaje y verificación de salud en el lanzador (`run.bat`)
- **Diagnóstico:** `run.bat` ejecutaba `start "" pythonw.exe -m app.main` y de inmediato finalizaba con `exit /b 0`. Como `pythonw.exe` suprime toda salida estándar y de error, cualquier fallo durante los primeros milisegundos de arranque (como una excepción de importación o un error de librerías) cerraba el proceso de forma invisible, dejando al usuario convencido de que la aplicación no arrancaba.
- **Solución implementada:**
  1. Se priorizó Python 3.13 (`py -3.13`) sobre versiones legacy.
  2. Se añadió la creación automática del acceso directo en la carpeta de inicio de Windows (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Moroco Voice.lnk`) para que la aplicación sobreviva a reinicios del sistema.
  3. Se implementó una verificación activa tras 1.5 segundos de arranque mediante `Get-CimInstance Win32_Process`. Si el proceso murió prematuramente, el script detiene la ejecución, muestra las últimas 15 líneas de `morocovoice.log` en pantalla y realiza una pausa para que el error sea visible y diagnosticable de inmediato.

### 2.4. Mapeo de teclas de control y códigos de teclado virtual (VK)
- **Diagnóstico:** Al presionar combinaciones como `Ctrl+S`, Windows emite el carácter de control ASCII `\x13`, el cual no coincidía con `"s"`. Asimismo, al usar teclas especiales como Espacio, Tabulador, Enter, Escape, Retroceso o Supr, si el carácter venía vacío, no se resolvían adecuadamente.
- **Solución implementada:** Se incorporó un diccionario maestro `VK_SPECIAL_MAP` en `hotkey.py` (VK 32 -> `"space"`, VK 9 -> `"tab"`, VK 13 -> `"enter"`, VK 27 -> `"esc"`, VK 8 -> `"backspace"`, VK 46 -> `"delete"`), garantizando paridad total entre los atajos capturados y los eventos de teclado físico.

---

## 3. Verificación de calidad y cobertura de pruebas

Se diseñaron y ejecutaron 57 pruebas unitarias exhaustivas en el entorno Python 3.13:
- `test_instrument_pystray_patches_icon_on_notify`: Verifica que el parche sobre `pystray._win32.Icon` se instale correctamente y que `WM_LBUTTONDBLCLK` despache la acción por defecto.
- `test_apply_dark_title_bar_handles_null_safely`: Verifica que la aplicación del modo oscuro en la barra DWM sea resiliente y maneje handles de ventana nulos o mocks sin excepciones.
- `test_virtual_key_special_mappings`: Comprueba la extracción canónica de códigos VK especiales y caracteres de espacio.
- `test_tray_menu_has_settings_as_default_item`: Confirma que la opción de Configuración es el elemento predeterminado en el menú de bandeja.

Resultado de la suite: **57 de 57 pruebas pasaron exitosamente en 6.76 segundos**.
