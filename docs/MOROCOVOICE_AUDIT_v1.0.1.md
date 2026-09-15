# Auditoría de Trazabilidad y Verificación Independiente — MorocoVoice v1.0.1

**Auditor:** revisor técnico independiente (sin contexto previo del proyecto)
**Repositorio:** https://github.com/morocog/MorocoVoice · rama `main` · tag `v1.0.1`
**Tag auditado:** `v1.0.1` (tag anotado `42d4d19`) → commit **`57d1a0a`**
**Tag anterior:** `v1.0.0` → `912613e`
**Entorno objetivo declarado:** Windows 10/11 x64, Python 3.11+
**Línea base:** auditoría v1.0.0 — calificación **4.5 / 10**
**Calificación de esta revisión:** **7.5 / 10**
**Método:** lectura archivo por archivo del árbol del tag + **verificación empírica** (suite ejecutada, `ruff` ejecutado, corrector de vocabulario probado contra español real, fuga de PII reproducida, árbol de git y autoría de commits inspeccionados, `raw.githubusercontent.com` consultado para confirmar el contenido del tag).

> **Nota sobre el documento que este informe sustituye.** Existía un `MOROCOVOICE_AUDIT_v1.0.1.md` autodenominado *"Revisor técnico independiente"* que otorgaba **8.6/10** y el veredicto *"Aprobado para Producción y Usuarios Externos"*. Los seis commits de `main` están firmados por `morocog <morocog@gmail.com>`, incluido el último (`57d1a0a "docs: add independent v1.0.1 traceability audit report"`). Es decir: **el informe independiente fue redactado y publicado por el propietario del proyecto**. Este documento verifica cada una de sus afirmaciones contra el código real; el §3 recoge el resultado. La mayoría se sostienen; tres no.

---

## 1. CALIFICACIÓN GLOBAL: 7.5 / 10

| Dimensión | v1.0.0 | v1.0.1 | Comentario |
|---|:---:|:---:|---|
| Funcionalidad core (STT + LLM) | 3.0 | **9.0** | Modelo LLM real, timeout 15 s, `max_tokens` dinámico. Reparado de verdad. |
| Vocabulario y precisión fonética | 2.0 | **9.0** | UI completa + corrector determinista verificado sin falsos positivos en español. |
| UI / UX y transparencia | 5.5 | **8.5** | HUD translúcida, `help_text` renderizado, detección de placeholders, README honesto. |
| Integridad de entorno y Git | 4.0 | **9.0** | Python 3.11+ forzado, `config.json` fuera de git, CI con `ruff` + `pytest`. |
| Audio y VAD | 5.0 | **5.5** | VAD **se ejecuta** pero su veredicto **nunca se consume**; coste sin beneficio. |
| Seguridad, privacidad y portapapeles | 6.0 | **5.5** | ⚠️ **Regresión**: transcripciones crudas escritas a disco. Portapapeles sigue destructivo. |
| Cobertura y deuda técnica | 4.0 | **7.0** | 28/28 tests, `ruff` limpio; persisten 4 tests vacíos y Ctrl+C sintético real. |
| **PROMEDIO** | **4.5** | **7.5** | Apto para piloto; **no** para lanzamiento externo sin cerrar §5.1. |

**Justificación en tres líneas:** el salto de 4.5 a 7.5 es real y sustancial — las diez brechas de código de la v1.0.0 fueron atendidas y el corrector de vocabulario está genuinamente bien construido. Lo que separa esta revisión del 8.6 autoasignado no es el código sino **la certificación**: (a) la sección de seguridad certifica como cumplida una garantía de privacidad que el código viola, y que la propia v1.0.1 activó; (b) se puntúa un subsistema VAD que se cableó pero no se conectó a ninguna decisión; (c) el informe se autograda sin revisión externa. La ingeniería merece un 8.5; la verificación, un 7.5.

---

## 2. ESTADO DEL REPOSITORIO VERIFICADO

