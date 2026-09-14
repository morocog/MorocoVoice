# Auditoría de Trazabilidad — MorocoVoice v1.0.0

**Auditor:** revisor técnico independiente (sin contexto previo del proyecto)
**Repositorio:** https://github.com/morocog/MorocoVoice · rama `main` · tag `v1.0.0`
**Commit auditado:** `8bd0ae9` (HEAD de `main`) y tag `v1.0.0` = `912613e`
**Entorno objetivo declarado:** Windows 10/11 x64, Python 3.10+
**Método:** lectura archivo por archivo de los 48 archivos versionados + **verificación empírica** (ejecución de la suite, inspección del modelo ONNX, medición del `.venv`, prueba de logging en vivo, consulta a la API/raw de GitHub).

---

## ⚠️ HALLAZGO PREVIO CRÍTICO: el tag `v1.0.0` NO contiene el código de `main`

`v1.0.0` es ancestro de `main` y **está un commit por detrás**:

```
8bd0ae9 fix: replace VoiceFlow with GitHub in vocabulary, trim to exactly 30 terms   <- main
912613e release: v1.0.0 initial public release ...                                  <- tag v1.0.0
```

Verificado contra GitHub en vivo:

| Archivo | `main` (raw GitHub) | tag `v1.0.0` (raw GitHub) |
|---|---|---|
| `custom_vocabulary.json` término 1 | `"GitHub"` | **`"VoiceFlow"`** |
| Términos | 30 | 30 |

**Consecuencia:** quien descarga el Release/ZIP `v1.0.0` —el artefacto "oficial"— obtiene un vocabulario que **sesga a Whisper hacia la marca equivocada ("VoiceFlow") y NO contiene "GitHub"**. Esto es exactamente la causa raíz del fallo reportado `GitHub → "GITCOP"`. **El fix existe en `main` pero no en la versión publicada.** La auditoría siguiente evalúa `main` salvo donde se indique lo contrario.

---

## PASO 1 — CHECKLIST DE PROMESAS DEL README

### Funcionalidad
1. Latencia STT **~400 ms** (badge + tabla comparativa)
2. Reescritura contextual **automática según ventana** (Outlook, Slack, Teams, VS Code)
3. **`Win + Space`** = Dictado Inteligente (toggle + HUD + inyección en app activa)
4. **`Ctrl + Shift + Space`** = Reescritura de la selección
5. Cloud STT: `whisper-large-v3-turbo` (~400 ms)
6. Cloud LLM: `qwen/qwen3.8-27b` o `llama-3.3-70b-versatile`
7. Modo Local Offline: `faster-whisper` int8, CTranslate2 AVX2/AVX512
8. Fallback semántico local con **Ollama** (`localhost:11434`)
9. Auto-corte de grabación (implícito, 60 s)
10. Ver logs desde la bandeja del sistema
11. Cerrar la aplicación limpiamente desde la bandeja

### Seguridad
12. API key **enmascarada con asteriscos** en la UI
13. API key almacenada en **`.env`**, estrictamente excluido por `.gitignore`
14. **Logs libres de PII**: filtro activo que prohíbe registrar transcripciones/prompts/textos
15. Solo se auditan **tiempos de latencia y nombres de procesos activos**
16. **Inyección no destructiva**: `SendInput` + liberación de modificadores + respaldo del portapapeles con `RLock` + restauración a los 120 ms
17. **Compatibilidad UIPI**: detecta ventana destino elevada para evitar fallos silenciosos

### UX
18. Instalación **"Zero-Touch"** con doble clic en `run.bat` (crea `.venv`, instala deps, arranca)
19. "No necesitas compilar modelos pesados **ni pelear con comandos de terminal**"
20. Botón **1-clic** "Obtener clave gratuita en console.groq.com" bajo el campo de clave
21. La ventana de Configuración se abre **"al arrancar por primera vez"**
22. Botón **"Guardar y Aplicar"** → listo
23. HUD flotante **translúcida** que indica `Escuchando...`
24. Instalación en **3 pasos** (clonar con `git clone`)
25. Suite de **26 tests** ejecutable con `.\.venv\Scripts\pytest -v`

### Arquitectura
26. **Zero PyTorch**
27. Huella **< 450 MB**
28. Windows 10/11 x64 nativo
29. **Python 3.10+** (badge "Python 3.10 | 3.11"; `pyproject` `requires-python = ">=3.10"`)
30. Licencia **MIT**
31. **VAD Silero ONNX** como parte de la arquitectura
32. **Mutex de instancia única** en `app/main.py`
33. Estructura del proyecto publicada y exacta
34. Rebranding completo a **MorocoVoice v1.0.0**

### Vocabulario personalizado
35. `custom_vocabulary.json` — "Vocabulario especializado (jerga técnica, nombres)", personalizable
36. El vocabulario personalizado **se aplica** a la transcripción

---

## PASO 2 y 3 — REPORTE DE TRAZABILIDAD

