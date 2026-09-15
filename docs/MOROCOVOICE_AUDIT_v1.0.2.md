# Auditoría Maestra de Producción — MorocoVoice v1.0.2

**Auditor:** Auditor de Software Sénior / Revisor Técnico Independiente sin Sesgo
**Repositorio:** https://github.com/morocog/MorocoVoice · rama `main`
**Tag auditado:** `v1.0.2` (tag anotado `7ed6bfe`) → commit **`22111b8`**
**HEAD en el momento de la auditoría:** `6ea6986` (= `v1.0.2` + 1 commit de documentación; el código es idéntico)
**Entorno de verificación:** Windows, CPython 3.11.9 de 64 bits, Tk 8.6, `groq` 1.7.0
**Línea base:** v1.0.0 → 4.5/10 · v1.0.1 (verificada) → 7.5/10
**Calificación final de esta auditoría: 8.4 / 10**

**Método:** lectura archivo por archivo del árbol del tag + **verificación empírica ejecutada**, no inferida:
suite y linter reproducidos, auto-corte de VAD ejercitado con fragmentos sintéticos, fuga de PII reproducida contra cinco formas reales de mensaje, medición del coste de Silero, prueba de corte de red, prueba de mutación del portapapeles por `pytest`, comprobación byte a byte de codificaciones y de la API del SDK de Groq.

---

## PASO 1 — ESTADO DE LAS 5 BRECHAS DE v1.0.1

| # | Brecha auditada | Evidencia en código v1.0.2 | Estado |
|---|---|---|---|
| **1** | **Fuga PII en logging** | `engine_manager.py:197-198` ya **no** registra texto: solo `Vocabulary post-processing applied (%+d char delta).` Verificado empíricamente: ninguna transcripción llega a `morocovoice.log`. `logging_setup.py:32` usa `record.getMessage()` ✅ y `:39` purga `record.args = ()` ✅. **Pero los patrones de detección (`:37`) nunca coinciden con la forma real del mensaje** (ver §2.1) | ⚠️ **PARCIAL** |
| **2** | **VAD + auto-corte de silencio** | `main.py:162,191,204` consumen `has_detected_speech()`; `recorder.py:34,37,42,111-127` implementan el auto-corte; `main.py:70` cablea `silence_cutoff_seconds=config.silence_threshold_seconds` y `:109` lo recarga en caliente. **Ejercitado:** dispara a los 48 fragmentos = 1.22 s de silencio tras 10 fragmentos de habla (esperado 10 + 38) | ✅ **RESUELTO** |
| **3** | **Sample rate parametrizado** | `stt_cloud.py:64,69` recibe `sample_rate`; `:92` `numpy_to_wav_bytes(audio_data, sample_rate=self.sample_rate)`; `engine_manager.py:150` inyecta `config.sample_rate`. Sin literales fijos | ✅ **RESUELTO** |
| **4** | **Aislamiento de tests `SendInput`** | `test_injector.py:56,69,82` mockean `ctypes.windll.user32.SendInput` en las tres pruebas de pulsaciones ✅ (el mock intercepta de verdad: los `assert` sobre `call_count` pasan). **Pero `test_clipboard_roundtrip:25` sigue escribiendo el portapapeles real** | ⚠️ **PARCIAL** |
| **5** | **Ping online de Groq** | `settings_window.py:90-103` `verify_groq_api_key_online()` con `client.models.list()`, timeout 2.5 s, 401 → mensaje claro + opción de guardar igualmente (`:719-727`) | ✅ **RESUELTO** (con 2 reservas, §2.3) |

**Resumen del Paso 1: 3 resueltas por completo, 2 parciales.**

---

## PASO 2 — AUDITORÍA PROFUNDA DE ARQUITECTURA Y ROBUSTEZ

### 2.1 🔴 El `PIISafeFilter` no funciona: la brecha #1 está resuelta por eliminación de llamadas, no por el guardarraíl

