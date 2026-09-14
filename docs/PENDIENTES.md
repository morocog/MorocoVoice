# PENDIENTES — MorocoVoice

> Generado tras la Auditoría de Trazabilidad DSH · commit `8bd0ae9` · 2026-09-14
> Fuente canónica: [`docs/MOROCOVOICE_AUDIT_v1.0.0.md`](./MOROCOVOICE_AUDIT_v1.0.0.md)
> Calificación de lanzamiento actual: **4.5 / 10**

---

## 🔴 1. VERIFICACIONES PENDIENTES EN CALIENTE (críticas, antes de que alguien lo use)

> 💡 **Validación Rápida con 1 Clic en Obsidian:** Haz clic directamente sobre la casilla `[ ]` para marcarla como `[x]` una vez probada en producción.

- [ ] **[BUG BLOQUEANTE #1]** Cambiar `config.json` línea 6: modelo LLM `qwen/qwen3.8-27b` **no existe en Groq** → toda reescritura falla con 404. Reemplazar por `llama-3.1-8b-instant`.
- [ ] **[BUG BLOQUEANTE #2]** Re-publicar `v1.0.1` desde `main` (el tag `v1.0.0` apunta a `912613e`, que aún tiene `"VoiceFlow"` en el vocabulario, no `"GitHub"`).
- [ ] **[BUG BLOQUEANTE #3]** `logging_setup.py:90` retorna `logging.getLogger("voiceflow.{name}")` en vez de `"morocovoice.{name}"` → `morocovoice.log` tiene **1 línea**, troubleshooting imposible, filtro PII inactivo, truncación de vocabulario silenciosa.
- [ ] **[BUG BLOQUEANTE #4]** Python 3.10 no puede arrancar (`StrEnum` requiere 3.11+). Con `pythonw.exe` el fallo es invisible (doble clic → nada). Unificar a `requires-python = ">=3.11"` en `pyproject.toml`, badge, README y `run.bat` (con comprobación de versión explícita).
- [ ] **[BUG BLOQUEANTE #5]** `.env.example` con placeholder `gsk_tu_clave_de_groq_aqui` tratado como credencial válida → cada arranque sin clave real hace llamadas 401 + descarga silenciosa de ~75 MB de Whisper local. La UI confirma "almacenada de forma segura" aunque sea el placeholder → engaño activo.
- [ ] **[BUG BLOQUEANTE #6]** `injector.get_clipboard_text()` solo guarda `CF_UNICODETEXT`. Si el usuario copió una imagen o archivos, al dictar los **pierde irrecuperablemente**. El README lo promete explícitamente como "no destructiva".
- [ ] **[BUG #7]** `Win + Space` colisiona con el atajo nativo de Windows de cambio de idioma/IME (teclado ES+EN). Cada dictado cambia la distribución. README lo vende como "sin conflictos".
- [ ] **[BUG #8]** HUD **no es translúcida** (no hay `-alpha` en ningún archivo). README dice "translúcida".
- [ ] **[BUG #9]** VAD Silero ONNX: `is_speech_chunk` **nunca se llama** en todo `app/`. La bandeja reporta "VAD: Silero (ONNX)" — información falsa. `onnxruntime` ocupa 45.6 MB para nada.
- [ ] **[BUG #10]** `max_tokens=300` en reescritura + reemplazo destructivo de la selección: texto largo puede quedar truncado a mitad de frase sin posibilidad de undo.
- [ ] **[BUG #11]** `language="es"` hardcodeado en STT cloud y local. Dictar en inglés se decodifica en español. No se documenta.
- [ ] **[BUG #12]** `config.json` está versionado y la app lo reescribe en `_on_save` → conflicto de `git pull` para todo usuario que guarde ajustes.

---

## 🟡 2. MEJORAS FUTURAS — ROADMAP v1.1

### 2A · Vocabulario personalizado (prioridad máxima tras los bloqueantes)
- [ ] Añadir sección **"Vocabulario Personalizado"** en la ventana de Configuración (`settings_window.py`):
  - `tk.Text` multilínea (una línea por término)
  - Contador en vivo `n/30` con color (verde → ámbar → rojo)
  - Aviso bloqueante antes de truncar, nombrando los términos ignorados
  - Botón "↩ Restaurar vocabulario recomendado"
- [ ] **Sustituir el vocabulario por defecto** — eliminar jerga privada del autor (`El Panóptico`, `Smart Time Blocks`, `Telat Group`, `rgarcia`) y poblar con términos genéricos útiles para WFM/call center.
- [ ] **Post-proceso correctivo determinista**: aplicar `difflib.SequenceMatcher` (umbral ~0.85) sobre la salida de Whisper para corregir términos del vocabulario malinterpretados (ej. `GITCOP → GitHub`). La dependencia ya existe en `stt_local.py:9`.
- [ ] Documentar en README (Paso 4 nuevo: "Opcional — enséñale tus palabras") el límite de 30, el motivo (224 tokens de Whisper) y cómo agregar términos.

### 2B · Rebranding completo a MorocoVoice
- [ ] `hud.py:109` — texto visible `"VoiceFlow"` al usuario
- [ ] `prompt_templates.py:32,39` — prompts enviados al LLM con marca antigua
- [ ] `vad.py:89` — User-Agent `VoiceFlow-Win-Bootstrap/3.4.1`
- [ ] `verify_install.py:205` — banner `VOICEFLOW-WIN v3.4.1`
- [ ] `logging_setup.py:99` — namespace `voiceflow`
- [ ] Clases: `VoiceFlowException`, alias `VoiceFlowApplication`
- [ ] Historial de `docs/` referenciando v3.4.1, v3.5.0, v3.5.1

### 2C · Experiencia no técnica
- [ ] Instrucciones de instalación sin `git clone` en terminal: enlace a "Download ZIP" o GitHub Desktop en el README
- [ ] Validar la API key con llamada de prueba al guardar (Groq devuelve 401 en ~200 ms → mostrar error claro en vez de éxito falso)
- [ ] `run.bat`: detectar Python 3.11+, detectar stub de Microsoft Store, mostrar error con pausa visible
- [ ] Abrir Settings solo en el primer arranque real (cuando `.env` no tiene clave válida), no en cada inicio
- [ ] Renderizar `help_text` en la ventana de Configuración (parámetro aceptado pero nunca mostrado en 6 lugares)
- [ ] Añadir timeout explícito a llamadas Groq STT y LLM (hoy pueden dejar el HUD en "Procesando..." indefinidamente)
- [ ] Validar formato del atajo al guardar en `_on_save` (hoy acepta cualquier string sin advertencia)

### 2D · Integridad y confianza
- [ ] `verify_install.py`: invocar desde `run.bat` o eliminar. Actualizar banner y versión.
- [ ] Añadir GitHub Actions CI: `ruff check` + `pytest` en PR
- [ ] Fijar versiones exactas en `requirements.txt`
- [ ] Eliminar `requests>=2.31.0` de `requirements.txt` (nunca importado)
- [ ] Mover `config.json` a `.gitignore` o convertirlo en `config.example.json` con valores seguros

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