| # | Promesa del README | Evidencia en Código | Estado | Riesgo |
|---|---|---|---|---|
| 1 | Latencia STT ~400 ms | `stt_cloud.py:81-100` mide solo la llamada HTTP. `docs/PENDIENTES.md:9` — **medición del propio autor: "~1.2s de latencia"**. `main.py:222` añade 2ª llamada LLM por dictado | ❌ NO CUMPLE | **ALTO** |
| 2 | Reescritura contextual por ventana | `prompt_templates.py:10-21` (outlook/teams/slack/code ✅), `context.py:91` ✅. **Pero** el modelo LLM de `config.json:6` no existe → `rewriter.py:160-161` falla y `rewrite_selection` devuelve `success=False` | ⚠️ PARCIAL | **ALTO** |
| 3 | `Win + Space` dictado | `hotkey.py:193-235`, `config.json:2`, test `test_hotkey.py:27` ✅. **Colisiona con el atajo nativo de Windows** (cambio de idioma/IME) | ⚠️ PARCIAL | **ALTO** |
| 4 | `Ctrl+Shift+Space` reescritura | `config.json:3`, `main.py:248-288` ✅. Mismo fallo de modelo + riesgo de destruir la selección | ⚠️ PARCIAL | **ALTO** |
| 5 | Cloud STT `whisper-large-v3-turbo` | `config.json:5`, `stt_cloud.py:87-96` ✅ | ✅ CUMPLE | BAJO |
| 6 | Cloud LLM `qwen/qwen3.8-27b` | `config.json:6` y `settings_window.py:222`. **Modelo inexistente en Groq** → 404 en cada llamada | ❌ NO CUMPLE | **ALTO** |
| 7 | Local `faster-whisper` int8 | `engine_manager.py:78-82` (`device="cpu"`, `int8`), `stt_local.py:107-112` ✅. Sin CUDA (`PENDIENTES.md:18` lo admite) | ✅ CUMPLE | MEDIO |
| 8 | Fallback Ollama | `rewriter.py:66-77`, `163-186` ✅ (timeout 500 ms health / 5 s inferencia) | ✅ CUMPLE | MEDIO |
| 9 | Auto-corte 60 s | `recorder.py:94-98`; HUD watchdog `hud.py:220` | ✅ CUMPLE | BAJO |
| 10 | Ver logs desde bandeja | `tray.py:72` existe… pero **el log está vacío** (§ bug de logging) | ❌ NO CUMPLE | **ALTO** |
| 11 | Salir limpio desde bandeja | `tray.py:73`, `main.py:302-340` (shutdown ordenado + watchdog 2 s) ✅ | ✅ CUMPLE | BAJO |
| 12 | API key enmascarada | `settings_window.py:388` `show="*"`, toggle 👁️ `:394-417` ✅ | ✅ CUMPLE | BAJO |
| 13 | Key en `.env`, ignorada por git | `settings_window.py:24-54,480-485` → escribe `.env`; `.gitignore:25` `.env`. **`config.json` NO contiene la key** ✅ | ✅ CUMPLE | BAJO |
| 14 | Logs libres de PII (filtro activo) | `PIISafeFilter` (`logging_setup.py:24-36`) se adjunta al logger `"morocovoice"` (`:50`), pero los módulos usan `"voiceflow.*"` (`:90`) → **el filtro nunca ve los registros reales** | ❌ NO CUMPLE | **ALTO** |
| 15 | Solo se auditan latencias/procesos | El logging no llega al archivo (verificado empíricamente) → **no se audita nada** | ❌ NO CUMPLE | **ALTO** |
| 16 | Inyección no destructiva del portapapeles | RLock `injector.py:83` ✅, 3 fases `:189-251` ✅, restauración `:303-325` ✅. **Pero solo texto** (`CF_UNICODETEXT`): imágenes/archivos se **pierden** | ⚠️ PARCIAL | **ALTO** |
| 17 | Compatibilidad UIPI | `context.py:37-64`, `main.py:162-166,253-257`, `hud.py:233-236` ✅ | ✅ CUMPLE | BAJO |
| 18 | Zero-Touch `run.bat` | `run.bat:14-78` crea `.venv`+instala+lanza ✅, pero **no instala Python**, no valida versión, y el paso 1 exige `git` | ⚠️ PARCIAL | MEDIO |
| 19 | "Sin pelear con la terminal" | Paso 1 del README es `git clone` en terminal; editar vocabulario exige abrir JSON | ❌ NO CUMPLE | MEDIO |
| 20 | Botón 1-clic Groq | `settings_window.py:199-211`, `webbrowser.open("https://console.groq.com/keys")` ✅ | ✅ CUMPLE | BAJO |
| 21 | Settings "por primera vez" | `main.py:359` `app.open_settings()` se ejecuta **siempre**; ventana `-topmost` (`:88`) | ⚠️ PARCIAL | MEDIO |
| 22 | Guardar y Aplicar | `settings_window.py:295-308,435-503` + hot-reload `main.py:103-115` ✅. **Confirma éxito aunque la key siga siendo el placeholder** | ⚠️ PARCIAL | MEDIO |
| 23 | HUD **translúcida** | **NO existe** `attributes("-alpha", ...)` en ningún archivo (verificado por grep). HUD opaco `#18181b` (`hud.py:87`) | ❌ NO CUMPLE | BAJO |
| 24 | Instalación en 3 pasos | Ver #18/#19 | ⚠️ PARCIAL | MEDIO |
| 25 | 26 tests / `pytest -v` | **26 recolectados / 26 pasan** (verificado) ✅. Pero `pytest` falta en `requirements.txt` (solo en `-dev`) y `run.bat:51` solo instala `requirements.txt` → el comando documentado **falla** para el usuario de `run.bat`. ~8/26 tests sin aserciones reales | ⚠️ PARCIAL | MEDIO |
| 26 | Zero PyTorch | **Verificado:** no existe `torch`/`pytorch` en `.venv` ni en `requirements.txt` | ✅ CUMPLE | BAJO |
| 27 | < 450 MB | **Medido: `.venv` = 387.8 MB** ✅. Excluye pesas de faster-whisper (~75 MB en caché HF al primer uso local → ~463 MB). Columna "Huella en Disco (RAM)" mezcla disco y RAM | ⚠️ PARCIAL | BAJO |
| 28 | Windows 10/11 x64 | `verify_install.py:24`, uso intensivo de Win32 ✅ (no probado en Win10) | ✅ CUMPLE | BAJO |
| 29 | **Python 3.10+** | `contracts.py:6` `from enum import StrEnum` → **exige 3.11+**. `verify_install.py:33` exige 3.11+. `pyproject` dice `>=3.10`. Badge dice "3.10 \| 3.11" | ❌ NO CUMPLE | **ALTO** |
| 30 | Licencia MIT | `LICENSE` presente, MIT, titular Ricardo García | ✅ CUMPLE | BAJO |
| 31 | VAD Silero ONNX | `vad.py:111` `is_speech_chunk` **NUNCA se invoca** (verificado por grep en todo `app/`). `silence_threshold_seconds` nunca se lee. El modo VAD solo se pinta en la bandeja (`tray.py:104-107`) | ❌ NO CUMPLE | MEDIO |
| 32 | Mutex instancia única | `main.py:117-128`, `MUTEX_NAME` ✅. No maneja `CreateMutexW` → NULL; usa `windll...GetLastError()` en vez de `ctypes.get_last_error()` | ✅ CUMPLE | BAJO |
| 33 | Estructura del proyecto | Correcta en lo listado; omite `docs/`, `verify_install.py`, `pyproject.toml`, `config.example.json`, `requirements-dev.txt` | ⚠️ PARCIAL | BAJO |
| 34 | Rebranding MorocoVoice v1.0.0 | **~20 archivos** aún con marca antigua: `hud.py:109` (texto visible `"VoiceFlow"`), `prompt_templates.py:32,39` (prompts al LLM), `vad.py:89` (User-Agent `VoiceFlow-Win-Bootstrap/3.4.1`), `verify_install.py:205` (banner `VOICEFLOW-WIN v3.4.1`), `logging_setup.py:99`, `VoiceFlowException`, alias `VoiceFlowApplication` | ❌ NO CUMPLE | MEDIO |
| 35 | `custom_vocabulary.json` personalizable | Existe (30 términos). **Pero ya está en el tope de 30** → el primer término que añada el usuario se descarta. Contiene jerga privada del autor. **Sin UI** | ⚠️ PARCIAL | **ALTO** |
| 36 | El vocabulario se aplica | `engine_manager.py:69,100,112` → `stt_cloud.py:93-94` (`prompt=`) y `stt_local.py:138` (`initial_prompt=`) ✅ mecanismo real. Sin post-proceso correctivo | ✅ CUMPLE | MEDIO |

