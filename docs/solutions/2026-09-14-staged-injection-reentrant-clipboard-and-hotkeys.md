# Ficha Técnica: Inyección Escalonada Win32, Cerrojo Reentrante y Atajos Robustos en VoiceFlow-Win

**Fecha:** 2026-09-14  
**Módulo / Repositorio:** `VoiceFlow-Win` (Windows 11 x64)  
**Versión:** `v3.4.1`  
**Autor:** Ricardo García (`rgarcia@telat-group.com`) & Antigravity IDE  

---

## 1. Contexto y Síntomas

Durante las pruebas iniciales de dictado e inyección universal en Windows 11:
1. **Inyección Bloqueada y HUD Atorado:** El HUD flotante se quedaba congelado indefinidamente mostrando *"Escribiendo..."* y no inyectaba texto en editores como Notepad o Antigravity IDE.
2. **Conflicto de Atajo `Win + Space`:** Al pulsar `Win + Space`, Windows 11 desplegaba el menú lateral del selector de idiomas (IME), robando el foco de la ventana activa y haciendo que `Ctrl+V` se enviara al menú del sistema o al vacío. Además, la tecla `Win` física quedaba retenida, interpretándose como `Win+Ctrl+V`.
3. **Disparo Involuntario de Terminal en `Ctrl + Shift + Space`:** Al ejecutar la reescritura contextual con `Ctrl + Shift + Space`, Windows abría una ventana externa de terminal `cmd.exe` en lugar de capturar el texto seleccionado.
4. **Activación de Micrófono con Barra Espaciadora Sola:** Tras iniciar la app con el atajo `win+space`, presionar la barra espaciadora **sola** durante la escritura normal volvía a activar el micrófono.
5. **Disonancia en Notificaciones:** El pop-up de bienvenida de Windows mostraba un atajo estático desactualizado que no coincidía con el atajo configurado en `config.json`.

---

## 2. Causa Raíz

1. **Deadlock Fatal en Cerrojo de Portapapeles:** En `app/platform/injector.py`, `_clipboard_lock` era un `threading.Lock()` estándar. Cuando una llamada a `set_clipboard_text` fallaba, el bloque de recuperación `except` invocaba a `emergency_restore()`, el cual también solicitaba `_clipboard_lock`. Al no ser reentrante, el hilo `AudioWorker` se auto-bloqueaba eternamente, impidiendo que el flujo alcanzara `self.hud.hide()`.
2. **Falta de Liberación Sintética de Modificadores:** Al enviar `SendInput` para `Ctrl+V` o `Ctrl+C`, si los dedos del usuario retenían físicamente `Win`, `Alt` o `Shift`, el sistema operativo combinaba las señales (ej. `Shift + Ctrl + C` = Abrir Terminal Nativa en VS Code).
3. **Omisión de la Tecla Windows en `ParsedHotkey`:** `parse_hotkey_string` solo validaba `ctrl`, `alt` y `shift`. Al parsear `win+space`, el token `win` fue ignorado, registrando `ctrl=False, alt=False, shift=False, win=False, key="space"`. Por lo tanto, presionar la barra espaciadora sola cumplía la condición y activaba el micrófono.
4. **Cadena Estática en Toast:** `app/ui/tray.py` contenía un string hardcodeado en la notificación toast de Windows.

---

## 3. Solución Implementada

1. **Cerrojo Reentrante y Recuperación Segura:**
   * Migración de `_clipboard_lock` a `threading.RLock()`.
   * Envoltura de los hilos de trabajo con bloques `try...except...finally` de nivel superior.
   * Inclusión de un watchdog automático en el HUD que fuerza su desvanecimiento si pasa más de 4.0 segundos en estado `INJECTING`.
2. **Inyección Escalonada y `release_modifiers()`:**
   * Implementación de `release_modifiers()` que fuerza la liberación sintética de `Win`, `Alt`, `Shift` y `Ctrl` antes de emitir combinaciones.
   * `send_ctrl_v()` y `send_ctrl_c()` se dividieron en 3 fases secuenciales con pausas de 15 ms para dar tiempo a la cola de mensajes de Windows.
3. **Soporte Completo de la Tecla Windows en `hotkey.py`:**
   * Se agregó el campo `win: bool` en `ParsedHotkey`, soporte de tokens (`win`, `windows`, `cmd`, `super`) en `parse_hotkey_string`, y normalización de `Key.cmd_l` y `Key.cmd_r` en `_normalize_key`.
4. **Notificaciones y UI Reactivas Dinámicas:**
   * El pop-up de Windows toast y el tooltip de la bandeja toman `{self.hotkey_dictation}` dinámicamente.
   * La barra de estado inferior en la ventana de configuración cuenta con un listener `trace_add` que actualiza la leyenda en tiempo real.
5. **Limpieza Automática en `run.bat`:**
   * `run.bat` ahora detiene cualquier instancia previa de `.venv` antes de arrancar, previniendo choques con el Win32 Named Mutex.

---

## 4. Anti-Patrones & Prohibiciones

* **PROHIBIDO** usar `threading.Lock()` no reentrante para recursos que se liberan dentro de bloques `except` o rutinas de rescate (`emergency_restore`). Usa siempre `threading.RLock()`.
* **PROHIBIDO** sintetizar combinaciones de teclado con `SendInput` (`Ctrl+C` o `Ctrl+V`) sin antes liberar explícitamente los modificadores del usuario (`Shift`, `Alt`, `Win`).
* **PROHIBIDO** omitir la tecla de Windows en parsers de atajos de teclado para Windows 10/11.
* **PROHIBIDO** colocar constantes literales de atajos en toasts o labels cuando la aplicación soporta atajos configurables.

---

## 5. Verificación & Evidencia

* **Pruebas Unitarias:** 24 pruebas automáticas pasando al 100% (`pytest -v`).
* **Calidad de Código:** Linting limpio sin advertencias (`ruff check`).
* **Validación en Caliente:** El usuario dictó mensajes extensos directamente en el chat de Antigravity IDE con `Win + Space`, utilizó `Ctrl + Shift + Space` para corregir texto crudo seleccionado, y corroboró que la barra de espacio convencional no activa el micrófono.
