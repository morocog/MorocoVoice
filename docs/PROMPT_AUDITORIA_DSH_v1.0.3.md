# PROMPT MAESTRO PARA DSH — AUDITORÍA FINAL DE PRODUCCIÓN MOROCOVOICE v1.0.3
## (Copia y pega este contenido directamente en DeepSeek Harness)

---

Actúa como **Auditor de Software Sénior y Revisor Técnico Independiente sin Sesgo**. En tu auditoría anterior de la versión v1.0.2 asignaste una calificación ponderada de **8.4 / 10** (con **9.5 / 10** en funcionalidad Core: STT/LLM/VAD) y emitiste un dictamen **"CONDICIONADO"** a la resolución de 3 puntos de bajo coste:
1. Unificar las versiones visibles en UI/CLI.
2. Blindar el filtro `PIISafeFilter` con patrones de fuga real y sustituir la prueba autocumplida.
3. Evitar el congelamiento de UI en el ping de Groq (`max_retries=0`) y tratar 429/500 como estados no concluyentes.

El equipo de desarrollo ha publicado la versión **`v1.0.3`** atendiendo quirúrgicamente tus observaciones. Tu objetivo en esta sesión es verificar empíricamente cada corrección y emitir la calificación definitiva de listura para producción masiva.

---

## 📌 DECISIONES INMUTABLES DEL AUTOR DEL PRODUCTO (NO AUDITAR COMO DEFECTO)

Antes de auditar, toma en cuenta que el autor del proyecto (**Ricardo García**) ha ratificado de forma explícita y definitiva dos decisiones de diseño de producto:
1. **Atajo `Win + Space`:** Se conserva firmemente como atajo principal de dictado por ser su preferencia ergonómica comprobada en su flujo operativo real.
2. **Portapapeles con `Ctrl+V` y disponibilidad en `Win + V`:** El comportamiento actual de inyección de texto plano (`CF_UNICODETEXT`) se mantiene tal cual está planteado. El autor y sus usuarios no tienen inconveniente en que el texto dictado quede disponible en el historial de Windows (`Win + V`).

---

## 🎯 METADATOS DEL REPOSITORIO AUDITADO

- **Repositorio público:** [https://github.com/morocog/MorocoVoice](https://github.com/morocog/MorocoVoice)
- **Rama objetivo:** `main`
- **Tag auditado:** `v1.0.3`
- **Entorno operativo declarado:** Windows 10 / 11 x64, Python 3.11+
- **Historial de auditorías previas (en el repo):**
  - `docs/MOROCOVOICE_AUDIT_v1.0.0.md` (4.5 / 10)
  - `docs/MOROCOVOICE_AUDIT_v1.0.1.md` (7.5 / 10)
  - `docs/MOROCOVOICE_AUDIT_v1.0.2.md` (8.4 / 10)

---

## 🔍 PASO 1 — VERIFICACIÓN EMPÍRICA DE LAS 3 CONDICIONES DE v1.0.2

Inspecciona el código en `v1.0.3` y verifica si cada condición fue satisfecha:

1. **Unificación Homogénea de Versión Visible:**
   - Verifica que todas las superficies visibles anuncien de forma idéntica **`v1.0.3`**:
     - `run.bat:8` (Banner de inicio)
     - `app/ui/tray.py:67` (Menú de la bandeja del sistema)
     - `app/ui/settings_window.py:178` (Encabezado de la ventana de Ajustes)
     - `pyproject.toml:3` (`version = "1.0.3"`)
     - `README.md:5` (Badge de versión)
     - `verify_install.py:205` (Diagnóstico CLI)
2. **Blindaje Real de `PIISafeFilter` & Prueba no Autocumplida:**
   - Inspecciona `app/logging_setup.py:24-60`. ¿`PIISafeFilter` evalúa ahora prefijos de fuga real (`adjusted text:`, `result text:`, `transcription:`, `raw text:`) y formatos de diccionario?
   - Inspecciona `tests/test_audio.py:64-105`. ¿La prueba valida ahora una frase confidencial realista del usuario (ej: `"la reunion confidencial de las 5"`) en lugar del disparador artificial `("text", "replaced")`?
3. **Resiliencia en Ping de Groq y Tkinter Thread-Safety:**
   - En `app/ui/settings_window.py:90-110`: ¿`verify_groq_api_key_online` utiliza `max_retries=0` para evitar multiplicadores de espera? ¿Se tratan los errores 429 (rate-limit) y 500/503 como avisos transitorios no bloqueantes?
   - En `app/main.py:164`: ¿Se enruta `hud.hide()` mediante `self.root.after(0, self.hud.hide)` al descartar sesiones sin voz para cumplir 100% el contrato de hilos de Tkinter?
4. **Higiene de Tests:**
   - En `tests/test_injector.py`: ¿`test_clipboard_roundtrip` respalda y restaura el portapapeles original del desarrollador para no ensuciarlo durante `pytest`? ¿Se sustituyeron los `assert True` por aserciones reales?
   - En `verify_install.py`: ¿Se eliminaron los residuos de nombres obsoletos?

---

## 📊 PASO 2 — RE-EVALUACIÓN PONDERADA Y CALIFICACIÓN FINAL

Actualiza tu tabla ponderada de las 6 dimensiones (100%):

| Dimensión | Peso | Nota v1.0.2 | Nota v1.0.3 | Justificación del cambio |
|---|:---:|:---:|:---:|---|
| Seguridad y privacidad | 25 % | 8.0 | [ ] | |
| Funcionalidad core (STT/LLM/VAD) | 20 % | 9.5 | [ ] | |
| Concurrencia y robustez | 15 % | 8.0 | [ ] | |
| UX no técnico e instalación | 15 % | 8.0 | [ ] | |
| Trazabilidad, versión y documentación | 15 % | 8.5 | [ ] | |
| Testing y CI | 10 % | 8.5 | [ ] | |
| **TOTAL PONDERADO** | **100 %** | **8.4** | **[ ]** | |

---

## 🏁 PASO 3 — DICTAMEN DEFINITIVO

Responde con total claridad:
1. ¿El proyecto pasa formalmente de **CONDICIONADO** a **APROBADO PARA PRODUCCIÓN GENERAL**?
2. Si resta alguna deuda técnica menor (nivel bajo/cosmético), lístala como backlog futuro para v1.1.0 sin que bloquee el lanzamiento actual.