**Resumen:** 15 ✅ CUMPLE · 11 ⚠️ PARCIAL · 10 ❌ NO CUMPLE

---

## Bug de logging (verificado empíricamente — causa raíz de varios hallazgos)

`logging_setup.py:50` configura el logger **`"morocovoice"`** con `RotatingFileHandler`.
`logging_setup.py:90` devuelve `logging.getLogger(f"voiceflow.{name}")` — **otro namespace**.
Los registros de todos los módulos se propagan al logger **root**, que no tiene handlers.

Prueba ejecutada (`setup_logging()` + `get_logger("probe")` emitiendo 3 canarios):

```
Contenido real de morocovoice.log:
  2026-09-14 17:08:57 [INFO] [MainThread] morocovoice: MorocoVoice logging subsystem initialized...
  (fin — los canarios INFO/WARNING/ERROR NO aparecieron en el archivo)
stderr:  WARN-PROBE-CANARY / ERROR-PROBE-CANARY   <- logging.lastResort
```

**Impacto en cadena:**
- `morocovoice.log` contiene **1 línea**. El menú "Abrir Logs" de la bandeja abre un archivo vacío → **troubleshooting imposible**.
- Lanzado con `pythonw.exe` (`run.bat:78`) **no hay stderr** → la aplicación no registra **nada, en ningún sitio**.
- El filtro `PIISafeFilter` está en un camino muerto → la salvaguarda de privacidad **no está activa**.
- La truncación del vocabulario (`engine_manager.py:49-53` emite `logger.info`) **nunca llega a ningún log** → la truncación es **literalmente silenciosa**, como reportó el autor. La causa raíz es este bug, no una decisión de diseño.

---

## PASO 4 — EXPERIENCIA DE USUARIO NO TÉCNICO

