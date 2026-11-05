# Ficha de Solución: Doble Clic en Bandeja de Tareas (Pystray Win32), Rediseño Spotify y Eliminación de Deuda Técnica

## 1. Contexto y Problema

Durante el uso operativo continuo de **MorocoVoice** en Windows 11, se identificaron tres fuentes críticas de fricción y deuda técnica:
1. **Inoperancia del doble clic en el icono de la bandeja del sistema:** Al hacer doble clic sobre el icono de MorocoVoice en la barra de tareas, no se abría la ventana de configuración. El usuario se veía obligado a abrir el menú contextual con clic derecho.
2. **Estética anticuada de interfaz ("parece de los 90s"):** El modal de configuración mostraba controles con aspecto clásico de Windows (comboboxes blancos/grises sin tema oscuro integrado, campos de texto sin estilo nativo para atajos de teclado, barras de scroll anticuadas y ausencia de previsualización visual de teclas).
3. **Persistencia de atajos secundarios no deseados:** Atajos no solicitados (`hotkey_settings`, `hotkey_diagnostics`) continuaban apareciendo con valores predeterminados en contratos y clases del sistema a pesar de la directiva de conservar exclusivamente dos atajos esenciales: **Dictado Inteligente** y **Reescritura Contextual**.

---

## 2. Causas Raíz

1. **Gestión de eventos en Pystray Win32:**
   - La implementación nativa de `pystray._win32.Icon._on_notify` solo evaluaba `lparam == win32.WM_LBUTTONUP` (0x0202). El mensaje de doble clic nativo de Windows (`WM_LBUTTONDBLCLK` = 0x0203) era completamente descartado.
   - Adicionalmente, el elemento del menú `⚙️ Configuración...` carecía del flag `default=True`. En Pystray, cuando un icono recibe clic o doble clic, despacha `self()`, el cual busca el primer elemento con `item.default == True`. Al no existir ninguno, la acción resultaba en un no-op silencioso (`StopIteration`).
2. **Renderizado de Tkinter TTK en Windows 10/11:**
   - Por omisión, `ttk.Combobox` utiliza el tema nativo del sistema (`vista` o `winnative`), el cual ignora los fondos oscuros del contenedor padre e inserta flechas y listas desplegables con fondo blanco brillante.
   - Los campos de texto de atajos requerían que el usuario escribiera manualmente cadenas como `ctrl+shift+h` en lugar de mostrar chips visuales de teclas (badges estilo macOS/Linear/Spotify) o contar con un botón interactivo de captura por pulsación.
3. **Deuda de contratos y valores por omisión:**
   - `AppConfig` y `HotkeyListener` mantenían firmas de inicialización con cadenas como `"ctrl+alt+s"` y `"ctrl+shift+d"`, reinyectando atajos no deseados si el archivo de configuración omitía esas llaves.

---

## 3. Solución Implementada

### A. Instrumentación de Pystray Win32 para Doble Clic
En `app/ui/tray.py`:
1. Se extendió la función `_instrument_pystray()` para interceptar el despachador de notificaciones Win32:
   ```python
   WM_LBUTTONUP = 0x0202
   WM_LBUTTONDBLCLK = 0x0203

   orig_on_notify = getattr(pystray_win32.Icon, "_on_notify", None)
   if orig_on_notify:
       def _patched_on_notify(self_icon, wparam, lparam):
           if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
               self_icon()
           elif self_icon._menu_handle and lparam == pystray_win32.win32.WM_RBUTTONUP:
               orig_on_notify(self_icon, wparam, lparam)
           else:
               orig_on_notify(self_icon, wparam, lparam)

       pystray_win32.Icon._on_notify = _patched_on_notify
   ```
2. Se asignó `default=True` al elemento `⚙️ Configuración...`:
   ```python
   pystray.MenuItem("⚙️ Configuración...", self._on_settings_clicked, default=True)
   ```
   Esto garantiza que Windows resalte el elemento en negrita (`MFS_DEFAULT`) en el menú contextual y que Pystray ejecute `_on_settings_clicked` de forma instantánea al detectar el doble clic.

### B. Rediseño Completo de UI/UX a Estándar Spotify Premium
En `app/ui/settings_window.py`:
1. **Lienzo amplio de dos columnas (1140 × 740 px):** Distribución balanceada que elimina cualquier barra de desplazamiento en monitores Full HD (1920 × 1080).
2. **Chips visuales Keycap interactivos:** Para cada atajo (`Dictado Inteligente` y `Reescritura Contextual`), el modal dibuja badges individuales (`[ CTRL ]` `+` `[ SHIFT ]` `+` `[ H ]`) sobre fondo `#282828` con borde `#3A3A3A`.
3. **Botón interactivo de captura ("Capturar"):** Permite al usuario hacer clic y simplemente presionar la combinación deseada de teclas; el sistema captura los modificadores y la tecla principal, normaliza la nomenclatura y actualiza tanto la variable como los chips en tiempo real.
4. **Comboboxes oscuros nativos TTK (`clam` theme):** Se configuró el estilo `Dark.TCombobox` y se inyectaron opciones en la base de datos de Tkinter para que las listas desplegables se rendericen en gris oscuro (`#1A1A1A`) con texto blanco y selección en verde Spotify (`#1DB954`).
5. **Transiciones de color en botones (`_bind_hover`):** Efectos suaves al pasar el cursor sobre botones principales, pills de navegación y controles de formulario.
6. **Notificación toast persistente en dock:** Retroalimentación no bloqueante integrada en la barra inferior que confirma el guardado sin recurrir a cuadros de diálogo modales molestos.

### C. Eliminación Estricta de Atajos Secundarios
- En `app/contracts.py`: `hotkey_settings: str = ""` y `hotkey_diagnostics: str = ""`.
- En `app/platform/hotkey.py`: valores por omisión limpios sin combinaciones parásitas.
- En `app/ui/settings_window.py`: el método `_on_save()` persiste exclusivamente los dos atajos principales en `config.json`.

---

## 4. Verificación y Pruebas

1. **Suite de Pruebas Automatizadas:**
   - Se añadieron pruebas unitarias para la generación de chips keycap (`test_render_keycap_chips_generates_chips`) y para la presencia de `default=True` en la bandeja del sistema (`test_tray_menu_has_settings_as_default_item`).
   - Se ejecutó `pytest tests/` con un resultado de **52 pruebas aprobadas al 100% en 6.99 segundos**.
2. **Pruebas de Inicialización y Ciclo de Vida:**
   - Verificación de arranque en frío de `MorocoVoiceApplication`, comprobando el mapeo exclusivo de `Dictation` y `Rewrite` y la correcta suscripción del mutex sin solapamientos.
