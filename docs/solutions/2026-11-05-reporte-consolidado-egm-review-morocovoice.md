# Reporte Consolidado EGM Review: Auditoría Integral MorocoVoice v1.0.5

**Fecha:** 2026-11-05  
**Documento Auditado:** `MorocoVoice/README.md` & Código Fuente (`app/`, `run.bat`, `tests/`)  
**Marco de Auditoría:** Elephant-Goldfish Model (EGM) Multi-Persona Review  
**Subagentes Participantes:**
- `egm-zoom-out` (Skeptical Architect)
- `egm-comprehension` (Naive Reader Auditor)
- `egm-design` (Hostile Design Critic)
- `egm-implementation-readiness` (Pragmatic Tech Lead)
- `egm-codebase-details` (Pedantic Code Auditor)

---

## 1. Resumen Ejecutivo de la Auditoría

El enjambre de subagentes Goldfish evaluó MorocoVoice desde cinco ángulos independientes con contexto limpio. El consenso general es que el proyecto posee un núcleo técnico sólido (latencia reducida, UI oscura moderna, bindings Win32 optimizados), pero **adolece de discrepancias críticas entre la documentación y el código real**, así como de tres fallas de diseño estructural en el manejo del portapapeles, la detección de elevación UIPI y la inicialización de motores offline.

---

## 2. Matriz de Hallazgos por Severidad

### 🔴 Hallazgos Críticos (Blockers)

| ID | Área Afectada | Hallazgo | Subagentes |
| :--- | :--- | :--- | :--- |
| **BLK-01** | `injector.py` / `README.md:104` | **Destrucción permanente del portapapeles:** El README promete restaurar el contenido a los 120 ms con RLock. En el código real, `inject_text` tiene `restore_clipboard = False` por omisión y nunca se activa en `main.py`. Además, `EmptyClipboard()` destruye bitmaps, fórmulas de Excel y formatos ricos. | `egm-design`, `egm-codebase-details` |
| **BLK-02** | `context.py:37-64` | **Inversión del chequeo de elevación UIPI:** Cuando `OpenProcessToken` falla con `ERROR_ACCESS_DENIED` (comportamiento estándar de Windows frente a procesos Administrador), la función retorna `False` en vez de `True`. La protección UIPI falla abierta. | `egm-design` |
| **BLK-03** | `README.md:181` / `contracts.py:86` | **Atajo `Ctrl + Alt + S` inexistente en runtime:** El README y `TROUBLESHOOTING.md` prometen `Ctrl + Alt + S` como red de seguridad obligatoria si falla la bandeja, pero en el código está desactivado (`""`) tras la directiva de no usar atajos extra. | `egm-zoom-out`, `egm-implementation-readiness`, `egm-codebase-details` |
| **BLK-04** | `engine_manager.py` / `stt_local.py` | **Congelamiento síncrono en fallback offline:** Si la API de Groq falla o no hay internet, la carga de `faster-whisper` en CPU ocurre de forma síncrona en el worker, provocando congelamientos o timeouts en el HUD. | `egm-design` |
| **BLK-05** | `README.md:77-85` | **Atajo por defecto en conflicto con el sistema operativo:** `Win + Space` está reservado por Windows para alternar la distribución de teclado/IME. Al no suprimirse el evento (`suppress=False`), el atajo cambia el idioma del usuario mientras dicta. | `egm-zoom-out`, `egm-design` |

---

### 🟡 Hallazgos Mayores (Major)