| # | Escenario | Fricción encontrada | Impacto |
|---|---|---|---|
| 1 | Llega al repo en GitHub | El README vende bien qué es ("dictado por voz + reescritura, $0, Windows"). En 10 s se entiende. **Pero** el paso 1 de "Comenzar en 3 Pasos" es `git clone` en terminal | CONFUNDE |
| 2 | Sigue el README paso a paso | **No tiene Git** → no puede ni empezar. No hay enlace a "Download ZIP" ni a GitHub Desktop | **BLOQUEA** |
| 3 | `run.bat` sin Python instalado | `run.bat:31-37` da un mensaje correcto con enlace y `pause` ✅. **Pero** `python` en Windows 10/11 es frecuentemente el **stub de Microsoft Store**, que abre la Store en vez de fallar limpio → el `pause` puede no verse | **BLOQUEA** |
| 4 | `run.bat` con Python 3.10 | `StrEnum` no existe → `ImportError`. Se lanza con **`pythonw.exe` (sin consola)** → **doble clic y no pasa absolutamente nada**, sin mensaje, sin ventana | **BLOQUEA** |
| 5 | Antivirus / SmartScreen | Se crea un `.venv` con binarios no firmados (`ctranslate2`, `onnxruntime`, `pywin32`) que instalan hooks de teclado globales y ejecutan `SendInput`. Corporativos (Defender ASR / EDR) suelen bloquear hooks de teclado → dictado silenciosamente muerto. No se documenta | **BLOQUEA** |
| 6 | Configura la API key | `run.bat:58-63` copia `.env.example` → `.env` con `GROQ_API_KEY=gsk_tu_clave_de_groq_aqui`. `config.py:76-78` lo trata como **credencial válida** → motor CLOUD, `is_llm_available()`=True. Cada dictado: 401 en STT + 401 en LLM → **fallback a Whisper local, que descarga ~75 MB sin avisar**. El botón 1-clic ✅ es claro, pero **nada valida la clave** | **BLOQUEA** (silencioso) |
| 7 | Pulsa "Guardar y Aplicar" sin cambiar la clave | `settings_window.py:494-498` muestra: *"Groq API Key: Almacenada y enmascarada de forma **segura**"* — **siendo todavía el placeholder**. Confirmación engañosa | **BLOQUEA** (mentira activa) |
| 8 | Primer `Win + Space` | Windows interpreta `Win+Space` como **cambio de idioma/IME**. El usuario con teclado ES+EN ve cambiar su distribución en cada dictado. `release_modifiers()` (`injector.py:179`) suelta la tecla Win durante la inyección. Sin supresión del evento (pynput no suprime) | **BLOQUEA** |
| 9 | La ventana de Configuración | `main.py:359` la abre en **cada arranque** (el README dice "por primera vez"), con `-topmost` y `focus_force()`, robando el foco a lo que el usuario estaba haciendo. Los `help_text` (`settings_window.py:148,154,216,222,235,241`) **se pasan pero nunca se renderizan** → **cero ayuda contextual** pese a estar escrita | MOLESTA / CONFUNDE |
| 10 | Botón "📄 Editar config.json" | Abre **Notepad con JSON crudo** en la ventana de configuración de producto. Un no-técnico que lo pulse verá `{"hotkey_dictation": "win+space", ...}` sin explicación | CONFUNDE |
| 11 | Quiere logs de depuración | Bandeja → "Abrir Logs" → **archivo con 1 línea** | CONFUNDE |
| 12 | `git pull` tras usar la app | `config.json` **está versionado** y la app lo **reescribe** en `_on_save` → conflicto de merge en cada actualización | CONFUNDE |
| 13 | Quiere añadir vocabulario | Único camino: abrir `custom_vocabulary.json` en un editor y escribir JSON. **Ya tiene 30 términos** → lo que añada se descarta sin aviso. **No hay UI** | **BLOQUEA** |
| 14 | Feedback visual del dictado | HUD con punto rojo + `"Escuchando..."` ✅ claro. **Pero** watchdog de 12 s en PROCESSING (`hud.py:221-222`) oculta el HUD antes de que termine el trabajo → el texto aparece "de la nada" | MOLESTA |

---

## PASO 4B — EVALUACIÓN DE LA BRECHA CONFIRMADA POR EL AUTOR

**Veredicto: sí, es un bloqueo real para usuarios no técnicos.** Y es peor de lo reportado.

### Causa raíz ampliada

`engine_manager.py:46` → `valid_terms[:MAX_VOCABULARY_TERMS]` con `MAX_VOCABULARY_TERMS = 30`.

Tres agravantes que la descripción del autor no recoge:

1. **El archivo por defecto ya está en el tope exacto de 30.** Un usuario que siga el único camino documentado (editar el JSON) y añada **su primer** término, lo pierde. El fallo no aparece "al llegar a 30": aparece **inmediatamente en la primera edición**. Eso convierte un caso borde en el caso normal.
2. **La truncación es aún más silenciosa de lo que el autor cree.** El `logger.info` de `engine_manager.py:49-53` **nunca llega a ningún log** por el bug de namespace. Está diseñado para avisar y no avisa a nadie.
3. **El vocabulario por defecto es jerga privada del autor**: "El Panóptico", "Smart Time Blocks", "Telat Group", "rgarcia", "Antigravity". Un usuario nuevo hereda 30 posiciones ocupadas por nombres internos de otra empresa. Esto **sesga activamente sus transcripciones** hacia términos que no le sirven, y le deja 0 posiciones libres.

### Respuestas a las preguntas de diseño

**¿Debería haber una sección "Vocabulario" dentro de la ventana de Configuración?**
Sí, sin duda. Es la opción correcta y de menor coste: la ventana ya existe, ya tiene estilo, ya sabe escribir en disco y ya tiene hot-reload. Añadir una 4ª sección no requiere arquitectura nueva. La alternativa (un `.exe`/`.bat` que abra el JSON) perpetúa el problema: el usuario sigue viendo JSON.

**¿Un campo de texto simple (una línea por término) basta?**
Sí para la v1.1, con matices. Recomiendo `tk.Text` multilínea (una línea por término), que es lo más simple y autoexplicativo, **más** estos cuatro elementos obligatorios:

- **Contador en vivo**: `Términos: 27 / 30` con color (verde → ámbar → rojo). Sin esto se repite el bug.
- **Bloqueo preventivo al guardar**: si hay >30, **avisar y no guardar** (o guardar solo 30 **diciéndolo**). Nunca truncar en silencio. Diálogo: *"Tienes 34 términos y el máximo es 30. Se guardarán los 30 primeros y se ignorarán: X, Y, Z, W. ¿Continuar?"*
- **Botón "Restaurar vocabulario recomendado"** para volver al set por defecto.
- **No hace falta** nada más sofisticado (tablas, ordenar, pesos, categorías) en la v1.1. Esa sofisticación es deuda innecesaria para una v1.

Nota técnica: `tk.Text` no es un `tk.Variable`, así que `_create_entry_row` no sirve; hay que añadir un widget nuevo. Y el usuario necesita **feedback de que el cambio se aplicó**: como `EngineManager` se reconstruye en `reload_config` (`main.py:112`), basta con guardar y aplicar, pero el README debe decir que aplica en caliente.

