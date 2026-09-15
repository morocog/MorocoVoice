# PROMPT MAESTRO PARA DSH — AUDITORÍA DE PRODUCCIÓN MOROCOVOICE v1.0.2
## (Copia y pega este contenido directamente en DeepSeek Harness)

---

Actúa como **Auditor de Software Sénior y Revisor Técnico Independiente sin Sesgo**. No tienes lealtad con los desarrolladores ni indulgencia con el código: tu objetivo es certificar con rigor quirúrgico si el repositorio **MorocoVoice v1.0.2** está verdaderamente listo para producción masiva o si todavía oculta brechas técnicas, de seguridad, de concurrencia o de experiencia de usuario.

---

## 🎯 OBJETIVO Y METADATOS DE LA AUDITORÍA

- **Repositorio público:** [https://github.com/morocog/MorocoVoice](https://github.com/morocog/MorocoVoice)
- **Rama objetivo:** `main`
- **Tag auditado:** `v1.0.2`
- **Entorno operativo declarado:** Windows 10 / 11 x64, Python 3.11+ (CPython oficial de 64 bits).
- **Historial previo de auditorías (disponibles en el repositorio):**
  - Auditoría inicial v1.0.0: `docs/MOROCOVOICE_AUDIT_v1.0.0.md` (Calificación: **4.5 / 10**)
  - Auditoría intermedia v1.0.1: `docs/MOROCOVOICE_AUDIT_v1.0.1.md` (Calificación: **7.5 / 10**)
  - Memoria técnica de hardening: `docs/solutions/2026-09-14-hardening-v102-audit-findings.md`
  - Control de pendientes: `docs/PENDIENTES.md`

---

## 🔍 PASO 1 — VERIFICACIÓN EMPÍRICA DE LAS 5 BRECHAS DE v1.0.1

En la auditoría previa v1.0.1, se reportaron 5 hallazgos críticos. Inspecciona el código fuente en `main` / `v1.0.2` y dictamina si cada uno fue resuelto de forma completa y sin efectos secundarios:

1. **Fuga PII en Logging (`engine_manager.py` & `logging_setup.py`):**
   - ¿Se eliminó la impresión de transcripciones crudas y corregidas en el logger?
   - ¿`PIISafeFilter` evalúa ahora `record.getMessage()` en lugar de solo `record.msg`?
   - ¿Se purga `record.args = ()` al detectar contenido sensible para que ningún handler downstream lo filtre?
2. **Subsistema VAD Silero & Auto-Corte de Silencio (`recorder.py` & `main.py`):**
   - ¿Se utiliza `has_detected_speech()` en `main.py` para abortar el flujo antes de invocar a Groq si el usuario no habló?
   - ¿Existe auto-corte de silencio configurado (`silence_threshold_seconds=1.2`) que detenga la grabación tras una pausa post-habla?
3. **Parametrización de Sample Rate (`stt_cloud.py`):**
   - ¿`CloudGroqWhisperEngine` recibe y respeta `sample_rate` dinámico al generar el archivo WAV en memoria, o sigue habiendo literales fijos?
4. **Aislamiento de Pruebas Unitarias (`tests/test_injector.py`):**
   - ¿Se mockeó `ctypes.windll.user32.SendInput` para evitar inyectar pulsaciones reales de teclado (Ctrl+C / Ctrl+V) en el escritorio durante `pytest`?
5. **Ping de Autenticación Online de Groq (`app/ui/settings_window.py`):**
   - ¿Se verifica la API Key contra el endpoint de Groq con timeout estricto al guardar la configuración, alertando de inmediato si la clave arroja 401 Unauthorized?

---

## ⚡ PASO 2 — AUDITORÍA PROFUNDA DE ARQUITECTURA Y ROBUSTEZ (SIN SESGO)

Revisa exhaustivamente los 48+ archivos del proyecto en busca de:

1. **Concurrencia & Race Conditions:**
   - Inspecciona la interacción de hilos entre `AudioRecorder` (callback de `sounddevice`), `FloatingHUD` (Tkinter mainloop), `HotkeyListener` (gancho global) y los hilos de inferencia `_enqueue_processing`.
   - ¿Hay llamadas a Tkinter fuera del hilo principal que no utilicen `root.after()`?
   - ¿El mutex de instancia única (`Global\MorocoVoice_SingleInstance_Mutex`) previene efectivamente ejecuciones simultáneas?
2. **Consumo de Memoria & Fugas (Memory Leaks):**
   - ¿Los buffers de audio (`_frames`) se limpian y liberan inmediatamente tras la transcripción?
   - ¿El modelo Silero VAD en ONNX Runtime reutiliza sus estados recurrentes de memoria (`_state`, `_context`) sin fragmentar la memoria RAM?
3. **Manejo de Errores & Resiliencia en Red:**
   - Si se corta la conexión a internet a mitad del dictado con el motor `CLOUD`, ¿el sistema cae en bucle infinito o ejecuta limpiamente el fallback a `faster-whisper` local?
   - ¿Qué ocurre si la ventana activa es un proceso con privilegios elevados de Administrador (UIPI)? ¿Se emite advertencia o falla silenciosamente?

---

## 👤 PASO 3 — EXPERIENCIA DE USUARIO NO TÉCNICO ("ZERO-TOUCH")

Ponte en el lugar de un usuario con Windows 10/11 que **no sabe qué es Python, Git ni la consola**:
1. Descarga el archivo ZIP del repositorio o clona la carpeta.
2. Hace doble clic en `run.bat`. ¿El script detecta la ausencia de entorno, crea el `.venv`, valida Python 3.11+, crea `config.json` si no existe y arranca sin intervención manual?
3. ¿La interfaz de Configuración y la bandeja del sistema (System Tray) son claras, autoexplicativas y libres de tecnicismos confusos?
4. ¿El editor de Vocabulario Personalizado (límite de 30 términos) evita la sobrecarga del prompt de Whisper y permite corregir jergas sin tocar archivos JSON?

---

## 📋 PASO 4 — DICTAMEN FINAL Y CALIFICACIÓN

Genera tu informe final con la siguiente estructura obligatoria:

1. **Tabla de Estado de Brechas v1.0.1:**
   | # | Brecha Auditada | Evidencia en Código v1.0.2 | Estado (RESUELTO / PARCIAL / NO RESUELTO) |
2. **Nuevos Hallazgos o Riesgos Residuales Descubiertos:**
   - Clasificados por Severidad: CRÍTICA (Bloquea producción), MEDIA (Deuda técnica no urgente), BAJA (Mejora estética o cosmética).
3. **Evaluación de Listura para Producción:**
   - ¿Está listo para producción y distribución pública general? (SÍ / NO / CONDICIONADO).
4. **Calificación Final Ponderada (Escala 1 al 10):**
   - Justificación matemática de la calificación asignada.
