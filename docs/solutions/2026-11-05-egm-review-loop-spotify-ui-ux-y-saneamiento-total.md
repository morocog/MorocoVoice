---
title: "Rediseño UI/UX estilo Spotify Desktop, HUD dinámico con soporte DPI y saneamiento integral bajo EGM Review Loop"
date: "2026-11-05"
category: "ui-ux-architecture-hardening"
tags:
  - tkinter
  - spotify-ui
  - win32-dpi
  - hotkey-capture
  - egm-review-loop
  - technical-debt
severity: "high"
component: "app/ui/settings_window.py, app/ui/hud.py, app/main.py, app/config.py"
---

# Rediseño UI/UX estilo Spotify Desktop, HUD dinámico con soporte DPI y saneamiento integral bajo EGM Review Loop

## 1. Contexto y síntomas detectados

Durante la validación visual y la auditoría multiagente con el protocolo **Elephant-Goldfish Model (`/egm-review-loop`)** sobre **MorocoVoice v1.0.5**, se identificaron defectos visuales y de lógica interactiva:

1. **Truncamiento en la cápsula flotante (HUD) al iniciar:** El banner de inicio mostraba `• rocoVoice Activo (ctrl+shift·` porque `FloatingHUD` utilizaba un ancho estático (`width = 240` px) insuficiente para cadenas de más de 25 caracteres o escalas DPI de 125%–200%.
2. **Botones cuadrados y recorte de controles en la tarjeta de atajos:** En `SettingsModal`, los botones nativos `tk.Button` carecían de geometría redondeada estilo Spotify y la fila de atajos apilaba etiqueta, entrada, chips y botón `Capturar` en una sola línea horizontal, recortando el botón a `"t"` en el borde derecho.
3. **Fallo crítico al capturar la tecla Windows (`Win + Space`) en Tkinter:** El manejador `on_key` de `Capturar` leía únicamente las máscaras de bits de `event.state` (`0x4` Ctrl, `0x1` Shift, `0x8`/`0x20000` Alt). En Windows, Tkinter no activa ningún bit en `event.state` para `Win_L`/`Win_R`, por lo que pulsar `Win + Space` ignoraba el modificador `Win` y guardaba únicamente `"space"`, secuestrando la barra espaciadora.
4. **Sobreescritura forzada de modo `LOCAL` a `CLOUD`:** En `_on_save()`, una condición convertía cualquier selección explícita de `LOCAL` nuevamente a `CLOUD` siempre que existiera una clave válida en `.env`, impidiendo usar el modo sin conexión desde la interfaz.
5. **Condición de carrera en temporizadores del HUD y sobreescritura de alerta de seguridad:** `app/main.py` programaba 10 llamadas `self.root.after(2000, self.hud.hide)` no rastreadas fuera de `hud._auto_dismiss_timer`, y `start()` sobrescribía inmediatamente la alerta roja de integridad `Low` con el mensaje verde de bienvenida.
6. **Control obsoleto en la interfaz (`Retardo Pegado`) y referencias residuales a atajos retirados:** La fila `Retardo Pegado` modificaba un parámetro inactivo tras desactivar la restauración automática del portapapeles (`restore_clipboard=False`), y aún existían menciones residuales a `Ctrl + Alt + S` y `Ctrl + Shift + D` en `README.md` y `docs/TROUBLESHOOTING.md`.

## 2. Causa raíz

- **Geometría estática en Tkinter:** `FloatingHUD` no medía el texto con `tkfont.Font(root=self.root).measure(text)` ni `metrics("linespace")` antes de posicionar la ventana.
- **Limitación de `event.state` en Tcl/Tk sobre Win32:** Tcl/Tk en Windows mapea `VK_CONTROL`, `VK_SHIFT` y `VK_MENU` en `event.state`, pero omite `VK_LWIN` (`0x5B`) y `VK_RWIN` (`0x5C`).
- **Acoplamiento y duplicación de validadores:** `settings_window.py` duplicaba funciones de `app/config.py` y `app/engine/engine_manager.py`, además de mantener `attributes("-topmost", True)` de forma permanente cubriendo ventanas externas abiertas desde el propio modal.

## 3. Solución implementada

1. **Componente `PillButton` en Canvas y diseño de 2 niveles para atajos (`app/ui/settings_window.py`):**
   - Creación de `PillButton(tk.Canvas)` con cápsulas geométricas redondeadas (`create_arc` + `create_rectangle`), soporte completo de teclado (`takefocus=1`, `<Return>`, `<space>`, `<FocusIn>`/`<FocusOut>`), activación en `<ButtonRelease-1>` y medición de texto consciente de DPI.
   - Separación de cada fila de atajo en dos niveles: encabezado descriptivo superior y barra inferior con chips de teclas a la izquierda y entrada + botón `Capturar` a la derecha, eliminando cualquier recorte.
2. **Captura confiable de tecla Windows y prevención de colisiones (`resolve_captured_hotkey_event`):**
   - Implementación de `resolve_captured_hotkey_event(event, held_mods)` combinando el seguimiento de `<KeyPress>`/`<KeyRelease>` de modificadores con consulta directa a hardware vía `ctypes.windll.user32.GetAsyncKeyState(0x5B / 0x5C)`.
   - Cancelación automática de capturas previas al cambiar de fila, pestaña o cerrar el modal (`_cancel_active_capture`), y validación en `_on_save()` que impide asignar el mismo atajo a Dictado y Reescritura.
3. **Respeto al modo `LOCAL` y preservación de ediciones abiertas:**
   - Registro de `self._had_valid_key_on_open` al abrir el modal para que la promoción automática `LOCAL → CLOUD` ocurra únicamente durante el alta inicial de la clave y jamás sobrescriba la elección manual del usuario.
   - Comprobación de `self.window.winfo_exists()` al inicio de `show()` para enfocar la ventana existente sin borrar cambios no guardados, y pulso temporal de `-topmost` (250 ms) para no tapar el navegador ni el Bloc de notas.
4. **HUD dinámico y temporizador único cancelable (`app/ui/hud.py` y `app/main.py`):**
   - Cálculo dinámico `self.width = max(260, text_width + 88)` y `self.height = max(44, linespace + 26)`.
   - Incorporación de `duration_ms` en `FloatingHUD.show()` y `_dispatch_hud()`, eliminando todos los `self.root.after(..., self.hud.hide)` huérfanos en `app/main.py` y respetando la alerta de entorno restringido cuando `_check_security_context()` devuelve `False`.

## 4. Verificación

- Suite completa de pruebas unitarias ampliada a **63 pruebas** (`.\.venv\Scripts\python -m pytest tests -v`), todas en verde (`63 passed`), incluyendo pruebas específicas para `resolve_captured_hotkey_event` con `Win + Space`, preservación de modo `LOCAL`, rechazo de atajos duplicados, `PillButton` y dimensionamiento dinámico del HUD.
