# PENDIENTES — MorocoVoice

> **Historial de Auditorías Independientes:**
> - 📄 **Auditoría Base v1.0.0:** [`docs/MOROCOVOICE_AUDIT_v1.0.0.md`](./MOROCOVOICE_AUDIT_v1.0.0.md) · Calificación inicial: **4.5 / 10**
> - 📄 **Auditoría Verificada v1.0.1:** [`docs/MOROCOVOICE_AUDIT_v1.0.1.md`](./MOROCOVOICE_AUDIT_v1.0.1.md) · Calificación auditada: **7.5 / 10**
> - 📄 **Auditoría Maestra v1.0.2:** [`docs/MOROCOVOICE_AUDIT_v1.0.2.md`](./MOROCOVOICE_AUDIT_v1.0.2.md) · Calificación auditada: **8.4 / 10** (CONDICIONADO)
> - 📄 **Auditoría Final v1.0.3:** [`docs/MOROCOVOICE_AUDIT_v1.0.3.md`](./MOROCOVOICE_AUDIT_v1.0.3.md) · Calificación auditada: **9.3 / 10** — **✅ APROBADO PARA PRODUCCIÓN GENERAL**

---

## 🟢 1. HITOS DE HARDENING Y AUDITORÍA ALCANZADOS (v1.0.4)

> 💡 **Validación Rápida con 1 Clic en Obsidian:** Haz clic directamente sobre la casilla `[x]` para consultar los ítems consolidados en producción.

- [x] **[REDISEÑO Y OPTIMIZACIÓN DEL MODAL DE CONFIGURACIÓN]** Resuelto el problema de botones cortados/apachurrados en el footer. Invertido el orden de empaque en Tkinter asegurando prioridad de anclaje para la barra de acciones inferior, ampliada la geometría a 640x750 (con soporte de redimensionamiento libre `minsize 600x700`), aplicado espaciado vertical armónico y estilizado en modo oscuro nativo para selectores Combobox. *(Resuelto v1.0.4)*
- [x] **[P0 RESTAURACIÓN DE REFINAMIENTO SEMÁNTICO & MODELO GROQ]** Detectado error 404 por descomisión de `llama-3.1-8b-instant` en Groq. Migrado a `qwen/qwen3.8-27b` como modelo primario e implementada lista de contingencia multi-modelo (`qwen3.8-27b`, `compound-mini`, `qwen3.6-27b`) con limpieza de etiquetas `<think>`, restaurando puntuación, mayúsculas y signos de interrogación `¿...?`. *(Resuelto v1.0.4)*
- [x] **[P0 RESTAURACIÓN DE DICTADO POR VOZ]** Eliminada la compuerta destructiva en `toggle_dictation` que descartaba erróneamente el audio antes de Whisper STT. Las grabaciones explícitas del usuario son despachadas incondicionalmente al motor de transcripción, permitiendo el dictado fluido. *(Resuelto v1.0.4)*
- [x] **[ALINEACIÓN MATEMÁTICA SILERO VAD v5]** Implementada la concatenación recurrente de 64 muestras de contexto en `app/audio/vad.py` (`(1, 576)` muestras totales en 16kHz) con actualización por ventana móvil, evitando atenuación de probabilidades en inferencia ONNX. *(Resuelto v1.0.4)*
- [x] **[MUTEX ROBUSTO & LIBERACIÓN EN CALIENTE]** Validación estricta de `handle` nulo en creación de Win32 Named Mutex (`app/main.py`), y liberación explícita de `old_engine` en `reload_config` para prevenir retención de RAM. *(Resuelto v1.0.4)*
- [x] **[BARRIDO TOTAL DE RESIDUOS COSMÉTICOS]**:
  - `verify_install.py:148`: Actualizado a `MorocoVoice Hardware & Environment Diagnostics`. *(Resuelto v1.0.4)*
  - `.gitignore`: Saneados comentarios y eliminados patrones muertos de log. *(Resuelto v1.0.4)*
  - `logging_setup.py:123`: Corregido docstring a `morocovoice.log`. *(Resuelto v1.0.4)*
  - `contracts.py`: Excepciones heredando de `MorocoVoiceException` con alias de compatibilidad. *(Resuelto v1.0.4)*
  - 14 docstrings de módulo unificados a `MorocoVoice`. *(Resuelto v1.0.4)*
- [x] **[APROBACIÓN FORMAL PARA PRODUCCIÓN GENERAL]** DeepSeek Harness emitió el veredicto definitivo de aprobación masiva con 9.3/10 ponderado y 9.5/10 en Funcionalidad Core y Seguridad. *(Certificado v1.0.3)*
- [x] **[UNIFICACIÓN DE VERSIONES VISIBLES]** Sincronizada la versión de forma homogénea en `tray.py`, `settings_window.py`, `run.bat`, `pyproject.toml`, `README.md` y `verify_install.py`. *(Resuelto v1.0.3/v1.0.4)*
- [x] **[FILTRO PII MULTIPATRÓN & PRUEBA REALISTA]** `PIISafeFilter` en `logging_setup.py` detecta prefijos de fuga real (`adjusted text:`, `transcription:`, etc.). En `test_audio.py` se validó empíricamente contra frases confidenciales reales (7/7 fugas redactadas, 0/7 falsos positivos). *(Resuelto v1.0.3)*
- [x] **[TKINTER THREAD-SAFETY EN HUD]** Invocación de `hud.hide()` enrutada mediante `self.root.after(0, self.hud.hide)` al descartar audios sin habla. *(Resuelto v1.0.3)*
- [x] **[GROQ PING NO BLOQUEANTE (`max_retries=0`)]** `verify_groq_api_key_online` configurado con `max_retries=0` (espera máxima de 2.5s). Códigos transitorios (429, 500, 503) tratados como avisos no bloqueantes. *(Resuelto v1.0.3)*
- [x] **[AISLAMIENTO DEL PORTAPAPELES EN PYTEST]** `test_clipboard_roundtrip` respalda y restaura el portapapeles del host. Aserciones reales en lugar de `assert True`. *(Resuelto v1.0.3)*
- [x] **[DECISIONES EXPLÍCITAS DE RICARDO GARCÍA RATIFICADAS]**:
  - `Win + Space` conservado como atajo principal de dictado.
  - Portapapeles (`CF_UNICODETEXT`) conservado con `Ctrl+V` y guardado en historial de Windows (`Win + V`).
  - Documentado con 100% de transparencia en `README.md`.

---

## 🟡 2. BACKLOG FUTURO (v1.1.0 / v1.2.0 — No bloqueante)

### 2A · Cobertura Adicional
- [ ] **Pruebas de cobertura para prefijos PII:** Formalizar pruebas unitarias adicionales para casos 429/500 en `test_settings.py`.

### 2B · Arquitectura y Rendimiento
- [ ] **Aceleración CUDA Opcional:** Permitir selección de GPU NVIDIA en `LocalWhisperEngine` cuando `ctranslate2` detecte hardware compatible con cuDNN.

### 2C · UX Avanzada
- [ ] **Selector de Dispositivo de Audio en Ajustes:** Permitir elegir el micrófono deseado en lugar del predeterminado de Windows.
