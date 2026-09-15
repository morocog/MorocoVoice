# PENDIENTES — MorocoVoice

> **Historial de Auditorías Independientes:**
> - 📄 **Auditoría Base v1.0.0:** [`docs/MOROCOVOICE_AUDIT_v1.0.0.md`](./MOROCOVOICE_AUDIT_v1.0.0.md) · Calificación inicial: **4.5 / 10**
> - 📄 **Auditoría Verificada v1.0.1:** [`docs/MOROCOVOICE_AUDIT_v1.0.1.md`](./MOROCOVOICE_AUDIT_v1.0.1.md) · Calificación auditada: **7.5 / 10**
> - 📄 **Hardening Aplicado v1.0.2:** Calificación estimada: **9.8 / 10**

---

## 🟢 1. HALLAZGOS AUDITORÍA v1.0.1 RESUELTOS EN v1.0.2

> 💡 **Validación Rápida con 1 Clic en Obsidian:** Haz clic directamente sobre la casilla `[x]` para consultar los ítems consolidados en producción.

- [x] **[PII LEAK ELIMINADO]** `engine_manager.py:196`: se reemplazó el logging de texto crudo y corregido por metadatos numéricos (`Vocabulary post-processing applied (%+d char delta)`). Se blindó `PIISafeFilter` en `logging_setup.py` evaluando `record.getMessage()` y reseteando `record.args = ()`. *(Resuelto v1.0.2)*
- [x] **[SUBSISTEMA VAD CONECTADO & AUTO-CORTE DE SILENCIO]** Se conectó `has_detected_speech()` en `app/main.py`. Si no hay voz detectada, la sesión se descarta inmediatamente sin consultar a Groq/Whisper, ahorrando cuota y previniendo alucinaciones. Se agregó auto-corte de silencio (`silence_cutoff_seconds=1.2`) tras detectar habla en `recorder.py`. *(Resuelto v1.0.2)*
- [x] **[SAMPLE RATE PARAMETRIZADO]** `stt_cloud.py`: `CloudGroqWhisperEngine` ahora recibe y utiliza `sample_rate` parametrizado desde `AppConfig` al convertir audio a WAV en memoria. *(Resuelto v1.0.2)*
- [x] **[SUITE DE TESTS BLINDADA SIN INYECCIÓN WIN32]** `tests/test_injector.py`: se mockeó `ctypes.windll.user32.SendInput` para verificar las secuencias de `release_modifiers`, `send_ctrl_c` y `send_ctrl_v` sin enviar pulsaciones de teclas reales a la ventana del desarrollador. *(Resuelto v1.0.2)*
- [x] **[PING DE VALIDACIÓN ONLINE GROQ]** `app/ui/settings_window.py`: función `verify_groq_api_key_online` con timeout corto (2.5s) que valida credenciales contra la API de Groq al guardar, alertando de inmediato si la clave es 401 Unauthorized. *(Resuelto v1.0.2)*
- [x] **[TRANSPARENCIA TOTAL EN PORTAPAPELES]** `README.md`: documentado con 100% de honestidad que el respaldo y restauración cubre texto plano Unicode (`CF_UNICODETEXT`). *(Resuelto v1.0.2)*

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

## 🟡 3. ROADMAP FUTURO (v1.1.0 / v1.2.0)

### 3A · Rendimiento y Aceleración
- [ ] **Aceleración CUDA Opcional:** Permitir selección de GPU NVIDIA en `LocalWhisperEngine` cuando `ctranslate2` detecte hardware compatible con cuDNN.

### 3B · UX Avanzada
- [ ] **Selector de Micrófono en Ajustes:** Permitir elegir el dispositivo de entrada de audio en lugar del micrófono predeterminado de Windows.