**¿Cómo explicárselo a un usuario no técnico?**

> **Vocabulario personalizado**
> Aquí puedes enseñarle a MorocoVoice **tus palabras**.
> Cuando hablas, el sistema intenta adivinar qué dijiste. Si dices un nombre propio, una sigla o un término técnico que no conoce, puede escribir otra cosa parecida (por ejemplo, oír "GitHub" y escribir "GITCOP").
> Escribe aquí esas palabras, **una por línea**. La próxima vez que las digas, es mucho más probable que las escriba bien.
> *Ejemplos: GitHub, WFM, Verint, IEX, el nombre de tu empresa, el de tus compañeros, tus productos.*
> Máximo **30**. Si tienes más, prioriza las que más te fallan.

**¿Documentar el límite de 30 en el README o en la UI?**
**En los dos, y la UI es la que importa.** En la UI el contador `n/30` es permanente y visible, no un texto de ayuda. En el README, una línea, con la razón (proteger la precisión de Whisper: un prompt demasiado largo **empeora** el reconocimiento, no lo mejora). Y **documentar también cómo se usa hoy** (editar `custom_vocabulary.json`), que actualmente no se explica en ningún sitio del README: se lista el archivo en la estructura del proyecto y nunca se dice que se pueda tocar.

**¿Qué pasa si el usuario excede los 30?**
Hoy: se descarta el exceso en silencio. Debería ser: **la UI advierte antes de guardar**, nombra los términos que se van a ignorar, y exige confirmación explícita. El principio es simple: **el usuario nunca debe perder datos sin saberlo.** Y si se decide truncar, que quede en `morocovoice.log` (una vez arreglado el logging) y en la UI.

### Diseño recomendado (mínimo viable, sin implementar)

```
┌─ ⚙️ Configuración de MorocoVoice ─────────── v1.0.0 ─┐
│ ATAJOS DE TECLADO (CORE SHORTCUTS)                   │
│   ...                                                │
│ MOTOR Y MODELOS DE INFERENCIA                        │
│   ...                                                │
│ COMPORTAMIENTO Y PARÁMETROS                          │
│   ...                                                │
│ ── VOCABULARIO PERSONALIZADO ──────── Términos: 27/30│   <- contador en vivo
│   Palabras que MorocoVoice debe reconocer siempre.   │
│   Una por línea. Máx. 30.                            │   <- explicación no técnica
│   ┌────────────────────────────────────────────────┐ │
│   │ GitHub                                         │ │
│   │ WFM                                            │ │
│   │ Verint                                         │ │
│   │ ...                                            │ │   <- tk.Text multilínea
│   └────────────────────────────────────────────────┘ │
│   [↩ Restaurar recomendado]  [📂 Abrir JSON avanzado]│
│ ──────────────────────────────────────────────────── │
│ 🟢 Activo en segundo plano. Dictado: win+space       │
│ [📄 Editar config.json]      [Minimizar] [💾 Guardar]│
└──────────────────────────────────────────────────────┘
```

Contrato de comportamiento: al pulsar Guardar, si `n > 30` → `messagebox.askyesno` listando los ignorados; si `n <= 30` → escribir `custom_vocabulary.json` normalizando (trim, sin vacíos, sin duplicados) y reconstruir `EngineManager` (ya ocurre en `main.py:112`). Y **añadir un 4º paso al README**: "Opcional — enséñale tus palabras".

---

## PASO 5 — ANÁLISIS DEL VOCABULARIO PERSONALIZADO

**1. ¿El `initial_prompt` de Whisper funciona realmente?**
**Sí, el mecanismo es real y está bien implementado.** `engine_manager.py:55` construye `", ".join(términos)` y se pasa a `prompt=` en Groq (`stt_cloud.py:93-94`) y a `initial_prompt=` en local (`stt_local.py:138`). Es la técnica estándar de *prompt biasing* de Whisper y sesga el decodificador hacia ese vocabulario. Es una implementación correcta, no decorativa.
**Limitaciones reales que nadie documenta:** (a) es un **sesgo, no un diccionario** — no garantiza la corrección; (b) Whisper trunca el prompt a **224 tokens**; 30 términos cortos caben, pero 30 frases largas pueden excederlo y provocar error o recorte; (c) el efecto decae con el **orden** (los primeros términos pesan más) — de ahí que poner `"GitHub"` primero en `main` sea exactamente la decisión correcta.

**2. ¿30 términos bastan para WFM / call center empresarial?**
**No.** Un caso real de WFM/call center necesita fácilmente 80–150: nombres de herramientas (Verint, NICE, IEX, Genesys, Calabrio), siglas de métricas (AHT, FCR, CSAT, SLA, Shrinkage, Adherence, Occupancy), nombres de clientes/campañas, apellidos de coordinadores y nombres de sedes. **30 es un techo de producto, no un techo técnico.** El límite correcto es el presupuesto de tokens (224), no un número redondo: la UI debería contar **caracteres/tokens** y avisar cerca del límite real, o implementar un "presupuesto" donde los términos más relevantes se prioricen.

**3. ¿Hay forma de añadir términos SIN editar JSON?**
**No. Ninguna.** Verificado: `settings_window.py` construye exactamente 3 secciones (Atajos / Motor y Modelos / Comportamiento) y ninguna toca `custom_vocabulary.json`. La única referencia al vocabulario en toda la UI es inexistente. El menú de la bandeja (`tray.py:66-74`) tiene Configuración, Abrir Logs y Salir. **La única vía es abrir el JSON en un editor.** El README no lo explica.

