# PENDIENTES — MorocoVoice

> Generado tras la Auditoría de Trazabilidad DSH · commit `8bd0ae9` · 2026-09-14
> Fuente canónica: [`docs/MOROCOVOICE_AUDIT_v1.0.0.md`](./MOROCOVOICE_AUDIT_v1.0.0.md)
> Calificación de lanzamiento actual: **4.5 / 10**

---

## 🔴 1. VERIFICACIONES PENDIENTES EN CALIENTE (críticas, antes de que alguien lo use)

> 💡 **Validación Rápida con 1 Clic en Obsidian:** Haz clic directamente sobre la casilla `[ ]` para marcarla como `[x]` una vez probada en producción.

- [x] **[BUG BLOQUEANTE #1]** Cambiar `config.json` línea 6: modelo LLM `llama-3.1-8b-instant` reemplazó al inexistente qwen. *(Resuelto v1.0.1)*
- [ ] **[BUG BLOQUEANTE #2]** Re-publicar `v1.0.1` desde `main` con nuevo tag `v1.0.1`.
- [x] **[BUG BLOQUEANTE #3]** `logging_setup.py:90` namespace `"morocovoice.{name}"` corregido, filtro PII y rotación activa. *(Resuelto v1.0.1)*
- [x] **[BUG BLOQUEANTE #4]** Python 3.11+ unificado en `pyproject.toml`, badge, README y `run.bat` con validación estricta al arranque. *(Resuelto v1.0.1)*
- [x] **[BUG BLOQUEANTE #5]** Placeholder de `.env` (`gsk_tu_clave_de_groq_aqui`) detectado y filtrado tanto en carga como en `settings_window.py` con advertencia al usuario. *(Resuelto v1.0.1)*
- [x] **[BUG BLOQUEANTE #6]** *Mantenido por decisión explícita de Ricardo García*: el portapapeles actual funciona bien en el día a día y se preserva intacto.
- [x] **[BUG #7]** *Mantenido por decisión explícita de Ricardo García*: el atajo `Win + Space` se conserva como atajo principal de dictado.
- [x] **[BUG #8]** HUD translúcida activada con `attributes("-alpha", 0.92)`. *(Resuelto v1.0.1)*
- [x] **[BUG #9]** VAD Silero ONNX activado en tiempo real en `_audio_callback` de `recorder.py` con método `has_detected_speech()`. *(Resuelto v1.0.1)*
- [x] **[BUG #10]** `max_tokens` dinámico en `rewriter.py` para evitar truncamientos de selección larga. *(Resuelto v1.0.1)*
- [x] **[BUG #11]** `stt_language` parametrizado en `AppConfig`, `config.example.json`, selector en UI y motores STT cloud y local. *(Resuelto v1.0.1)*
- [x] **[BUG #12]** `config.json` añadido a `.gitignore` y generado automáticamente desde `config.example.json` en `run.bat`. *(Resuelto v1.0.1)*

---

## 🟡 2. MEJORAS FUTURAS — ROADMAP v1.1

### 2A · Vocabulario personalizado (prioridad máxima tras los bloqueantes)
- [x] Pestaña **"Vocabulario Personalizado"** en la ventana de Configuración (`settings_window.py`) con editor multilínea, contador `n/30` dinámico con semáforo y confirmación antes de truncar. *(Resuelto v1.0.1)*
- [x] **Sustituir el vocabulario por defecto**: eliminada jerga privada del autor y poblada con 30 términos estándar de tecnología y WFM. *(Resuelto v1.0.1)*
- [x] **Post-proceso correctivo determinista**: `difflib.SequenceMatcher` y homófonos duros en `engine_manager.py` (corrige `gitcop -> GitHub`, `github -> GitHub`, etc.). *(Resuelto v1.0.1)*
- [x] Documentar en README (Paso 4: "Enséñale tus palabras y jerga técnica") el funcionamiento del vocabulario y su corrector. *(Resuelto v1.0.1)*

### 2B · Rebranding completo a MorocoVoice
- [x] `hud.py:109` — texto visible cambiado a `"MorocoVoice"`. *(Resuelto v1.0.1)*
- [x] `prompt_templates.py:32,39` — prompts del sistema actualizados a MorocoVoice. *(Resuelto v1.0.1)*
- [x] `vad.py:89` — User-Agent actualizado a `MorocoVoice-Bootstrap/1.0.1`. *(Resuelto v1.0.1)*
- [x] `verify_install.py:205` — banner actualizado a `MOROCOVOICE v1.0.1`. *(Resuelto v1.0.1)*
- [x] `logging_setup.py:99` — namespace canónico `morocovoice`. *(Resuelto v1.0.1)*
- [x] Clases: `MorocoVoiceException` creada con alias de retrocompatibilidad `VoiceFlowException`. *(Resuelto v1.0.1)*

### 2C · Experiencia no técnica
- [x] Instrucciones de instalación sin terminal con enlace a "Download ZIP" en README. *(Resuelto v1.0.1)*
- [x] Detección de claves inválidas/placeholders con diálogo interactivo en `_on_save`. *(Resuelto v1.0.1)*
- [x] `run.bat`: detección explícita de Python 3.11+ y copia de `config.example.json`. *(Resuelto v1.0.1)*
- [x] Apertura de ventana de configuración solo si no hay clave válida configurada. *(Resuelto v1.0.1)*
- [x] Renderizado de `help_text` inline debajo de cada campo en `SettingsModal`. *(Resuelto v1.0.1)*
- [x] Timeout de 15.0 segundos en llamadas STT y LLM a Groq. *(Resuelto v1.0.1)*
- [x] Validación de atajos de teclado no vacíos en `_on_save`. *(Resuelto v1.0.1)*

### 2D · Integridad y confianza
- [x] `verify_install.py` actualizado a MorocoVoice v1.0.1. *(Resuelto v1.0.1)*
- [x] GitHub Actions CI implementado en `.github/workflows/ci.yml` (ruff + pytest en Python 3.11 Windows). *(Resuelto v1.0.1)*
- [x] `requirements.txt` saneado: eliminado `requests` no utilizado, añadido `pytest>=8.0.0`. *(Resuelto v1.0.1)*
- [x] `config.json` excluido en `.gitignore` y sincronizado en `config.example.json`. *(Resuelto v1.0.1)*

---

## 🔵 3. DEUDA TÉCNICA CONOCIDA

- **Tests sin aserciones reales** (~8/26): `test_emergency_restore_safeguard`, `test_clipboard_lock_reentrancy`, `test_release_modifiers_executes_safely`, `test_send_ctrl_c_executes_safely` → todos `assert True`. `test_send_ctrl_c_executes_safely` inyecta Ctrl+C real al sistema durante tests.
- **Cobertura cero** de rutas críticas: `inject_text()`, restauración asíncrona del portapapeles, `get_selected_text()`, `numpy_to_wav_bytes()`, `load_config()`/`.env`, `recorder.py`, `_on_save()`, HUD y bandeja.
- **Race condition en portapapeles**: dos inyecciones seguidas sobrescriben `_active_backup_text` mientras el primer hilo de restauración está pendiente.
- **`get_selected_text()` con `time.sleep(0.12)` fijo**: en Outlook/Teams lentos el portapapeles aún está vacío.
- **`numpy_to_wav_bytes(sample_rate=16000)` hardcodeado** ignorando `config.sample_rate`.
- **`trigger_diagnostics` / `hotkey_shutdown` / `hotkey_diagnostics`** en código, eliminados por `_on_save` → código medio muerto.
- **GPU/CUDA**: `verify_install.py` recomienda tiers por VRAM pero `engine_manager.py:80` fija `device="cpu"` siempre.
- **`contracts.py:81` default `"alt+space"`** vs `config.json` `"win+space"` → borrar `config.json` cambia el atajo silenciosamente.