| ID | Área Afectada | Hallazgo | Subagentes |
| :--- | :--- | :--- | :--- |
| **MAJ-01** | `settings_window.py` / `config.py` | **Trampa de primer inicio:** Al arrancar por primera vez sin clave de Groq, la app se inicializa en `LOCAL`. Si el usuario pega la clave en Configuración y guarda, la app no conmuta automáticamente a `CLOUD`, dejándolo atrapado en modo local de baja velocidad. | `egm-implementation-readiness` |
| **MAJ-02** | `run.bat:14-16` | **Fallo silencioso ante instalaciones interrumpidas:** `run.bat` solo valida si existe `.venv\Scripts\python.exe`. Si un `pip install` previo fue cancelado a la mitad, salta a ejecutar con `pythonw.exe` y muere sin emitir error. | `egm-implementation-readiness` |
| **MAJ-03** | `hotkey.py:90-110` | **Modificadores pegajosos (*sticky keys*):** Si se activa un diálogo de UAC o bloqueo de pantalla, el hook pierde los eventos `WM_KEYUP`, dejando las teclas Ctrl/Alt/Win registradas permanentemente como presionadas. Se recomienda consultar `GetAsyncKeyState`. | `egm-design` |
| **MAJ-04** | `recorder.py:73-87` | **Rigidez de frecuencia de muestreo WASAPI:** Hardcodear 16,000 Hz mono hace que ciertos auriculares Bluetooth o interfaces de audio USB rechacen el stream (`PortAudioError: Invalid sample rate`). Requiere fallback con re-muestreo a 48 kHz. | `egm-design` |
| **MAJ-05** | `README.md:82` / `tray.py` | **Icono de bandeja erróneo en documentación:** El README dice "icono de la pluma", mientras que `tray.py` dibuja procedimentalmente un **micrófono azul con base dorada**. | `egm-codebase-details` |
| **MAJ-06** | `README.md:92` / `contracts.py:89` | **Desfase en modelo STT:** README publicita `whisper-large-v3-turbo`, mientras que el código por omisión declara `whisper-large-v3`. | `egm-codebase-details` |
| **MAJ-07** | `README.md:124` | **Conteo de pruebas unitarias desactualizado:** El README indica 43 tests; la suite real cuenta con 57 pruebas unitarias. | `egm-implementation-readiness`, `egm-codebase-details` |
| **MAJ-08** | `run.bat:130-132` | **Filtro de limpieza de procesos indiscriminado:** `Get-CimInstance ... *app.main*` mata cualquier script de Python del sistema que coincida con `app.main`, sin verificar la ruta del repositorio. | `egm-implementation-readiness` |

---

### 🟢 Hallazgos Menores & Estilo (Nits)

| ID | Área Afectada | Hallazgo | Subagentes |
| :--- | :--- | :--- | :--- |
| **NIT-01** | `README.md:39` | Inconsistencia de conteo en título: "Comenzar en 3 Pasos" pero lista 4 pasos numerados. | `egm-comprehension` |
| **NIT-02** | `README.md:32` | Falsa equivalencia de métricas: Agrupa almacenamiento y memoria bajo "Huella en Disco (RAM): < 450 MB". | `egm-comprehension` |
| **NIT-03** | `README.md:66-70` | Caída excesiva de altitud: Expone nombres de módulos internos (`difflib`, `RLock`, `CF_UNICODETEXT`) en un README para usuarios finales. | `egm-zoom-out` |
| **NIT-04** | `logging_setup.py:26` | Filtro PII sobre-agresivo: Censura líneas de trazas completas que contengan la subcadena `"text"`. | `egm-design` |
| **NIT-05** | `app/main.py:53` | Namespace `Global\` en Mutex puede fallar en tokens restringidos sin privilegio global; se aconseja `Local\`. | `egm-implementation-readiness` |

---

## 3. Plan de Acción Priorizado para Remediación

1. **Corrección de Seguridad UIPI (`context.py`):**
   - Corregir el retorno de `is_process_elevated`: si `OpenProcessToken` retorna error `5` (`ERROR_ACCESS_DENIED`), retornar `True` (el proceso objetivo está más elevado que el proceso actual).
2. **Saneamiento Documental en `README.md` y `TROUBLESHOOTING.md`:**
   - Eliminar las referencias a `Ctrl + Alt + S` como atajo activo; clarificar que el acceso es vía icono de bandeja (micrófono azul).
   - Alinear la explicación del portapapeles: MorocoVoice mantiene el texto dictado en el portapapeles por diseño para garantizar cero pérdida de texto.
   - Corregir "icono de la pluma" por "micrófono azul".
   - Actualizar el contador de tests de 43 a 57.
3. **Optimización del Lanzador (`run.bat`):**
   - Añadir archivo centinela `.venv\.installed` para evitar falsos positivos de instalación.
   - Acotar el filtro de procesos en PowerShell a la ruta del directorio local `%~dp0`.
4. **Resiliencia de Configuración Inicial (`settings_window.py`):**
   - Conmutar automáticamente el selector de motor a `CLOUD` cuando el usuario ingresa una API Key de Groq válida desde el estado `LOCAL`.