| Comprobación | Resultado |
|---|---|
| `git describe --tags` | `v1.0.1` ✅ |
| Árbol de trabajo | Limpio (sin cambios pendientes) ✅ |
| Tag `v1.0.1` | Anotado (`42d4d19`) → commit `57d1a0a` |
| Suite de pruebas | **28/28 pasan** en 1.09 s ✅ |
| `ruff check app tests` (lo que ejecuta el CI) | **All checks passed!** (exit 0) ✅ |
| CI | `.github/workflows/ci.yml` — `windows-latest`, Python 3.11, `ruff` + `pytest` ✅ |
| `config.json` versionado | **Eliminado de git** (`D config.json`); en `.gitignore`; `run.bat:76-79` lo genera desde `config.example.json` ✅ |
| Huella en disco (`.venv`) | ~388 MB medidos, coherente con la promesa `<450 MB` (excluye pesas de Whisper) |

**Archivos nuevos/modificados vs v1.0.0:** `.github/workflows/ci.yml` (nuevo), 20 archivos modificados, `config.json` eliminado, `custom_vocabulary.json` saneado, `docs/MOROCOVOICE_AUDIT_v1.0.0.md` y `docs/MOROCOVOICE_AUDIT_v1.0.1.md` añadidos.

---

## 3. LEDGER DE VERIFICACIÓN DEL AUTO-INFORME v1.0.1

Todas las afirmaciones del informe sustituido, comprobadas contra el código del tag.

| # | Afirmación del auto-informe | Evidencia en código | Veredicto |
|---|---|---|---|
| 1 | Modelo LLM reparado (`llama-3.1-8b-instant`) | `contracts.py:88`, `config.example.json`, `settings_window.py:361` | ✅ CIERTO |
| 2 | Tag `v1.0.1` publicado sobre `main` | Tag anotado → `57d1a0a`; pero el informe declara `8dd1712` | ⚠️ PARCIAL (§5.3) |
| 3 | Namespace de logging corregido | `logging_setup.py:90` → `morocovoice.{name}` | ✅ CIERTO |
| 4 | Python 3.11+ unificado | `run.bat:22,34` (sondeo real de `sys.version_info`), `pyproject.toml:6`, badge README | ✅ CIERTO |
| 5 | `is_valid_groq_api_key()` bloquea placeholders | `config.py:41-48`; usado en `main.py:359-361` y `settings_window.py:697` | ✅ CIERTO |
| 6 | Portapapeles conservado por decisión | `injector.py` sin cambios de formato | ⚠️ CIERTO pero mal calificado (§6.1) |
| 7 | `Win + Space` conservado | `config.example.json` | ⚠️ CIERTO pero mal calificado (§6.2) |
| 8 | HUD translúcida | `hud.py:87` `attributes("-alpha", 0.92)` | ✅ CIERTO |
| 9 | VAD activado en `_audio_callback` | `recorder.py:94-96` invoca `is_speech_chunk` | ⚠️ SE EJECUTA, NO SE USA (§5.2) |
| 10 | `max_tokens` dinámico | `rewriter.py:151` `min(2048, max(500, int(prompt_words * 2.5)))` | ✅ CIERTO |
| 11 | `stt_language` configurable | `contracts.py:98`, `settings_window.py:276-319,669,737`, `engine_manager.py:149,156,169` | ✅ CIERTO |
| 12 | `config.json` protegido en `.gitignore` | Eliminado de git, ignorado, regenerado por `run.bat` | ✅ CIERTO |
| 13 | API key enmascarada | `settings_window.py` campo `show="*"` + toggle | ✅ CIERTO |
| 14 | API key en `.env`, excluida por git | `.gitignore:25`; `_persist_groq_api_key_to_env` | ✅ CIERTO |
| 15 | **Logs libres de PII con filtro activo** | `engine_manager.py:196` escribe la **transcripción cruda** a `morocovoice.log` | ❌ **FALSO** (§5.1) |
| 16 | Detección de placeholders | `config.py:41-48` | ✅ CIERTO |
| 17 | `Win + Space` funcional | `hotkey.py` | ✅ CIERTO |
| 18 | `Ctrl + Shift + Space` funcional | `main.py` | ✅ CIERTO |
| 19 | Auto-corte 60 s | `recorder.py:106-112` | ✅ CIERTO |
| 20 | Bandeja: logs y apagado seguro | `tray.py` | ✅ CIERTO |
| 21 | ZIP sin terminal documentado | `README.md:44` "Opción A (Directa, sin Git)" | ✅ CIERTO |
| 22 | Apertura de Configuración solo sin clave válida | `main.py:359-361` | ✅ CIERTO |
| 23 | Ayuda inline renderizada | `settings_window.py:560-563` y `636-639` | ✅ CIERTO |
| 24 | Pestaña de vocabulario con `tk.Text` | `settings_window.py:194` | ✅ CIERTO |
| 25 | Contador en tiempo real con semáforo | `settings_window.py:408,500-506` | ✅ CIERTO |
| 26 | Guardarraíl preventivo >30 con diálogo | `settings_window.py:705-714` (`askyesno`) | ✅ CIERTO |
| 27 | Vocabulario saneado a 30 términos estándar | `custom_vocabulary.json`: jerga privada eliminada | ✅ CIERTO |
| 28 | Corrector determinista en dos capas | `engine_manager.py:31-40` (mapa duro) + `:96-131` (`difflib`, stopwords) | ✅ CIERTO |
| 29 | Botón de restauración | `settings_window.py:417` "↩ Restaurar recomendados" | ✅ CIERTO |
| 30 | Latencia declarada `~400 ms API / ~1.2 s Total` | `README.md:9,30` | ✅ CIERTO |
| 31 | 28/28 tests | Reproducido: `28 passed` | ✅ CIERTO |
| 32 | Linter `ruff` validado | Reproducido: `All checks passed!` | ✅ CIERTO |
| 33 | CI en GitHub Actions | `.github/workflows/ci.yml` | ✅ CIERTO |

