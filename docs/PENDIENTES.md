# PENDIENTES — MorocoVoice

> **Historial de Auditorías Independientes:**
> - 📄 **Auditoría Base v1.0.0:** [`docs/MOROCOVOICE_AUDIT_v1.0.0.md`](./MOROCOVOICE_AUDIT_v1.0.0.md) · Calificación inicial: **4.5 / 10**
> - 📄 **Auditoría Verificada v1.0.1:** [`docs/MOROCOVOICE_AUDIT_v1.0.1.md`](./MOROCOVOICE_AUDIT_v1.0.1.md) · Calificación actual: **7.5 / 10**
> - **Meta próxima release (v1.0.2 / v1.1.0):** **9.5+ / 10**

---

## 🔴 1. HALLAZGOS CRÍTICOS POST-AUDITORÍA v1.0.1 (Prioridad Inmediata)

> 💡 **Validación Rápida con 1 Clic en Obsidian:** Haz clic directamente sobre la casilla `[ ]` para marcarla como `[x]` una vez probada en producción.

- [ ] **[PII LEAK]** `engine_manager.py:196`: la línea `logger.info("Vocabulary post-processing adjusted text: '%s' -> '%s'...")` escribe la **transcripción cruda a disco en morocovoice.log**. Además, `PIISafeFilter` en `logging_setup.py` solo inspecciona `record.msg` (la plantilla) y no `record.getMessage()` (con argumentos interpolados), por lo que cualquier llamada formateda evade el filtro.
  - *Acción:* Registrar solo metadatos numéricos (caracteres ajustados) en `engine_manager.py` y endurecer `PIISafeFilter` para evaluar `record.getMessage()`.
- [ ] **[VAD SIN CONSUMIDOR]** `recorder.py:150` define `has_detected_speech()` pero ningún módulo la invoca. `is_speech_chunk` ejecuta inferencia ONNX en cada bloque de 32ms dentro del callback sensible de `sounddevice` sin que su veredicto detenga la grabación ni descarte silencios.
  - *Acción:* Conectar el veredicto de silencio al auto-corte usando `silence_threshold_seconds` (1.2s), o desacoplar la inferencia del hilo de audio.
- [ ] **[SAMPLE RATE HARDCODEADO]** `stt_cloud.py:85`: invoca `numpy_to_wav_bytes(audio_data, sample_rate=16000)` con valor literal fijo, ignorando `self.config.sample_rate`.

---

## 🟢 2. BLOQUEANTES DE v1.0.0 YA RESUELTOS EN v1.0.1

- [x] **[BUG BLOQUEANTE #1]** Cambiar modelo LLM a `llama-3.1-8b-instant` en `contracts.py`, `config.example.json` y settings. *(Resuelto v1.0.1)*
- [x] **[BUG BLOQUEANTE #2]** Publicada la versión `v1.0.1` desde `main` con nuevo tag anotado `v1.0.1`. *(Resuelto v1.0.1)*
- [x] **[BUG BLOQUEANTE #3]** `logging_setup.py:90` namespace `"morocovoice.{name}"` corregido, filtro PII y rotación activa. *(Resuelto v1.0.1)*
- [x] **[BUG BLOQUEANTE #4]** Python 3.11+ unificado en `pyproject.toml`, badge, README y `run.bat` con validación estricta al arranque. *(Resuelto v1.0.1)*
- [x] **[BUG BLOQUEANTE #5]** Placeholder de `.env` (`gsk_tu_clave_de_groq_aqui`) detectado y filtrado tanto en carga como en `settings_window.py` con advertencia al usuario. *(Resuelto v1.0.1)*
- [x] **[BUG BLOQUEANTE #6]** *Mantenido por decisión explícita de Ricardo García*: el portapapeles actual (`CF_UNICODETEXT`) se preserva intacto por ser funcional para texto en el día a día.
- [x] **[BUG #7]** *Mantenido por decisión explícita de Ricardo García*: el atajo `Win + Space` se conserva como atajo principal de dictado.
- [x] **[BUG #8]** HUD translúcida activada con `attributes("-alpha", 0.92)`. *(Resuelto v1.0.1)*
- [x] **[BUG #9]** VAD Silero ONNX ejecutado en tiempo real en `_audio_callback` de `recorder.py`. *(Resuelto v1.0.1)*
- [x] **[BUG #10]** `max_tokens` dinámico en `rewriter.py` para evitar truncamientos de selección larga. *(Resuelto v1.0.1)*
- [x] **[BUG #11]** `stt_language` parametrizado en `AppConfig`, `config.example.json`, selector en UI y motores STT cloud y local. *(Resuelto v1.0.1)*
- [x] **[BUG #12]** `config.json` añadido a `.gitignore` y generado automáticamente desde `config.example.json` en `run.bat`. *(Resuelto v1.0.1)*
- [x] **[VOCABULARIO UI & DIFflib]** Pestaña con `tk.Text`, contador `n/30` dinámico, eliminación de jerga privada y corrector fonético `difflib` sin falsos positivos en español. *(Resuelto v1.0.1)*
- [x] **[REBRANDING COMPLETO]** Prompts de LLM, HUD, User-Agent, banners de instalación y alias de excepciones saneados. *(Resuelto v1.0.1)*
- [x] **[CI GITHUB ACTIONS]** Pipeline de `.github/workflows/ci.yml` con `ruff` y `pytest` en Windows Python 3.11. *(Resuelto v1.0.1)*

---

## 🟡 3. ROADMAP Y DEUDA TÉCNICA (v1.1.0 / v1.2.0)

### 3A · Calidad de Testing
- [ ] **Mocks Win32 en Test Suite:** Reemplazar los 4 `assert True` en `test_injector.py` (`test_emergency_restore_safeguard`, `test_clipboard_lock_reentrancy`, `test_release_modifiers_executes_safely`) por verificaciones con mocks.
- [ ] **Aislar `test_send_ctrl_c_executes_safely`:** Mockear `ctypes.windll.user32.SendInput` para evitar inyectar un Ctrl+C real al entorno de trabajo durante la ejecución de `pytest`.

### 3B · UX y Seguridad
- [ ] **Ping de Validación Online en Groq:** Realizar llamada de comprobación HTTP rápida con timeout de 2s en `_on_save()` para certificar que la clave es válida antes de guardar.
- [ ] **Portapapeles multi-formato (o advertencia):** Evaluar soporte para `CF_DIB` / `CF_HDROP` o documentar explícitamente en README que solo preserva texto plano.

### 3C · Rendimiento Local
- [ ] **Aceleración CUDA Opcional:** Permitir selección de GPU NVIDIA en `LocalWhisperEngine` cuando `ctranslate2` detecte hardware compatible.