Es el hallazgo más importante de esta auditoría. El filtro se arregló **mecánicamente** (ahora llama a `getMessage()` y purga `args`), pero sus patrones de detección están mal construidos:

```python
FORBIDDEN_KEYS = ("text", "prompt", "transcription", "llm_response", "vocabulary", "token")
# ...
if f'"{key}":' in full_msg or f"'{key}':" in full_msg or f"'{key}' ->" in full_msg:
```

El tercer patrón busca la cadena literal `'text' ->`. Pero el mensaje real produce
`Vocabulary post-processing adjusted text: '<TEXTO DEL USUARIO>' -> '<TEXTO CORREGIDO>'` — ahí `text` va seguido de `:` y **entre comillas va el contenido del usuario**, nunca la palabra `text`. El patrón no puede coincidir jamás con la fuga que dice remediar.

**Prueba ejecutada contra cinco formas de mensaje:**

| Forma del mensaje | ¿Redactado? |
|---|---|
| Fuga real de v1.0.1: `Vocabulary post-processing adjusted text: 'la reunion secreta' -> ...` | ❌ **NO** |
| Forma de v1.0.2 (delta numérico) | ✅ nada que redactar (seguro) |
| Fuga hipotética natural: `Transcription: contrasena falso-9912` | ❌ **NO** |
| `Payload {'transcription': 'contrasena'}` (repr de dict) | ✅ SÍ |
| Carga del propio test: `Result text: 'text' -> 'replaced'` | ✅ SÍ |

**Y aquí está el problema de fondo:** la prueba que certifica el filtro, `test_audio.py:64-81`, pasa **únicamente porque inyecta la palabra clave literal como carga útil**:

```python
record2 = logging.LogRecord(..., "Result text: '%s' -> '%s'", ("text", "replaced"), None)
#                                                          ^^^^^^ la carga ES la palabra "text"
```

Es una **prueba autocumplida**: valida el guardarraíl con una entrada fabricada para contener el disparador. Con una carga real (`("la reunion secreta", "la reunion secreta")`) el filtro no redacta nada, como demuestra la tabla anterior.

**Estado real de la privacidad hoy:** la auditoría confirma por `grep` que **ninguna llamada de producción registra ya texto transcrito** (las 9 coincidencias restantes registran excepciones, recuentos o nombres de archivo). Por tanto **no hay fuga activa** y el objetivo de privacidad se cumple. Pero se cumple por ausencia de llamadas, **no** por el guardarraíl. La afirmación del README —*"un filtro activo que prohíbe tajantemente registrar transcripciones crudas"*— y la de `PENDIENTES.md:14` —*"Se blindó PIISafeFilter"*— **no están respaldadas por el comportamiento del código**. Cualquier `logger.info("Transcription: %s", texto)` futuro reintroduce la fuga sin que nada la detenga.

**Severidad: MEDIA** (no hay fuga actual; se trata de una garantía de seguridad decorativa y de una afirmación de README incorrecta).

### 2.2 🟡 Concurrencia

- **Única violación de Tkinter fuera del hilo principal — introducida por v1.0.2.** `main.py:164` llama a `self.hud.hide()` **directamente** desde el hilo del gancho de teclado (`hotkey.py:234` lanza `on_dictate_toggle` en un `threading.Thread`). Los otros dos caminos nuevos del mismo commit sí lo hacen bien (`main.py:193` y `:206` usan `self.root.after(0, self.hud.hide)`), así que se trata de una inconsistencia dentro del mismo cambio.
  **Calibración honesta:** reproduje la llamada desde un hilo trabajador con `mainloop()` activo y **no lanza excepción** en CPython 3.11 / Tk 8.6 (`withdraw` y `after_cancel` desde hilo ajeno: sin excepción). No es, por tanto, un fallo determinista, sino un peligro latente que contraviene el contrato documentado de thread-safety de Tkinter y la convención del propio proyecto. **Severidad: MEDIA.**