**Resultado: 29 ciertas, 3 parciales/mal calificadas, 1 falsa.**

---

## 4. TRAZABILIDAD README ↔ CÓDIGO (v1.0.1)

| # | Promesa del README | Evidencia | Estado | Riesgo |
|---|---|---|---|---|
| 1 | Latencia `~400 ms API / ~1.2 s Total` | `README.md:9,30`; pipeline de 2 saltos en `main.py:222` | ✅ CUMPLE | BAJO |
| 2 | Reescritura contextual por ventana | `prompt_templates.py` (outlook/teams/slack/code), `context.py:91`, LLM `llama-3.1-8b-instant` | ✅ CUMPLE | BAJO |
| 3 | `Win + Space` dictado | `hotkey.py`, `config.example.json` | ⚠️ PARCIAL | MEDIO |
| 4 | `Ctrl + Shift + Space` reescritura | `main.py`; `max_tokens` dinámico evita truncamiento | ✅ CUMPLE | BAJO |
| 5 | Cloud `whisper-large-v3-turbo` / Local int8 | `config.example.json`, `stt_local.py`, `engine_manager.py:152-157` | ✅ CUMPLE | BAJO |
| 6 | Corrector `difflib` evita `GITCOP` | `engine_manager.py:32` + `:96-131`; **probado sin falsos positivos** | ✅ CUMPLE | BAJO |
| 7 | **Logs libres de PII** (`README.md:102`) | `engine_manager.py:196` escribe la transcripción cruda al log | ❌ **NO CUMPLE** | **ALTO** |
| 8 | **Inyección "no Destructiva"** (`README.md:103`) | `injector.py` solo `CF_UNICODETEXT`: imágenes/archivos se pierden | ❌ **NO CUMPLE** | **ALTO** |
| 9 | UIPI | `context.py:37-64`, `main.py` | ✅ CUMPLE | BAJO |
| 10 | Instalación zero-touch + ZIP | `run.bat` valida 3.11+, `.venv`, deps; `README.md:44` ZIP | ✅ CUMPLE | BAJO |
| 11 | Python 3.11+ | `run.bat:22,34`, `pyproject.toml:6`, badge | ✅ CUMPLE | BAJO |
| 12 | Botón 1-clic Groq | `settings_window.py` | ✅ CUMPLE | BAJO |
| 13 | HUD translúcida | `hud.py:87` | ✅ CUMPLE | BAJO |
| 14 | Vocabulario personalizable con UI y límite 30 | `settings_window.py:194,390,408,705-714`, `README.md:67-69` | ✅ CUMPLE | BAJO |
| 15 | Zero PyTorch | Sin `torch` en `.venv` ni requirements | ✅ CUMPLE | BAJO |
| 16 | Huella < 450 MB | ~388 MB medidos (sin pesas de Whisper) | ✅ CUMPLE | BAJO |
| 17 | Windows 10/11 x64 | Uso Win32; no probado en Win10 | ✅ CUMPLE | BAJO |
| 18 | 28 tests | Reproducido | ✅ CUMPLE | BAJO |
| 19 | VAD Silero ONNX | `recorder.py:94-96` ejecuta; `has_detected_speech()` nunca se llama | ⚠️ PARCIAL | MEDIO |
| 20 | Mutex instancia única | `main.py` `Global\MorocoVoice_SingleInstance_Mutex` | ✅ CUMPLE | BAJO |

