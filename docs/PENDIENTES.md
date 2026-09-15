# PENDIENTES — MorocoVoice

> **Historial de Auditorías Independientes:**
> - 📄 **Auditoría Base v1.0.0:** [`docs/MOROCOVOICE_AUDIT_v1.0.0.md`](./MOROCOVOICE_AUDIT_v1.0.0.md) · Calificación inicial: **4.5 / 10**
> - 📄 **Auditoría Verificada v1.0.1:** [`docs/MOROCOVOICE_AUDIT_v1.0.1.md`](./MOROCOVOICE_AUDIT_v1.0.1.md) · Calificación auditada: **7.5 / 10**
> - 📄 **Auditoría Maestra v1.0.2:** [`docs/MOROCOVOICE_AUDIT_v1.0.2.md`](./MOROCOVOICE_AUDIT_v1.0.2.md) · Calificación auditada por DSH: **8.4 / 10** (Funcionalidad Core: **9.5 / 10**)
> - 📄 **Hardening & Unificación v1.0.3:** Calificación objetivo: **9.6+ / 10**

---

## 🟢 1. HALLAZGOS AUDITORÍA v1.0.2 RESUELTOS EN v1.0.3

> 💡 **Validación Rápida con 1 Clic en Obsidian:** Haz clic directamente sobre la casilla `[x]` para consultar los ítems consolidados en producción.

- [x] **[UNIFICACIÓN DE VERSIONES VISIBLES]** Sincronizada la versión `v1.0.3` de forma homogénea en `tray.py:67`, `settings_window.py:178`, `run.bat:8`, `pyproject.toml:3`, `README.md:5` y `verify_install.py:205`. *(Resuelto v1.0.3)*
- [x] **[FILTRO PII MULTIPATRÓN & PRUEBA REALISTA]** `PIISafeFilter` en `logging_setup.py` ahora detecta prefijos de fuga real (`adjusted text:`, `result text:`, `transcription:`, etc.) y diccionarios con comillas. En `test_audio.py` se validó con frases reales de usuario (`"la reunion confidencial de las 5"`), eliminando la prueba autocumplida. *(Resuelto v1.0.3)*
- [x] **[TKINTER THREAD-SAFETY EN HUD]** `main.py:164`: invocación de `hud.hide()` enrutada mediante `self.root.after(0, self.hud.hide)` al descartar audios sin habla, garantizando 100% de cumplimiento con el contrato de hilos de Tkinter. *(Resuelto v1.0.3)*
- [x] **[GROQ PING NO BLOQUEANTE (`max_retries=0`)]** `settings_window.py`: `verify_groq_api_key_online` configurado con `max_retries=0` para evitar congelamiento de hasta 7.5s. Además, códigos transitorios (429 rate limit, 500, 503) se tratan como avisos de red no bloqueantes en lugar de rechazar la clave. *(Resuelto v1.0.3)*
- [x] **[AISLAMIENTO DEL PORTAPAPELES EN PYTEST]** `tests/test_injector.py`: `test_clipboard_roundtrip` respalda y restaura el portapapeles del desarrollador en un bloque `finally`. Sustituidos los `assert True` residuales por comprobaciones reales de estado. *(Resuelto v1.0.3)*
- [x] **[REBRANDING COMPLETO EN DIAGNÓSTICO]** `verify_install.py` actualizado íntegramente con la marca oficial `MorocoVoice` y versión `v1.0.3`. *(Resuelto v1.0.3)*

---

## 🟢 2. BLOQUEANTES DE VERSIONES ANTERIORES RESUELTOS

- [x] **[PII LEAK ELIMINADO]** Logging de texto crudo reemplazado por metadatos numéricos en `engine_manager.py:198`. *(Resuelto v1.0.2)*
- [x] **[SUBSISTEMA VAD CONECTADO & AUTO-CORTE]** Conectado `has_detected_speech()` y auto-corte de silencio a 1.2s post-habla en `recorder.py` y `main.py`. *(Resuelto v1.0.2)*
- [x] **[SAMPLE RATE PARAMETRIZADO]** `CloudGroqWhisperEngine` parametrizado con `config.sample_rate`. *(Resuelto v1.0.2)*
- [x] **[SUITE TEST MOCKEADA]** `SendInput` aislado con `unittest.mock.patch` en `test_injector.py`. *(Resuelto v1.0.2)*
- [x] **[DECISIONES EXPLÍCITAS DE RICARDO GARCÍA]**:
  - `Win + Space` se preserva intacto como atajo oficial de dictado.
  - El portapapeles (`CF_UNICODETEXT`) se mantiene tal cual con inyección `Ctrl+V` y disponibilidad en historial `Win + V`.
  - Documentado con 100% de honestidad en `README.md`.

---

## 🟡 3. ROADMAP FUTURO (v1.1.0 / v1.2.0)

### 3A · Rendimiento y Aceleración
- [ ] **Aceleración CUDA Opcional:** Permitir selección de GPU NVIDIA en `LocalWhisperEngine` cuando `ctranslate2` detecte hardware compatible con cuDNN.

### 3B · UX Avanzada
- [ ] **Selector de Dispositivo de Audio en Ajustes:** Permitir elegir el micrófono deseado en lugar del predeterminado de Windows.