**4. Si Whisper transcribe mal un término que SÍ está en el vocabulario, ¿hay corrección post-proceso?**
**No existe ninguna.** `engine_manager.py` devuelve `result.text` sin tocar. No hay búsqueda difusa, ni diccionario de reemplazo, ni verificación posterior. Es la **carencia funcional más importante** de la feature: el `initial_prompt` solo reduce la probabilidad del error, no lo elimina. Un `GITCOP → GitHub` no se corrige nunca.
**Recomendación:** un post-proceso determinista barato y de alto valor — para cada término del vocabulario, comparar contra las palabras del texto con `difflib.SequenceMatcher` (la dependencia ya se usa en `stt_local.py:9`) o distancia de Levenshtein sobre tokens de longitud similar, y sustituir si la similitud > ~0.85 y la palabra no es una palabra común del español. Es ~30 líneas, elimina la clase entera de fallos reportada por el autor y convierte la feature en una **garantía** en vez de una **probabilidad**. Riesgo a controlar: falsos positivos (que "gitan" se vuelva "GitHub"), así que conviene un umbral conservador y no tocar palabras del diccionario común.

**5. ¿Se documenta en algún lugar cómo agregar términos nuevos?**
**No.** El README lista `custom_vocabulary.json # Vocabulario especializado (jerga técnica, nombres)` en el árbol de estructura (`README.md:115`) y **nunca** explica que se pueda editar, ni cómo, ni el límite de 30, ni el formato JSON. `docs/PENDIENTES.md` tampoco lo menciona. Un usuario puede pasar meses sin saber que la feature existe.

---

## PASO 6 — ÁREAS DE MEJORA (Roadmap honesto, sin filtros)

### 6.1 Bugs y riesgos que afectarán al primer usuario externo

Ordenados por probabilidad × daño:

1. **`qwen/qwen3.8-27b` no existe** (`config.json:6`, `settings_window.py:222`). Es el modelo LLM por defecto. Toda llamada al LLM falla con 404. Efecto: (a) la **reescritura contextual (`Ctrl+Shift+Space`) no funciona en absoluto** — el usuario recibe "Error al Reescribir"; (b) cada dictado hace una llamada de red **fallida** extra que se suma a la latencia. **Este es el bug #1**: rompe la funcionalidad estrella y el titular de latencia, y es una línea.
2. **El tag `v1.0.0` no tiene el fix de "GitHub"** y sesga a Whisper hacia "VoiceFlow". El artefacto publicado reproduce el bug que el autor cree haber corregido.
3. **Pérdida de datos del portapapeles.** `injector.get_clipboard_text()` solo lee `CF_UNICODETEXT`. Si el usuario tenía **una imagen o archivos** copiados, devuelve `""` y la restauración (`injector.py:317-318`) escribe `""` → **contenido irrecuperable**. `context.py:103-116` repite el patrón y además **vacía** el portapapeles (`:106`) sin restaurarlo cuando no había texto (`:115`). Copiar un archivo y dictar = archivo perdido. El README lo promete explícitamente como "no destructiva".
4. **Python 3.10 no arranca.** `StrEnum` (`contracts.py:6`) requiere 3.11+. Con `pythonw.exe` (sin consola) el fallo es **totalmente invisible**: doble clic → nada. El README, el badge y `pyproject.toml` dicen 3.10+; `verify_install.py:33` dice 3.11+.
5. **`.env.example` con placeholder tratado como credencial válida** (`config.py:76-78`). Primer arranque → fallos 401 → descarga silenciosa de ~75 MB de Whisper local → primera dictación lentísima sin feedback. Y "Guardar" confirma éxito diciendo que la key está "almacenada de forma segura" **siendo el placeholder**.
6. **`Win + Space` colisiona con el atajo nativo de Windows** de cambio de idioma/IME. En LATAM (ES+EN) cada dictado cambia la distribución del teclado. El README lo vende como "protección contra conflictos".
7. **Logging roto** (`logging_setup.py:50` vs `:90`): `morocovoice.log` = 1 línea (verificado). Troubleshooting imposible, telemetría de latencia inexistente, filtro PII inactivo, truncación de vocabulario invisible.
8. **`max_tokens=300` en la reescritura** (`rewriter.py:156`) + inyección que **reemplaza la selección**: seleccionar un párrafo largo y pulsar `Ctrl+Shift+Space` puede sustituirlo por una versión truncada a mitad de frase → **el original se pierde** (no hay undo). Riesgo de pérdida de datos del usuario.
9. **`language="es"` hardcodeado** (`stt_cloud.py:90`, `stt_local.py:137`) pese a venderse como "teclados internacionales". Dictar en inglés fuerza decodificación en español. No se documenta que sea solo español.
10. **VAD es decorativo.** `is_speech_chunk` nunca se llama; `silence_threshold_seconds` nunca se lee; el modelo ONNX se descarga (1.8 MB) y `onnxruntime` ocupa 45.6 MB del `.venv` **para nada**. La bandeja informa "VAD: Silero (ONNX)" — información falsa.
11. **Config.json versionado y reescrito por la app** → conflictos de `git pull` para todo usuario que guarde ajustes.
12. **`pytest` no está en `requirements.txt`** pero el README manda ejecutarlo → falla para quien usó `run.bat`.
13. **`get_selected_text()` con `time.sleep(0.12)` fijo** (`context.py:111`): en Outlook/Teams lentos el portapapeles aún está vacío → falso "Selecciona texto primero".
14. **`numpy_to_wav_bytes(sample_rate=16000)` hardcodeado** (`stt_cloud.py:84`) ignorando `config.sample_rate` → si se cambia la tasa, el WAV queda mal etiquetado (audio acelerado/agudo).
15. **Sin timeout explícito en las llamadas a Groq** (`stt_cloud.py:96`, `rewriter.py:149`): un cuelgue de red deja el HUD en "Procesando..." y la app aparentemente congelada.
16. **`_on_save` no valida el formato del atajo** (`settings_window.py:446-448` solo comprueba no-vacío): un atajo mal escrito se guarda y el hotkey deja de funcionar **sin ningún aviso**.
17. **`config.json` diverge de `config.example.json` y de `contracts.py`** (modelos STT/LLM y `clipboard_restore_delay_ms` 120 vs 80; `contracts.py:81` `hotkey_dictation` por defecto `"alt+space"` vs `config.json` `"win+space"`). Borrar `config.json` cambia silenciosamente el comportamiento.
18. **Race del portapapeles**: dos inyecciones seguidas sobrescriben `_active_backup_text` mientras el primer hilo de restauración está pendiente.
19. **`trigger_diagnostics` y `hotkey_shutdown`/`hotkey_diagnostics`** existen en código pero se eliminan del `config.json` al guardar (`settings_window.py:471-472`) — código medio muerto.
20. **`requests>=2.31.0`** declarado en `requirements.txt` y **nunca importado** (verificado).