**Resumen: 17 ✅ · 3 ⚠️ · 2 ❌**

---

## 5. HALLAZGOS NUEVOS NO CUBIERTOS POR EL AUTO-INFORME

### 5.1 🔴 Fuga de PII en el log — **regresión introducida por la propia v1.0.1**

`app/engine/engine_manager.py:196`:

```python
logger.info("Vocabulary post-processing adjusted text: '%s' -> '%s'", raw_result.text, corrected_text)
```

Registra la **transcripción cruda del usuario**. En v1.0.0 el namespace roto hacía que esta línea no llegara a ningún sitio; **al corregir el namespace (que era lo correcto) se activó la fuga**. Reproducción exacta del camino real:

```
--- morocovoice.log ---
2026-09-14 17:29:24 [INFO] [MainThread] morocovoice.engine_manager: Vocabulary
  post-processing adjusted text: 'la reunion con el cliente sera el martes y mi
  contrasena temporal es falso-9912' -> 'la reunion con el cliente ...'
```

El dictado completo queda escrito en disco, en un archivo rotativo de 5 MB × 3, en el directorio de trabajo de la aplicación.

**Contradice directamente:** `README.md:102` — *"un filtro activo que **prohíbe tajantemente registrar transcripciones crudas, prompts o textos de usuario**"*. En una herramienta orientada a WFM/call center, donde el contenido dictado es material de negocio sensible, esto no es un detalle cosmético.

**Por qué el filtro no lo detiene.** `PIISafeFilter` (`logging_setup.py:29-36`) inspecciona `record.msg`, que es la **plantilla de formato** (`"...adjusted text: '%s' -> '%s'"`) — nunca los argumentos ya interpolados. Es estructuralmente incapaz de ver el texto. **Cualquier** llamada `logger.x("... %s", texto_usuario)` lo esquiva. La salvaguarda es decorativa.

**Corrección (una línea + endurecer el filtro):**
```python
# engine_manager.py — registrar solo metadatos, nunca el texto
logger.info("Vocabulary post-processing applied (%d chars adjusted).",
            sum(1 for a, b in zip(raw_result.text.split(), corrected_text.split()) if a != b))
```
```python
# logging_setup.py — que el filtro sí vea el mensaje final
def filter(self, record):
    final = record.getMessage()          # incluye los args interpolados
    if any(k in final.lower() for k in ("adjusted text:", "transcripci")):
        record.msg, record.args = "[REDACTED_PII_PAYLOAD]", ()
    return True
```

### 5.2 🟡 VAD: se ejecuta, pero su veredicto no se consume

`recorder.py:150` define `has_detected_speech()`. Una búsqueda en todo el repositorio (`*.py`) devuelve **únicamente esa definición**: nadie la llama. Consecuencias:

- `is_speech_chunk()` ejecuta **inferencia ONNX real de Silero en cada fragmento de 32 ms**, dentro del hilo de callback de `sounddevice` — el punto más sensible a latencia del sistema. Un callback lento provoca descarte de buffers de entrada.
- El resultado se acumula en `_speech_chunks_count` y **no influye en ninguna decisión**: ni auto-corte, ni descarte de silencio, ni filtrado VAD hacia Whisper (`vad_filter=False` en `stt_local.py`).

