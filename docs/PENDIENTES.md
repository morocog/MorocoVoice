# PENDIENTES — MorocoVoice

> **Historial de auditorías independientes:**
> - 📄 **Auditoría base v1.0.0:** [`docs/MOROCOVOICE_AUDIT_v1.0.0.md`](./MOROCOVOICE_AUDIT_v1.0.0.md) · Calificación inicial: **4.5 / 10**
> - 📄 **Auditoría verificada v1.0.1:** [`docs/MOROCOVOICE_AUDIT_v1.0.1.md`](./MOROCOVOICE_AUDIT_v1.0.1.md) · Calificación auditada: **7.5 / 10**
> - 📄 **Auditoría maestra v1.0.2:** [`docs/MOROCOVOICE_AUDIT_v1.0.2.md`](./MOROCOVOICE_AUDIT_v1.0.2.md) · Calificación auditada: **8.4 / 10** (CONDICIONADO)
> - 📄 **Auditoría final v1.0.3:** [`docs/MOROCOVOICE_AUDIT_v1.0.3.md`](./MOROCOVOICE_AUDIT_v1.0.3.md) · Calificación auditada: **9.3 / 10** — **✅ APROBADO PARA PRODUCCIÓN GENERAL**

---

## 🟢 1. Hitos de endurecimiento y auditoría alcanzados (v1.0.4 – v1.0.5)

> 💡 **Validación rápida con 1 clic en Obsidian:** Haz clic directamente sobre la casilla `[x]` para consultar los ítems consolidados en producción.