### 6.2 Funcionalidades prometidas incompletas o dependientes de condiciones no documentadas

| Prometida | Realidad |
|---|---|
| HUD **translúcida** | No hay `-alpha` en ningún sitio (verificado). HUD opaco |
| "Zero-Touch" | Requiere Git + Python 3.11+ + PATH preexistentes. `PENDIENTES.md:19` admite que el `.exe` standalone está **pendiente** |
| "Reescritura contextual" | Rota por defecto (modelo inexistente) |
| "~400 ms" | La medición del propio autor es **~1.2 s** (`PENDIENTES.md:9`) |
| "VAD Silero ONNX" | Código muerto |
| "Zero PyTorch" | ✅ **Cierto y verificado** |
| "< 450 MB" | ✅ Aproximadamente cierto en disco (387.8 MB medidos), sin contar pesas de Whisper |
| "Reescritura con `llama-3.3-70b-versatile`" | Ese modelo es **Enterprise-only** en Groq hoy; un usuario gratuito obtendrá error |
| GPU / CUDA | `verify_install.py:85-121` recomienda tiers por VRAM (hasta `large-v3`, `float16`), pero `engine_manager.py:80` fija **`device="cpu"`** siempre. Las recomendaciones son inaplicables |
| `verify_install.py` | **Huérfano**: no lo invoca `run.bat`, no lo menciona el README, banner `VOICEFLOW-WIN v3.4.1`, y valida el VAD muerto |

### 6.3 Deuda técnica que heredaría el siguiente contribuidor

- **Dos marcas conviviendo.** `VoiceFlow`/`VoiceFlow-Win` en ~20 archivos, incluidos **textos visibles al usuario** (`hud.py:109`) y **prompts enviados al LLM** (`prompt_templates.py:32,39`). Clases `VoiceFlowException`, alias `VoiceFlowApplication`, User-Agent `VoiceFlow-Win-Bootstrap/3.4.1`, banner v3.4.1. El "rebranding canónico" que anuncia `PENDIENTES.md:27` está a medias.
- **Logging roto por namespace** — un contribuidor que añada `logger.info` asumirá que se registra, y no.
- **`docs/` apunta a una versión que ya no existe** (v3.4.1, v3.5.0, v3.5.1 en `PENDIENTES.md`) mientras el producto es v1.0.0. El historial es incoherente (commits `v3.5.0` → `v1.0.0`).
- **`config.json` versionado** con estado de usuario.
- **Sin CI.** No hay GitHub Actions; `ruff` está configurado en `pyproject.toml` pero no se ejecuta en ningún sitio.
- **Sin versiones fijadas** en `requirements.txt` (solo rangos laxos) → alta variabilidad entre instalaciones.
- **`help_text` muerto** en `settings_window.py` (parámetro aceptado y nunca renderizado en 6 sitios) — un contribuidor escribirá ayuda que nunca se ve.
- **Suite orientada a lo trivial:** ~8 de 26 tests no tienen aserción real o prueban código muerto:
  - `test_injector.py:33-63` → `assert True` ×4 (`test_emergency_restore_safeguard`, `test_clipboard_lock_reentrancy`, `test_release_modifiers_executes_safely`, `test_send_ctrl_c_executes_safely`).
  - `test_audio.py` (4 tests) prueba `is_speech_chunk`, que **nunca se usa en producción**.
  - `test_context.py` → 3 tests de `isinstance(x, bool)`, pasan siempre.
  - **Además, `test_send_ctrl_c_executes_safely` inyecta Ctrl+C sintético al sistema durante los tests** — puede interrumpir o copiar en la aplicación realmente enfocada del desarrollador.
  - **Cero cobertura** de: `inject_text()` completo, la restauración asíncrona del portapapeles, `get_selected_text()`, `numpy_to_wav_bytes()`, `load_config()`/`.env`, `recorder.py`, `_on_save()`, HUD y bandeja. Es decir, **están sin probar exactamente las rutas donde he encontrado los bugs**.

### 6.4 Qué haría yo si fuera a usar esto en producción mañana