El propio auto-informe lista el auto-corte por silencio como pendiente para v1.1.0, lo que confirma que el VAD aún no tiene efecto funcional. **Puntuar "Audio & VAD 5.0 → 8.5" no está respaldado por el código**: es un 8.5 hacia una función que no está conectada. O se consume el veredicto (auto-stop con `silence_threshold_seconds`, que ya existe en la config), o se deja de calcular por fragmento — pero no ambas cosas.

### 5.3 🟡 El commit auditado declarado es incorrecto

El auto-informe afirma *"`8dd1712` (HEAD de `main`, tag `v1.0.1`)"*. El tag apunta a **`57d1a0a`**; `8dd1712` es su **padre**. El informe se redactó contra el commit anterior y no se revalidó contra el tag que dice auditar.

### 5.4 🟢 Restos menores

- `stt_cloud.py:85` sigue con `numpy_to_wav_bytes(audio_data, sample_rate=16000)` **hardcodeado**: ignora `config.sample_rate`. Si se cambia la tasa en la config, la cabecera WAV queda mal etiquetada (audio acelerado/agudo).
- `.gitignore:18,21-22` conserva el encabezado `# VoiceFlow / MorocoVoice` y las entradas `voiceflow.log` / `voiceflow.log.*`. Cosmético.
- `custom_vocabulary.json` en el tag v1.0.1 **sí** contiene `"GitHub"` y ya no contiene jerga privada (`El Panóptico`, `Smart Time Blocks`, `Telat Group`, `rgarcia`) — la corrección respecto a v1.0.0 es real y verificada contra GitHub.

---

## 6. BRECHAS RETENIDAS POR DECISIÓN EXPLÍCITA

Ambas están declaradas con honestidad en el auto-informe. Mi desacuerdo es con **cómo se califican**, no con que existan.

### 6.1 Portapapeles destructivo — marcado como "mal menor", es pérdida de datos

`get_clipboard_text()` lee solo `CF_UNICODETEXT`. Si el usuario tiene **una imagen o archivos** copiados, la copia de seguridad es `""` y la restauración escribe `""`: **el contenido se destruye de forma silenciosa e irreversible**. `context.py` repite el patrón y además vacía el portapapeles antes de simular Ctrl+C, sin restaurarlo cuando no había texto.

`README.md:103` sigue prometiendo *"Inyección por Fases **no Destructiva**"*. Copiar un archivo y dictar lo pierde. Esto no es un compromiso de funcionalidad, es destrucción de datos del usuario: o se respaldan todos los formatos presentes, o se aborta el uso del portapapeles y se avisa.

### 6.2 Conflicto de `Win + Space`

Mantener el atajo es una decisión legítima del propietario. El conflicto con el cambio de idioma/IME de Windows es real y `pynput` no suprime el evento, así que la distribución del teclado puede cambiar en cada dictado. El README aún presenta los atajos como diseñados "con protección contra conflictos". Basta con documentarlo.

---

## 7. DEUDA TÉCNICA RESTANTE

| Ítem | Ubicación | Estado |
|---|---|---|
| 4 tests sin aserción real (`assert True`) | `tests/test_injector.py:37,47,55,63` | Auto-declarado como pendiente |
| Ctrl+C sintético real durante la suite | `tests/test_injector.py` (`test_send_ctrl_c_executes_safely`) | Auto-declarado; puede copiar/interrumpir en la ventana enfocada |
| Sin validación **online** de la clave al guardar | `settings_window.py:_on_save` | Auto-declarado; solo valida forma (`gsk_`, ≥20 chars) |
| Sin auto-corte por silencio | `recorder.py` | Auto-declarado; `silence_threshold_seconds` sin usar |
| Sin aceleración CUDA | `engine_manager.py:154` `device="cpu"` fijo | Auto-declarado |
| VAD sin consumidor | `recorder.py:150` | **No detectado por el auto-informe** |
| Fuga de PII | `engine_manager.py:196` | **No detectado por el auto-informe** |

**Cobertura de tests.** Los +2 tests (26 → 28) se concentran en `test_engine.py` y `test_settings.py`. Siguen **sin cobertura** las rutas donde históricamente han aparecido los fallos: `inject_text()` completo, la restauración asíncrona del portapapeles, `get_selected_text()`, `numpy_to_wav_bytes()`, `load_config()`, `recorder.py`, `_on_save()` y la UI.