- **Mutex de instancia única (`main.py:121-132`).** Si `CreateMutexW` devolviera `NULL`, `last_err` no sería 183 y el código guardaría `_mutex_handle = NULL` devolviendo `True`: la protección desaparecería **en silencio**. Además usa `ctypes.windll.kernel32.GetLastError()` en lugar de `ctypes.get_last_error()`, que es la forma fiable en `ctypes`. **Severidad: BAJA** (probabilidad baja, impacto bajo).
- **Correcto:** `AudioRecorder.stop()` lee y vacía `_frames` bajo una única adquisición del lock, por lo que dos llamadas concurrentes no pueden duplicar la transcripción. La mutación de `silence_cutoff_seconds` desde el hilo de Tk mientras el callback lo lee es una asignación de `float` (atómica en CPython).

### 2.3 🟡 Resiliencia y manejo de errores

- **Corte de red — verificado.** Con `cloud_engine.transcribe` lanzando `Connection reset by peer`: se registra el aviso, se ejecuta el fallback local, se aplica la corrección de vocabulario (`gitcop` → `GitHub`) y se devuelve con `engine=LOCAL`. **Sin bucle infinito.** ✅
- **Supresión de alucinaciones — verificada.** `"Gracias por ver el video"` → `text=''`, `confidence=0.0`. ✅
- **UIPI.** Advertencia por HUD (`_dispatch_uipi_alert` → `hud.show_uipi_alert`), sin fallo silencioso. ✅
- **Timeout de 15 s** en el cliente de Groq STT (`stt_cloud.py:77`). ✅
- **Reserva sobre el ping online (brecha #5):** `verify_groq_api_key_online` se invoca en `_on_save`, que corre en el **hilo principal de Tk**, y el cliente se construye **sin sobrescribir `max_retries`**. Verifiqué el SDK instalado (`groq` 1.7.0): `max_retries` por defecto = **2**. El peor caso es `2.5 s × 3 intentos = 7.5 s` de **interfaz congelada**, sin indicador de progreso. **Severidad: MEDIA.**
- **Reserva sobre el ping online (2):** en `:103`, cualquier error que no sea 401 ni de conexión (p. ej. **429 rate-limit** o **500** del servidor) devuelve `False` y la UI ofrece "¿Deseas guardarla de todas formas?" — el usuario debe saltarse una advertencia de "clave inválida" que en realidad es un problema transitorio del servicio. Debería tratarse como no concluyente, igual que el caso de timeout. **Severidad: BAJA.**

### 2.4 🟡 Memoria y fugas

- **Buffers de audio:** `_frames` se limpia en `stop()` (`recorder.py:155`) y en `start()` (`:63`). El descarte por VAD y el auto-corte pasan ambos por `stop()`, así que no quedan buffers retenidos. ✅
- **Silero:** la sesión ONNX se crea una vez; `_state` se reutiliza y se resetea en `start()` (`:71`); el estado recurrente **sí se propaga** entre llamadas (`vad.py:146-147`, verificado: el tensor muta). Coste medido: **0,197 ms por fragmento de 512 muestras frente a un presupuesto de 32 ms** → 163× de margen. **Retiro mi reserva de v1.0.1** sobre el coste de la inferencia en el callback de audio: la medición la desmiente.
- **`_context` (1,64) asignado y nunca usado** (`vad.py:50,109`; `is_speech_chunk` solo pasa `state`, `:140`). La implementación de referencia de silero-vad v5 concatena 64 muestras de contexto previo (entrada de 576) y guarda las últimas 64. Aquí se alimentan 512 sin contexto. El modelo lo acepta (la forma de entrada es dinámica, lo comprobé en la auditoría anterior), pero es una **desviación de la implementación de referencia** cuya degradación no puedo cuantificar sin audio de referencia. **Severidad: MEDIA/BAJA.**
- **Recreación de `EngineManager` en caliente:** `main.py:116-117` construye un `EngineManager` y un `SemanticRewriter` nuevos en **cada** "Guardar y Aplicar", sin liberar explícitamente el anterior. En modo LOCAL, guardar ajustes repetidamente puede duplicar de forma transitoria la RAM del modelo CTranslate2 (decenas a cientos de MB) hasta que el recolector lo libere. **Severidad: MEDIA.**

---

## PASO 3 — EXPERIENCIA DE USUARIO NO TÉCNICO ("ZERO-TOUCH")

**El flujo de arranque pedido está completo y correcto** (`run.bat`): detecta la ausencia de entorno (`:14`), **valida Python 3.11+ con un sondeo real de `sys.version_info`** (`:22,34`, no un simple `--version`), crea el `.venv` (`:52`), instala dependencias (`:62`), genera `.env` desde plantilla (`:69-74`), **genera `config.json` desde `config.example.json`** (`:76-81`) y arranca con `pythonw.exe` (`:97`). ✅

Fricciones encontradas:

| # | Fricción | Impacto |
|---|---|---|
| 1 | **El banner del instalador dice "MorocoVoice v1.0.1"** (`run.bat:8`) mientras el release es v1.0.2 — es lo primero que ve el usuario | CONFUNDE |
| 2 | **Tres números de versión distintos visibles:** bandeja "MorocoVoice **v1.0.0**" (`tray.py:67`), Configuración "**v1.0.1**" (`settings_window.py:178`), banner "**v1.0.1**" (`run.bat:8`), README badge "**v1.0.2**". Un usuario que reporte un fallo no podrá decir qué versión usa | CONFUNDE |
| 3 | Botón "📄 Editar config.json" abre **Notepad con JSON crudo** dentro de la UI del producto | CONFUNDE |
| 4 | `Win + Space` conservado: sigue colisionando con el cambio de idioma/IME de Windows; `pynput` no suprime el evento. El README no lo advierte | MOLESTA |
| 5 | Watchdog del HUD: 12 s en estado PROCESSING (`hud.py:221`) puede ocultar la cápsula antes de terminar el trabajo | MOLESTA |
| 6 | `verify_install.py` sigue **huérfano** (no lo invoca `run.bat`, no aparece en README, `pyproject.toml` ni el CI) y conserva 4 banners "VoiceFlow-Win" | BAJA (no visible) |

**Lo que sí está bien:** el editor de Vocabulario Personalizado (pestaña propia, contador `n/30` con semáforo, guardarraíl bloqueante con diálogo, botón de restauración) permite corregir jerga **sin tocar JSON**, y el README documenta la opción ZIP sin Git (`README.md:44`). El limitador de 30 términos protege correctamente el presupuesto de prompt de Whisper.

---

## PASO 4 — DICTAMEN FINAL

### 4.1 Nuevos hallazgos y riesgos residuales, por severidad

**CRÍTICA (bloquea producción): ninguna.** Las cuatro condiciones que bloqueaban en v1.0.0/v1.0.1 (modelo LLM inexistente, logging roto, PII en logs, Python incompatible) están verificadas como resueltas, y no he encontrado ninguna ruta que destruya datos del usuario sin que esté ahora documentada.

**MEDIA (deuda técnica que conviene cerrar antes de distribución general):**

| # | Hallazgo | Evidencia |
|---|---|---|
| M1 | **`PIISafeFilter` inoperante** — redacta 0 de las formas reales de fuga; la prueba que lo certifica es autocumplida | `logging_setup.py:37`, `test_audio.py:78` |
| M2 | **Inconsistencia de versión visible al usuario** (v1.0.0 / v1.0.1 / v1.0.2 simultáneamente) | `tray.py:67`, `settings_window.py:178`, `run.bat:8`, `README.md:5` |
| M3 | **Congelación de UI hasta ~7,5 s** al guardar con verificación online (`max_retries`=2 por defecto × timeout 2,5 s), en el hilo principal | `settings_window.py:94,719`; SDK `groq` 1.7.0 |
| M4 | **Llamada a Tkinter fuera del hilo principal** (`hud.hide()`), introducida en v1.0.2; no reproduce excepción en CPython 3.11/Tk 8.6 | `main.py:164` vs `:193,:206` |
| M5 | **Portapapeles: destrucción de contenido no textual** (imágenes, archivos) al dictar. Ahora **documentada**, pero sigue ocurriendo sin aviso en tiempo de ejecución | `injector.py`; `README.md:103` |
| M6 | **`EngineManager`/`SemanticRewriter` recreados en caliente sin liberar el modelo anterior** | `main.py:116-117` |
| M7 | **`_context` de Silero asignado y nunca usado** — desviación de la implementación de referencia v5 | `vad.py:50,109,140` |

**BAJA (cosmética o higiene):**

| # | Hallazgo | Evidencia |
|---|---|---|
| B1 | `PENDIENTES.md:6` declara **"Calificación estimada: 9.8 / 10"** — autoevaluación, no verificada | `PENDIENTES.md:6` |
| B2 | `PENDIENTES.md:38` declara **"[REBRANDING COMPLETO]"**: falso. Persisten "VoiceFlow-Win" en `verify_install.py` (4 banners), ~12 docstrings de módulo, `.gitignore:18,21-22` y `logging_setup.py:104` | verificado por `grep` |
| B3 | Quedan **2 pruebas vacías** con `assert True` (`test_injector.py:37,47`) | verificado |
| B4 | **La suite de tests sobrescribe el portapapeles real del usuario.** Comprobado antes/después de `pytest`: `"CLIPBOARD-DEL-USUARIO-ANTES-DE-PYTEST"` → `"VoiceFlow-Win-Test-Unicode-123_..."`, sin restaurar | `test_injector.py:22-30` |
| B5 | El test de portapapeles sigue usando la cadena de marca antigua `"VoiceFlow-Win-Test-Unicode"` | `test_injector.py:24` |
| B6 | El registro `"Vocabulary post-processing applied (+0 char delta)"` puede reportar delta 0 en una corrección real (`gitcop`→`GitHub` conserva longitud): telemetría engañosa aunque inofensiva | `engine_manager.py:197-198` |
| B7 | Mutex: no contempla `CreateMutexW` → `NULL`; usa `GetLastError()` en lugar de `ctypes.get_last_error()` | `main.py:124-125` |

**Corrección de una afirmación mía anterior.** En la revisión de v1.0.1 indiqué que `docs/MOROCOVOICE_AUDIT_v1.0.0.md` estaba "corrupto de codificación". **Era incorrecto y lo retiro.** Comprobado byte a byte: `settings_window.py`, `LICENSE`, `pyproject.toml`, `README.md` y ambos informes de `docs/` son **UTF-8 válido** (`\xf3` = ó, `\xed` = í, `\u2014` = —). El mojibake que creí ver era un artefacto de renderizado de la consola de PowerShell. No existe tal defecto. (El informe v1.0.1 que redacté no incluía esa afirmación; solo apareció en mi respuesta de chat.)

### 4.2 ¿Está listo para producción y distribución pública general?

## **CONDICIONADO**

El núcleo funcional está genuinamente listo: STT cloud con fallback local probado, VAD conectado con auto-corte verificado, corrección de vocabulario determinista, instalación zero-touch completa, CI verde y 32/32 pruebas. Ninguna ruta destruye datos sin documentar.

Se puede distribuir **tras cerrar tres condiciones de coste muy bajo**, todas de horas, no de días:

1. **Unificar la versión visible** (`run.bat:8`, `tray.py:67`, `settings_window.py:178` → `v1.0.2`). Es lo primero que verá cada usuario y hoy el producto anuncia tres versiones distintas. *(minutos)*
2. **Hacer que el filtro PII funcione de verdad** — que evalúe `record.getMessage()` contra una lista que incluya las formas reales (o, mejor, que redacte por *política*: cualquier mensaje con un `%s` cuyo argumento sea texto largo), **y corregir la prueba autocumplida**. Si no se va a arreglar, hay que suavizar la afirmación del README: hoy promete una garantía que el código no ejecuta. *(1 hora)*
3. **Sacar la verificación online de Groq del hilo de UI** (a un hilo con `root.after` de vuelta, o `max_retries=0`) y tratar 429/500 como no concluyentes. Evita que la ventana se congele hasta 7,5 s al guardar. *(1-2 horas)*

La destrucción del portapapeles no textual (M5) es la única pérdida de datos relevante, y **el propietario la ha aceptado explícitamente** como decisión de producto; ahora está documentada en `README.md:103`. Mi recomendación sería que, además de documentarla, la app **detecte** el caso (portapapeles sin `CF_UNICODETEXT`) y omita el respaldo/restauración en vez de escribir `""` — así se convierte en "no toco tu imagen" en lugar de "borro tu imagen".

### 4.3 Calificación final ponderada

| Dimensión | Peso | Nota | Aporte |
|---|:---:|:---:|:---:|
| Seguridad y privacidad | 25 % | 8.0 | 2.000 |
| Funcionalidad core (STT/LLM/VAD) | 20 % | 9.5 | 1.900 |
| Concurrencia y robustez | 15 % | 8.0 | 1.200 |
| UX no técnico e instalación | 15 % | 8.0 | 1.200 |
| Trazabilidad, versión y documentación | 15 % | 8.5 | 1.275 |
| Testing y CI | 10 % | 8.5 | 0.850 |
| **TOTAL PONDERADO** | **100 %** | | **8.425 → 8.4 / 10** |

**Justificación de cada nota:**

- **Seguridad 8.0.** La fuga real está eliminada y verificada (no hay texto en el log). Baja de 9 porque el guardarraíl que se dice haber "blindado" no redacta nada de lo que debería (M1), la prueba que lo certifica es autocumplida, y el README mantiene una promesa absoluta que el código no respalda. El portapapeles suma su parte (M5).
- **Funcionalidad 9.5.** Modelo LLM real, VAD conectado y con auto-corte **medido**, sample rate parametrizado, fallback local probado sin bucle, filtro de alucinaciones funcionando y corrector de vocabulario sin falsos positivos en español. Es el subsistema mejor resuelto del proyecto.
- **Concurrencia 8.0.** El diseño de bloqueos del audio es correcto y no hay fugas de buffers. Penalizan la llamada a Tkinter fuera de hilo introducida en esta versión (M4), la recreación sin liberación del motor (M6) y el caso `NULL` del mutex (B7).
- **UX 8.0.** El flujo zero-touch pedido está completo y es verificable. Penaliza con fuerza la inconsistencia de versión (M2), que es trivial de arreglar y muy visible, más el congelamiento de UI (M3) y el conflicto de `Win+Space`.
- **Trazabilidad 8.5.** El README es ahora notablemente honesto (latencia `~400 ms API / ~1.2 s Total`, límite de 30 términos, portapapeles declarado). Penalizan las afirmaciones no verificadas de `PENDIENTES.md` —"9.8/10", "REBRANDING COMPLETO"— y el `verify_install.py` huérfano con marca antigua.
- **Testing 8.5.** 32/32 verdes y `ruff` limpio reproducidos; el mockeo de `SendInput` es un avance real. Penalizan las 2 pruebas vacías, el test que sobrescribe el portapapeles real (B4) y, sobre todo, la prueba autocumplida del filtro PII.

**Contexto de la serie:** 4.5 → 7.5 → **8.4**. La progresión es real y verificable. La diferencia entre el 8.4 medido y el **9.8 "estimado"** que el propio repositorio se asigna en `PENDIENTES.md:6` no está en el esfuerzo —que es evidente y notable— sino en que tres de las mejoras declaradas (filtro PII, rebranding completo, consistencia de versión) **no superan la verificación empírica**. Ese es exactamente el hueco que una auditoría independiente debe medir.
