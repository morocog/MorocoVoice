# Ficha Técnica: Restauración de Dictado por Voz, Migración LLM Groq y Barrido Cosmético v1.0.4

**Módulo / Repositorio:** `MorocoVoice` (Windows 10/11 x64)  
**Fecha:** 2026-09-14  
**Versión:** `v1.0.4`  
**Autor:** Antigravity AI & Ricardo García  

---

## 1. Contexto y Síntomas del Problema

Al probar la versión localmente mediante `run.bat`:
- **Síntoma 1 (P0 Dictado Mudo):** La interfaz HUD y el sonido de inicio (`blip`) se reproducían, pero al pulsar `Win + Espacio` para cerrar, sonaba el tono de fin (`pop`) y **no se transcribía ni inyectaba nada**.
- **Síntoma 2 (P0 Ausencia de Refinamiento Semántico y Signos de Puntuación):** Tras restaurar el audio hacia Whisper STT, el texto dictado salía en crudo (sin mayúsculas iniciales, sin puntos y sin signos de interrogación `¿...?` ante inflexiones de voz), como si el LLM no estuviera activo.

---

## 2. Causa Raíz

1. **Cerrojo Prematuro y Destructivo en `toggle_dictation` (`app/main.py`):**  
   En la versión `v1.0.2` se agregó una condición que evaluaba `if self.vad and not self.recorder.has_detected_speech(): return`. Esta compuerta descartaba silenciosamente todo el buffer de audio antes de llegar a Whisper STT debido a que Silero VAD v5 requería 64 muestras de contexto para no atenuar su probabilidad.
2. **Descomisión del Modelo `llama-3.1-8b-instant` en Groq (Error 404):**  
   Al inspeccionar `morocovoice.log:324,337,345`, se descubrió la falla silenciosa del refinador:
   ```text
   [WARNING] morocovoice.rewriter: Groq LLM call failed: Error code: 404 - {'error': {'message': 'The model `llama-3.1-8b-instant` does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'code': 'model_not_found'}}
   ```
   Groq retiró de su catálogo activo el modelo `llama-3.1-8b-instant`. Al fallar la llamada a la API con 404, `refine_dictation` entraba en la rama de fallback rápido de emergencia (`return raw_transcript`), entregando la transcripción sin procesar por IA (sin puntuación, sin signos de interrogación y sin corrección gramatical).

---

## 3. Solución Implementada

1. **Migración Oficial de Modelo Groq a `qwen/qwen3.8-27b`:**  
   Se actualizó el modelo por defecto en `app/contracts.py`, `config.json`, `config.example.json` y `app/ui/settings_window.py` a `qwen/qwen3.8-27b`, el modelo de producción más veloz y preciso disponible en Groq para razonamiento en español y puntuación natural.
2. **Mecanismo de Resiliencia Multi-Modelo (Fallback Automático en `app/llm/rewriter.py`):**  
   Se implementó una lista de contingencia en `_call_llm` (`[self.groq_model, "qwen/qwen3.8-27b", "groq/compound-mini", "qwen/qwen3.6-27b"]`). Si el modelo configurado devuelve error 404, 400 o `model_not_found`, el despachador prueba de forma transparente los siguientes modelos candidatos antes de rendirse.
3. **Limpieza de Etiquetas `<think>` de Modelos de Razonamiento:**  
   Se implementó `_clean_llm_response()` para eliminar etiquetas internas de razonamiento si un modelo de la familia Qwen las emite, garantizando texto 100% limpio para inyección en pantalla.
4. **Eliminación del Descarte por VAD en Dictado Explícito (`app/main.py`):**  
   En `toggle_dictation`, `_on_max_recording_reached` y `_on_silence_cutoff_reached`, si el buffer contiene datos (`len(audio_buffer) > 0`), se encola incondicionalmente a `_enqueue_processing(audio_buffer)`.
5. **Implementación Completa del Contexto Silero VAD v5 (`app/audio/vad.py`):**  
   Concatenación de `self._context` (64 muestras) antes de la inferencia ONNX y actualización recurrente.
6. **Barrido Total de Residuos Cosméticos (Inventario DSH):**  
   - `verify_install.py:148`: `MorocoVoice Hardware & Environment Diagnostics`.
   - `.gitignore`: Eliminación de patrones muertos y corrección del encabezado.
   - `logging_setup.py:123`: Corrección del docstring a `morocovoice.log`.
   - `contracts.py`: Herencia de `MorocoVoiceException` preservando alias de compatibilidad.
   - Barrido de 14 docstrings de módulo a `MorocoVoice`.

---

## 4. Anti-Patrones y Prohibiciones

- **PROHIBIDO:** Depender de un único identificador estático de modelo LLM en la nube sin lista de fallback automático ante deprecaciones de proveedores.
- **PROHIBIDO:** Usar VAD para tirar a la basura grabaciones iniciadas y terminadas deliberadamente por el usuario.

---

## 5. Verificación y Evidencia

- **Prueba Empírica con el Texto Real de Ricardo:**
  - Entrada: `"estoy confirmando que todo este funcionando correctamente y entiendes preguntas sabes cuando estoy poniendo inflexion de voz para hacer una pregunta"`
  - Salida Refinada: `"Estoy confirmando que todo está funcionando correctamente. ¿Entiendes las preguntas? ¿Sabes cuándo estoy poniendo inflexión de voz para hacer una pregunta?"`
- **Suite de Pruebas Pytest:** 33 pruebas unitarias pasando (`33 passed in 1.79s`).
- **Linter Ruff:** `All checks passed!`.