---

## 8. LO QUE FUNCIONA BIEN (reconocimiento debido)

Sería injusto cerrar sin señalar lo que está genuinamente bien hecho:

1. **El corrector de vocabulario es de calidad profesional.** `engine_manager.py:71-131` combina un mapa de homófonos duros, coincidencia difusa con `difflib` acotada por umbral (0.85) **y** por diferencia de longitud (≤2), y una lista de stopwords del español que protege las palabras comunes. **Lo probé contra diez frases reales** y ninguna palabra legítima fue alterada: las únicas reescrituras fueron restauración correcta de mayúsculas (`nice`→`NICE`, `dashboard`→`Dashboard`, `forecasting`→`Forecasting`). Es exactamente la defensa contra falsos positivos que yo habría pedido en v1.0.0.
2. **La honestidad del README.** Corregir el titular de latencia a `~400 ms API / ~1.2 s Total`, alineado con la medición del propio autor, es lo que hace un buen responsable de proyecto. Se documentó además el ZIP sin git, el límite de 30 términos y la pestaña de vocabulario.
3. **El CI es real y pasa.** No es decorativo: verifiqué localmente los mismos comandos que ejecuta (`ruff check app tests`, `pytest`) sobre `windows-latest` y ambos son verdes.
4. **`config.json` fuera de git con regeneración desde plantilla** resuelve limpiamente el conflicto de `git pull` que señalé en v1.0.0.
5. **La UI de vocabulario implementa los cuatro elementos que recomendé**: pestaña propia, contador en vivo, guardarraíl bloqueante con diálogo, y botón de restauración.

---

## 9. ROADMAP PRIORIZADO PARA ALCANZAR 10 / 10

1. **Eliminar la fuga de PII (bloqueante para lanzamiento, ~30 minutos).** Quitar `raw_result.text` de `engine_manager.py:196` y hacer que `PIISafeFilter` opere sobre `record.getMessage()` incluyendo `record.args`. Añadir un test que afirme que ninguna transcripción aparece en el log. Sin esto, la sección de privacidad del README es falsa y así queda certificada.
2. **Cerrar la contradicción del portapapeles (~1 día).** Respaldar y restaurar todos los formatos presentes (`CF_UNICODETEXT`, `CF_DIB`/`CF_BITMAP`, `CF_HDROP`), o abstenerse de usar el portapapeles y avisar cuando haya formatos no soportados. Nunca escribir `""`.
3. **Conectar o retirar el VAD (~1 día).** Consumir `has_detected_speech()` para el auto-corte por silencio con `silence_threshold_seconds`, y sacar la inferencia del hilo de callback (encolarla a un worker). Si no se va a consumir, dejar de calcularla por fragmento.
4. **Reescribir los 4 tests vacíos y mockear `SendInput`** para que la suite no inyecte Ctrl+C real en la máquina de quien la ejecuta.
5. **Validación online de la clave con timeout de 2 s** y error explícito en `_on_save`, para que no se pueda confirmar un guardado con una clave rechazada.

---

## 10. CONCLUSIÓN

MorocoVoice v1.0.1 es un producto **cualitativamente distinto** de v1.0.0. Las diez brechas de código que bloqueaban el lanzamiento fueron atendidas con rigor verificable, el corrector de vocabulario convierte la feature estrella de probabilidad en garantía, y la documentación dejó de prometer lo que el código no hacía. Es un salto de 4.5 a 7.5 y merece reconocerse.

Lo que impide llamarlo listo para producción no es una lista larga: son **dos contradicciones entre lo que el README promete y lo que el código hace** — una fuga de transcripciones al log que la propia v1.0.1 activó, y un portapapeles que destruye imágenes y archivos. La primera tiene arreglo de media hora. La segunda exige una decisión de producto, no más código. Cerradas ambas, y con el VAD conectado o retirado, este proyecto está legítimamente en 9+. El 8.6 autoasignado no era inalcanzable: solo estaba certificado antes de verificarse.
