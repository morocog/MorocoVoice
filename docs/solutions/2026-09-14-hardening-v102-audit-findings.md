# Ficha Técnica: Hardening Integral MorocoVoice v1.0.2 Post-Auditoría Independiente

**Fecha:** 2026-09-14  
**Repositorio:** `MorocoVoice`  
**Versión:** `v1.0.2`  
**Autor:** Antigravity AI & Ricardo García  

---

## 1. Contexto y Síntomas

Tras el lanzamiento de la versión `v1.0.1`, se comisionó una auditoría independiente profunda sin sesgo previo ([`docs/MOROCOVOICE_AUDIT_v1.0.1.md`](../MOROCOVOICE_AUDIT_v1.0.1.md)), elevando la calificación del proyecto de 4.5/10 a 7.5/10.

No obstante, la auditoría identificó 5 áreas críticas de mejora para alcanzar el estándar de producción (9.5+/10):
1. **Fuga PII en Logger:** `engine_manager.py:196` registraba en texto plano la transcripción cruda y corregida al aplicar el vocabulario. `PIISafeFilter` solo inspeccionaba `record.msg` y no los argumentos interpolados `record.args`.
2. **VAD sin consumidor activo:** `recorder.py` calculaba `is_speech_chunk` con Silero ONNX pero no auto-detenía la grabación por silencio ni descartaba sesiones sin voz antes de llamar a Groq Cloud.
3. **Sample Rate fijo:** `stt_cloud.py` convertía a WAV usando un literal `16000` hardcodeado ignorando `AppConfig.sample_rate`.
4. **Pruebas invasivas de SendInput:** `test_injector.py` invocaba `SendInput` real durante `pytest`, inyectando pulsaciones Ctrl+C a la ventana activa del desarrollador.
5. **Falta de comprobación online de credenciales:** `settings_window.py` solo validaba formato regex de la API Key de Groq sin certificar validez ni estado 401 Unauthorized contra el endpoint.

---

## 2. Causa Raíz

- **PII Leak:** Interpolación clásica de strings `%s` en `logger.info(template, arg1, arg2)`. En Python `logging.LogRecord`, `record.msg` conserva la plantilla original ("... %s -> %s"), mientras que los textos confidenciales viajan en `record.args`, evadiendo la búsqueda de palabras clave en `record.msg`.
- **VAD Desconectado:** `AudioRecorder` acumulaba `_speech_chunks_count` pero no exponía un temporizador de silencio posterior a la voz ni `main.py` consultaba `has_detected_speech()` antes de despachar a Groq.
- **Inyección en Test Runner:** Pruebas unitarias que pretendían comprobar que la función Win32 no arrojaba excepciones ejecutaban la API del sistema operativo en vivo sobre el escritorio del host.

---

## 3. Solución Implementada

### A. Eliminación de Fuga PII & Blindaje de Logger
- En [`app/engine/engine_manager.py`](file:///c:/Users/SDVP/Documents/GitHub/MorocoVoice/app/engine/engine_manager.py): se reemplazó la emisión de texto por metadatos numéricos puros:
  ```python
  delta = len(corrected_text) - len(raw_result.text)
  logger.info("Vocabulary post-processing applied (%+d char delta).", delta)
  ```
- En [`app/logging_setup.py`](file:///c:/Users/SDVP/Documents/GitHub/MorocoVoice/app/logging_setup.py): `PIISafeFilter` ahora evalúa `record.getMessage()`, detecta palabras prohibidas en el mensaje interpolado completo y purga `record.args = ()`.

### B. Conexión Activa de VAD & Auto-Corte de Silencio
- En [`app/audio/recorder.py`](file:///c:/Users/SDVP/Documents/GitHub/MorocoVoice/app/audio/recorder.py):
  - Añadido `silence_cutoff_seconds` (1.2s por defecto) y callback `on_silence_cutoff`.
  - El contador de silencio solo se activa **después de haber detectado habla humana**, disparando el auto-corte si el usuario deja de hablar por más de 1.2 segundos.
- En [`app/main.py`](file:///c:/Users/SDVP/Documents/GitHub/MorocoVoice/app/main.py):
  - Conectado `on_silence_cutoff` al flujo de procesamiento.
  - Al pulsar el atajo para detener la grabación, si `self.vad and not self.recorder.has_detected_speech()`, la sesión se descarta de inmediato, ocultando el HUD sin invocar a Groq ni gastar tokens.

### C. Parametrización de Sample Rate
- En [`app/engine/stt_cloud.py`](file:///c:/Users/SDVP/Documents/GitHub/MorocoVoice/app/engine/stt_cloud.py): `CloudGroqWhisperEngine` recibe `sample_rate: int = 16000` y lo transfiere dinámicamente a `numpy_to_wav_bytes`.
- En [`app/engine/engine_manager.py`](file:///c:/Users/SDVP/Documents/GitHub/MorocoVoice/app/engine/engine_manager.py): se suministra `sample_rate=config.sample_rate`.

### D. Mocking Seguro de `SendInput` en Tests
- En [`tests/test_injector.py`](file:///c:/Users/SDVP/Documents/GitHub/MorocoVoice/tests/test_injector.py): se mockeó `ctypes.windll.user32.SendInput` en `test_release_modifiers_executes_safely`, `test_send_ctrl_c_executes_safely` y `test_send_ctrl_v_executes_safely`, garantizando 0 pulsaciones parásitas durante la suite.

### E. Ping de Validación Online de API Key
- En [`app/ui/settings_window.py`](file:///c:/Users/SDVP/Documents/GitHub/MorocoVoice/app/ui/settings_window.py): función `verify_groq_api_key_online(api_key, timeout=2.5)` consulta `client.models.list()`. Si se recibe un error 401 Unauthorized, se alerta inmediatamente al usuario antes de guardar.

### F. Transparencia en README sobre Portapapeles
- En [`README.md`](file:///c:/Users/SDVP/Documents/GitHub/MorocoVoice/README.md): aclaración formal de que el respaldo y restauración cubre texto plano Unicode (`CF_UNICODETEXT`).

---

## 4. Anti-Patrones y Prohibiciones

1. **PROHIBIDO** interpolar variables que contengan texto dictado o transcrito dentro de `logger.info`, `logger.debug` o `logger.warning`. Solo se permiten longitudes, conteos o deltas.
2. **PROHIBIDO** invocar funciones de `ctypes.windll.user32.SendInput` directamente en pruebas unitarias automatizadas sin aislarlas mediante `unittest.mock.patch`.
3. **PROHIBIDO** ejecutar transcripciones cloud cuando el VAD Silero certifique ausencia total de voz en el buffer.

---

## 5. Verificación & Evidencia

- **Suite de Pruebas Automatizadas:**
  ```text
  pytest -v -> 32 passed in 1.20s (100% exitoso)
  ```
- **Linter & Formato:**
  ```text
  ruff check app tests -> All checks passed! (0 errores)
  ```
- **Consolidación de Archivos:**
  - Raíz del workspace `c:\Users\SDVP\Documents\GitHub\` 100% limpia de markdown y logs temporales.
  - Histórico de auditorías archivado en `MorocoVoice/docs/MOROCOVOICE_AUDIT_v1.0.0.md` y `v1.0.1.md`.
