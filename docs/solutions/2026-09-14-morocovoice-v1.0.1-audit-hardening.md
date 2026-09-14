# Ficha Técnica: Hardening Industrial y Cierre de Brechas Auditoría DSH (MorocoVoice v1.0.1)

**Fecha:** 2026-09-14  
**Versión:** `v1.0.1`  
**Autor:** Ricardo García (`rgarcia@telat-group.com`) / Asistente Antigravity  
**Repositorio:** `https://github.com/morocog/MorocoVoice`  

---

## 1. Contexto y Síntomas

Tras el lanzamiento inicial de MorocoVoice v1.0.0, una auditoría técnica externa e independiente ejecutada por DeepSeek Harness (DSH) arrojó una calificación de 4.5/10, detectando múltiples discrepancias entre las promesas funcionales del repositorio y el comportamiento del código:
1. Reescritura semántica rota por referencia a modelo inexistente en Groq (`qwen/qwen3.8-27b`).
2. Error de transcripción de términos clave (`GitHub -> GITCOP`) y presencia de jerga privada en el vocabulario por defecto.
3. El HUD carecía de la translucidez prometida en la documentación (`-alpha` ausente).
4. `StrEnum` exigía Python 3.11+ pero los scripts y badges declaraban Python 3.10+, provocando cierres invisibles con `pythonw.exe`.
5. El VAD Silero ONNX (`is_speech_chunk`) nunca era invocado durante la captura de audio en `recorder.py`.
6. La clave de Groq aceptaba el placeholder `gsk_tu_clave_de_groq_aqui` y mostraba mensajes falsos de éxito.
7. Modificaciones en la interfaz guardaban `config.json`, archivo versionado que provocaba conflictos inmediatos de `git pull`.

Por directriz explícita del usuario, se acordó:
- **Mantener `Win + Space`** como atajo de dictado predeterminado.
- **Mantener el portapapeles actual** (el manejo actual es seguro y funcional en el uso diario).
- **Resolver de forma integral todas las demás brechas** identificadas en la auditoría.

---

## 2. Causa Raíz

1. **Desfase de modelos:** El catálogo de Groq descontinuó `qwen/qwen3.8-27b` a favor de `llama-3.1-8b-instant`.
2. **Ausencia de post-procesador:** Whisper con `initial_prompt` solo sesga probabilidades pero no previene fonética errónea si el audio es rápido o ruidoso.
3. **Falta de UI para vocabulario:** Los usuarios novatos no tenían forma visual de personalizar sus palabras clave sin editar archivos JSON a mano.
4. **Desconexión VAD-Recorder:** `AudioRecorder` recibía la instancia de `VoiceActivityDetector` pero su método `_audio_callback` no llamaba a `is_speech_chunk`.
5. **Divergencia de versión Python:** `contracts.py` importaba `StrEnum` (Python 3.11+) mientras `run.bat` y `pyproject.toml` permitían 3.10.

---

## 3. Solución Implementada

1. **Unificación a Python 3.11+:**
   - Actualizado `pyproject.toml` a `requires-python = ">=3.11"` y versión `1.0.1`.
   - Modificado `run.bat` para verificar estrictamente `sys.version_info >= (3, 11)`.
   - Actualizado badge en `README.md`.
2. **Pestaña de Vocabulario y Corrector Determinista:**
   - Creada pestaña `📖 Vocabulario Personalizado` en `SettingsModal` con `tk.Text`, contador dinámico `n/30` con código de colores (verde/ámbar/rojo), advertencia antes de truncar y botón de restauración.
   - Reemplazada la jerga privada en `custom_vocabulary.json` por 30 términos estándar de industria tech y WFM (`GitHub`, `Whisper`, `WFM`, `Workforce Management`, `Dashboard`, `Omnicanal`, `Backend`, etc.).
   - Implementado en `engine_manager.py` el post-procesador `apply_vocabulary_post_processing` combinando diccionario fonético duro (`gitcop -> GitHub`) y fuzzy matching con `difflib.SequenceMatcher` (umbral 0.85) excluyendo stopwords en español.
3. **Activación de VAD Silero ONNX:**
   - En `recorder.py`, cada chunk de audio evalúa `vad.is_speech_chunk(chunk)` y acumula estadísticas en `has_detected_speech()`.
4. **Translucidez HUD y Rebranding:**
   - Añadido `self.root.attributes("-alpha", 0.92)` en `FloatingHUD`.
   - Limpieza exhaustiva de la marca previa en `hud.py`, `prompt_templates.py`, `vad.py`, `verify_install.py` y alias `MorocoVoiceException`.
5. **Saneamiento de Claves y Configuración Git:**
   - Añadida validación `is_valid_groq_api_key()` en `config.py` y diálogo interactivo en `settings_window.py`.
   - Añadido `config.json` a `.gitignore` y sincronizado en `config.example.json`.
   - `run.bat` auto-genera `config.json` desde `config.example.json` si no existe.
6. **Ajustes de Red y Rendimiento:**
   - Añadido `timeout=15.0` en clientes Groq STT y LLM.
   - Cálculo dinámico de `max_tokens` en `rewriter.py` para selecciones extensas.
   - Configurado `stt_language` (default `"es"`) expuesto en `AppConfig` y la UI.
7. **CI y Automatización:**
   - Creado `.github/workflows/ci.yml` para ejecutar `ruff check` y `pytest -v` en Windows con Python 3.11.

---

## 4. Anti-Patrones / Prohibiciones

1. **NUNCA versionar `config.json` modificado por la UI:** Mantenerlo en `.gitignore` y usar `config.example.json` como plantilla inmutable.
2. **NUNCA asumir que el `initial_prompt` de Whisper es suficiente:** Siempre complementar con post-procesamiento determinista para términos técnicos críticos.
3. **NUNCA permitir que claves placeholder se marquen como válidas:** Si la clave es un placeholder o vacía, avisar inmediatamente al usuario en la UI.
4. **NUNCA omitir timeout en llamadas a APIs en la nube:** Un cliente Groq sin timeout congela el HUD de Windows indefinidamente si se pierde la conexión.

---

## 5. Verificación & Evidencia

- **Suite de Pruebas Unitarias:** 28 pruebas ejecutadas con `pytest -v`, 100% pasando:
  - `test_vocabulary_post_processing_corrections`: Verificó `gitcop -> GitHub`, `github -> GitHub` y frases multi-palabra.
  - `test_is_valid_groq_api_key`: Verificó el rechazo de placeholders y aceptación de claves legítimas.
- **Ruff Linter:** `ruff check app tests` completado con 0 errores (`All checks passed!`).
- **HUD:** Inspección de inicialización con `attributes("-alpha", 0.92)` validada.
