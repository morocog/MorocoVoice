# Solución: Decodificación de caracteres de control ASCII de Windows en atajos de teclado personalizados

**Fecha:** 2026-11-05  
**Autor:** Ricardo García & Antigravity  
**Repositorio:** `MorocoVoice`  
**Módulos afectados:** `app/platform/hotkey.py`, `tests/test_hotkey.py`  
**Estatus:** Resuelto e integrado en `main` (`8984dae`)

---

## 1. Problema detectado

Al intentar cambiar el atajo global de dictado o reescritura desde la ventana visual de configuración (por ejemplo a `ctrl+s`, `ctrl+h` o combinaciones con letras y modificador `Ctrl`):
1. La interfaz persistía correctamente el nuevo valor en `config.json` y el sistema ejecutaba el hot-reload en tiempo de ejecución (`reload_config`).
2. Sin embargo, al pulsar la combinación en el teclado, el sistema ignoraba la pulsación y no iniciaba la grabación ni la reescritura.

---

## 2. Causa raíz

En el sistema operativo Windows, el hook de bajo nivel de teclado (`WH_KEYBOARD_LL`) a través de la librería `pynput` procesa las teclas cuando la tecla `Ctrl` está presionada de una manera particular:
* El campo `event.char` de `KeyCode` **no** contiene el carácter alfabético legible (`"s"`, `"h"`, `"a"`), sino su correspondiente **código de control ASCII** (1 a 26):
  * `Ctrl + A` ➔ `\x01` (SOH)
  * `Ctrl + H` ➔ `\x08` (BS / Backspace)
  * `Ctrl + S` ➔ `\x13` (DC3 / Device Control 3)
  * `Ctrl + Z` ➔ `\x1a` (SUB)
* En `app/platform/hotkey.py`, el método `matches()` realizaba una comparación directa de cadenas:
  ```python
  pressed_name = (pressed_key.char or "").lower()
  return pressed_name == self.key_name.lower()
  ```
  Al comparar `"\x13" == "s"` o `"\x08" == "h"`, la condición evaluaba a `False`. Por lo tanto, aunque la configuración se guardara y recargara exitosamente, el listener descartaba silenciosamente todas las combinaciones de `Ctrl + <letra>`.
* Además, si `char` venía nulo (`None`) como sucede con teclas de función (`F1`–`F12`) o teclado numérico bajo ciertos modificadores, no se consultaba el código virtual de hardware (`vk`).

---

## 3. Solución implementada

1. **Extracción y normalización canónica de caracteres (`extract_key_name`):**
   * Se implementó la función `extract_key_name(key)` que decodifica caracteres de control ASCII (`1 <= ord(c) <= 26`) devolviendo el carácter alfabético original mediante `chr(ord(c) + 96)`.
   * Se incorporó resolución por `key.vk` para letras (`65-90`), números (`48-57`), teclado numérico (`96-105`) y teclas de función (`112-123` ➔ `f1`-`f12`).
2. **Resiliencia en detección de modificadores:**
   * Se actualizó la verificación de `Ctrl`, `Alt`, `Shift` y `Win` en `matches()` para comprobar cualquiera de las variantes izquierda (`_l`), derecha (`_r`), AltGr (`_gr`) o canónica.
3. **Limpieza de códigos virtuales en liberación de teclas (`_on_release`):**
   * Se asegura la remoción de cualquier instancia en `_current_keys` que comparta el mismo `vk` para evitar estados atascados.
4. **Soporte para alias en español:**
   * Mapeo de `espacio`, `barra`, `intro`, `escape` a sus identificadores estándar de teclado.
5. **Pruebas unitarias:**
   * Se agregaron pruebas en `tests/test_hotkey.py` simulando la emisión de códigos de control ASCII de Windows (`\x13`, `\x08`) y la verificación con `HotkeyListener` en vivo.