1. **No lo desplegaría como está.** Con el modelo LLM inexistente y la pérdida de portapapeles, falla en las dos cosas que más importan (la función estrella y la confianza del usuario).
2. Como parche mínimo antes de tocar nada: cambiar `config.json:6` por `llama-3.1-8b-instant` (que sí existe y es el default de `contracts.py:88`), hacer `git clone` desde `main` en vez del tag, y **desactivar el vocabulario** (dejarlo en `[]`) para que no sesgue con jerga ajena.
3. Poner un `requirements.txt` con versiones fijas y `pip install -r requirements-dev.txt`.
4. Avisar a todo el equipo: **copiar algo que no sea texto antes de dictar lo pierde**. Es el riesgo más peligroso porque es silencioso e irreversible.
5. Antes de comprar/estandarizar: reasignar el atajo a `ctrl+alt+space` (evita el conflicto de IME) y decidir el idioma explícitamente.
6. Medir latencia real extremo a extremo — el autor ya midió 1.2 s, no 400 ms.

---

## CALIFICACIÓN GLOBAL DE LANZAMIENTO: **4.5 / 10**

Se sostiene sobre una base de ingeniería Win32 genuinamente buena — mutex, UIPI, `SendInput` en 3 fases, `RLock` reentrante, fallback cloud→local, hot-reload, HUD no intrusiva, filtro anti-alucinaciones y 26 tests que pasan — pero **está publicado en un estado en el que la funcionalidad estrella no funciona por defecto** (modelo LLM inexistente), **puede destruir datos del usuario** (portapapeles con imágenes/archivos, reescritura truncada sobre la selección) y **no arranca en la versión de Python que promete**. El tag `v1.0.0` ni siquiera contiene el fix del bug que motivó esta auditoría. El README describe un producto mejor que el que el repo entrega: la brecha no está en la ambición sino en la verificación. Con tres correcciones concretas (abajo) sube a ~8; llegar a 10 exige cerrar además la brecha de vocabulario, la de idioma y la de logging.

---

## 3 RECOMENDACIONES PRIORITARIAS PARA LLEGAR A 10/10

### 1. Arreglar lo que rompe el primer contacto (bloqueante, ~1 día)
Un solo commit que elimine la mayor parte del riesgo percibido:
- `config.json:6` → un modelo **real** (`llama-3.1-8b-instant`), y **validar la clave** con una llamada de prueba en "Guardar y Aplicar" que muestre un error claro en vez de un éxito falso. Nunca confirmar "almacenada de forma segura" sin haber probado la credencial.
- **Re-tag `v1.0.0` (o publicar `v1.0.1`) desde `main`** para que el artefacto descargable incluya `"GitHub"` en el vocabulario.
- Detectar el placeholder `gsk_tu_clave_de_groq_aqui` y el caso "sin clave" explícitamente, con un mensaje en la UI.
- `verify_install.py` al arranque (o eliminarlo) y **unificar la versión de Python**: o `requires-python = ">=3.11"` + badge + README + `run.bat` con comprobación de versión, o sustituir `StrEnum` por `class X(str, Enum)`. Recomiendo lo primero. Y **nunca** lanzar con `pythonw.exe` sin capturar la excepción de arranque: si falla el import, hay que mostrar un diálogo.
- Corregir el namespace del logger (`logging_setup.py:90` → `"morocovoice." + name`) y verificar que `morocovoice.log` recibe registros reales.

### 2. Hacer la feature de vocabulario real y segura (el mayor salto de calidad percibida, ~2-3 días)
- **Sección "Vocabulario personalizado" en la ventana de Configuración** con `tk.Text` (una línea por término), **contador `n/30` en vivo**, aviso **bloqueante** antes de truncar (nombrando los términos ignorados) y botón "Restaurar recomendado".
- **Sustituir el vocabulario por defecto** por uno genérico de WFM/negocio: la jerga privada del autor (`El Panóptico`, `Smart Time Blocks`, `Telat Group`, `rgarcia`) no debe venir activada por defecto ni ocupar el tope de 30.
- **Post-proceso correctivo determinista** sobre la salida de Whisper con `difflib` (umbral ~0.85, excluyendo palabras comunes) → convierte `GITCOP → GitHub` de "ojalá" en "seguro". Esto es lo que convierte la feature en vendible.
- Documentar el límite (y **su motivo**: 224 tokens de Whisper) en la UI y en el README, con un 4º paso: "Opcional — enséñale tus palabras".

### 3. Blindar los datos del usuario y decir la verdad en el README (confianza, ~1-2 días)
- **Portapapeles no destructivo de verdad:** respaldar y restaurar **todos** los formatos presentes (`CF_UNICODETEXT`, `CF_DIB`/`CF_BITMAP`, `CF_HDROP`), o **abortar el respaldo y avisar** cuando el portapapeles contenga formatos no soportados. Nunca escribir `""`. Corregir también `context.py:103-116`.
- **Quitar el techo de 300 tokens de la reescritura** (o dimensionarlo al texto de entrada) y **no reemplazar la selección sin confirmación/undo** cuando la salida parezca truncada. Guardar el original accesible.
- **Reasignar el atajo por defecto** a `ctrl+alt+space` (o documentar y advertir del conflicto de IME con `Win+Space`).
- **Corregir el README**: latencia real ~1.2 s (medida por el propio autor) o explicar que 400 ms es solo el tramo STT sin LLM; declarar que el dictado es **solo en español**; eliminar "translúcida"; documentar el límite de 30 y cómo editar el vocabulario; declarar Python 3.11+; y **terminar el rebranding** (eliminar los `VoiceFlow` visibles y de los prompts).
- **Activar o eliminar el VAD.** Hoy cuesta 45.6 MB de `onnxruntime` + 1.8 MB de modelo + descarga en el primer arranque, y la bandeja informa de un modo que no se usa. O se integra `is_speech_chunk` en `recorder.py` para auto-cortar por silencio (usando el ya existente `silence_threshold_seconds`), o se elimina — pero no puede quedarse mintiendo en la bandeja.