- [x] **[REDISEÑO SPOTIFY DESKTOP UI/UX & CÁPSULA HUD DINÁMICA]** Rediseñado el centro de control (`app/ui/settings_window.py`) con botones tipo cápsula dibujados en Canvas (`PillButton` con soporte de foco por teclado, bordes redondeados y hover suave), disposición de atajos en dos niveles sin truncamiento de botones ni etiquetas, y cálculo dinámico de ancho y alto con conciencia de DPI en `FloatingHUD` (`app/ui/hud.py`). *(Resuelto v1.0.5)*
- [x] **[CAPTURA DE TECLA WINDOWS (`VK_LWIN`/`VK_RWIN`) & SANEAMIENTO EGM REVIEW LOOP]** Corregido el capturador interactivo de atajos (`resolve_captured_hotkey_event`) para detectar la tecla Windows mediante `GetAsyncKeyState` y seguimiento de modificadores, evitando que `Win + Space` se guardara como solo `space`. Resuelta la sobreescritura forzada `LOCAL -> CLOUD`, eliminado el campo obsoleto de retardo de pegado en la interfaz, unificada la validación de claves en `app/config.py`, y centralizados los temporizadores cancelables del HUD. *(Resuelto v1.0.5)*
- [x] **[REDISEÑO Y OPTIMIZACIÓN DEL MODAL DE CONFIGURACIÓN]** Resuelto el problema de botones cortados/apachurrados en el pie de ventana. Invertido el orden de empaque en Tkinter asegurando prioridad de anclaje para la barra de acciones inferior, ampliada la geometría a 1140x740 en 2 columnas sin barras de desplazamiento innecesarias y estilizado en modo oscuro nativo para selectores Combobox y Scrollbar. *(Resuelto v1.0.4 / v1.0.5)*
- [x] **[P0 RESTAURACIÓN DE REFINAMIENTO SEMÁNTICO & MODELO GROQ]** Detectado error 404 por descomisión de `llama-3.1-8b-instant` en Groq. Migrado a `qwen/qwen3.8-27b` como modelo primario e implementada lista de contingencia multimodelo (`qwen/qwen3.8-27b`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`) con limpieza de etiquetas `<think>`, restaurando puntuación, mayúsculas y signos de interrogación `¿...?`. *(Resuelto v1.0.4 / v1.0.5)*
- [x] **[P0 RESTAURACIÓN DE DICTADO POR VOZ]** Eliminada la compuerta destructiva en `toggle_dictation` que descartaba erróneamente el audio antes de Whisper STT. Las grabaciones explícitas del usuario son despachadas incondicionalmente al motor de transcripción, permitiendo el dictado fluido. *(Resuelto v1.0.4)*
- [x] **[ALINEACIÓN MATEMÁTICA SILERO VAD v5]** Implementada la concatenación recurrente de 64 muestras de contexto en `app/audio/vad.py` (`(1, 576)` muestras totales en 16 kHz) con actualización por ventana móvil, evitando atenuación de probabilidades en inferencia ONNX. *(Resuelto v1.0.4)*
- [x] **[MUTEX ROBUSTO & LIBERACIÓN EN CALIENTE]** Validación estricta de `handle` nulo en creación de Win32 Named Mutex (`app/main.py`), y liberación explícita de `old_engine` en `reload_config` para prevenir retención de RAM. *(Resuelto v1.0.4)*
- [x] **[BARRIDO TOTAL DE RESIDUOS COSMÉTICOS]**:
  - `verify_install.py:148`: Actualizado a `MorocoVoice Hardware & Environment Diagnostics`. *(Resuelto v1.0.4)*
  - `.gitignore`: Saneados comentarios y eliminados patrones muertos de log. *(Resuelto v1.0.4)*
  - `logging_setup.py`: Corregido docstring a `morocovoice.log` sin atajos obsoletos. *(Resuelto v1.0.5)*
  - `contracts.py`: Excepciones heredando de `MorocoVoiceException` con alias de compatibilidad. *(Resuelto v1.0.4)*
  - 14 docstrings de módulo unificados a `MorocoVoice`. *(Resuelto v1.0.4)*
- [x] **[APROBACIÓN FORMAL PARA PRODUCCIÓN GENERAL]** DeepSeek Harness emitió el veredicto definitivo de aprobación masiva con 9.3/10 ponderado y 9.5/10 en Funcionalidad Core y Seguridad. *(Certificado v1.0.3)*
- [x] **[UNIFICACIÓN DE VERSIONES VISIBLES]** Sincronizada la versión dinámicamente desde `app.__version__` en `tray.py`, `settings_window.py`, `run.bat`, `pyproject.toml`, `README.md` y `verify_install.py`. *(Resuelto v1.0.3 – v1.0.5)*
- [x] **[FILTRO PII MULTIPATRÓN & PRUEBA REALISTA]** `PIISafeFilter` en `logging_setup.py` detecta prefijos de fuga real (`adjusted text:`, `transcription:`, etc.). En `test_audio.py` se validó empíricamente contra frases confidenciales reales (7/7 fugas redactadas, 0/7 falsos positivos). *(Resuelto v1.0.3)*
- [x] **[TKINTER THREAD-SAFETY EN HUD]** Invocación de `hud.hide()` y `hud.show(..., duration_ms=...)` enrutadas mediante `self.root.after` con un único temporizador cancelable `_auto_dismiss_timer`. *(Resuelto v1.0.5)*
- [x] **[GROQ PING NO BLOQUEANTE (`max_retries=0`)]** `verify_groq_api_key_online` configurado con `max_retries=0` (espera máxima de 2.5 s) y validado con pruebas unitarias para códigos 200, 401 y 429. *(Resuelto v1.0.3 – v1.0.5)*
- [x] **[AISLAMIENTO DEL PORTAPAPELES EN PYTEST]** `test_clipboard_roundtrip` respalda y restaura el portapapeles del host. Aserciones reales en lugar de `assert True`. *(Resuelto v1.0.3)*
- [x] **[DECISIONES EXPLÍCITAS DE RICARDO GARCÍA RATIFICADAS]**:
  - `Win + Space` conservado como atajo principal de dictado.
  - Portapapeles (`CF_UNICODETEXT`) conservado con `Ctrl + V` y guardado en historial de Windows (`Win + V`).
  - Documentado con 100% de transparencia en `README.md` y `docs/TROUBLESHOOTING.md`.
- [x] **[PORTAPAPELES PERMANENTE & BLINDAJE WIN+V]** Se desactivó la restauración automática del portapapeles en `inject_text` (`restore_clipboard=False`). El texto transcrito o refinado ahora permanece en el portapapeles para evitar pérdidas si el foco de texto no estaba activo al hablar. Se blindó `set_clipboard_text` para ignorar cadenas vacías, eliminando al 100% las entradas en blanco en el historial de `Win + V`. *(Resuelto v1.0.5)*
- [x] **[DEPURACIÓN DE ATAJOS CANÓNICOS]** Eliminadas referencias espurias a `hotkey_diagnostics` (`Ctrl+Shift+D`) y `hotkey_settings` (`Ctrl+Alt+S`) en código, UI y documentación. Únicamente se conservan y mapean los 2 atajos oficiales: dictado (`Win + Space`) y reescritura (`Ctrl + Shift + Space`). *(Resuelto v1.0.5)*
- [x] **[CORRECCIÓN DE INSTALADOR RUN.BAT & SYS.PATH]** Corregido error de sintaxis en Batch por paréntesis anidados en comprobación de Python (`sys.hexversion >= 0x030B0000`) e inyectada la raíz del proyecto a `sys.path` en `app/main.py`. *(Resuelto v1.0.5)*
- [x] **[MODELOS GROQ ACTIVOS]** Actualizados fallbacks de Groq LLM a `openai/gpt-oss-120b` y `openai/gpt-oss-20b`, evitando errores 404. *(Resuelto v1.0.5)*

---

## 🟡 2. Backlog futuro (v1.1.0 / v1.2.0 — No bloqueante)

### 2A · Arquitectura y rendimiento
- [ ] **Aceleración CUDA opcional:** Permitir selección de GPU NVIDIA en `LocalWhisperEngine` cuando `ctranslate2` detecte hardware compatible con cuDNN.

### 2B · UX avanzada
- [ ] **Selector de dispositivo de audio en ajustes:** Permitir elegir el micrófono deseado en lugar del predeterminado de Windows.

### 2C · Compatibilidad Windows 11 NotifyIconSettings & versión de Python
- [ ] **Alineación de Python 3.12 vs 3.13 en bandeja de Windows 11:** En Windows 11, `Shell_NotifyIcon(NIM_ADD)` puede requerir promoción manual en `HKCU\Control Panel\NotifyIconSettings` cuando cambia la ruta del ejecutable `pythonw.exe`.
