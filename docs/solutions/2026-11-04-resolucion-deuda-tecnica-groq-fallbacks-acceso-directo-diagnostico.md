# Ficha Técnica: Resolución de Deuda Técnica, Groq Fallbacks, Portapapeles Permanente y Atajos Canónicos

**Fecha:** 2026-11-04  
**Repositorio:** `MorocoVoice`  
**Versión:** `v1.0.5`  
**Autor:** Antigravity AI & Ricardo García  

---

## 1. Contexto y Diagnóstico

Durante el análisis del flujo de trabajo y la auditoría de experiencia de usuario (UX) se detectaron las siguientes problemáticas críticas:

1. **Contaminación de `Win + V` con bloques vacíos:** Al usar el historial de portapapeles de Windows (`Win + V`), aparecía constantemente una entrada en blanco. Esto se debía a que [`app/platform/injector.py`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/app/platform/injector.py) ejecutaba una restauración asíncrona ciega a los 80 ms; si el portapapeles previo no contenía texto o estaba vacío, llamaba a `set_clipboard_text("")`, inyectando una cadena vacía en Windows Clipboard Broker.
2. **Pérdida de dictados largos por pérdida de foco:** Si el usuario no tenía el cursor dentro de un campo de texto interactivo en el momento exacto en que finalizaba la transcripción, la combinación `Ctrl+V` no tenía efecto y, al restaurar el portapapeles original, el texto dictado se destruía de la memoria volátil, provocando frustración operativa.
3. **Atajos espurios en configuración:** Existían referencias a `hotkey_diagnostics` (`Ctrl+Shift+D`), una función obsoleta que nunca se utilizaba y que podía colisionar con atajos globales del sistema. El usuario ratificó que únicamente deben existir dos atajos activos: hablar (`Win + Space`) y corregir texto (`Ctrl + Shift + Space`).
4. **Modelos inexistentes en Groq LLM:** Se intentaba invocar `groq/compound-mini` y `qwen/qwen3.6-27b` como respaldo, nombres no soportados en la API actual.
5. **Falso positivo en `verify_install.py`:** En sesiones de consola sin ventana activa de escritorio, `SendInput` devolvía error 5 (`ERROR_ACCESS_DENIED`), provocando falsos reportes de hook roto.

---

## 2. Soluciones Implementadas

### A. Portapapeles Permanente & Blindaje de `Win + V`
- En [`app/platform/injector.py`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/app/platform/injector.py):
  - **Preservación por defecto:** `inject_text` ahora opera con `restore_clipboard = False` por defecto. El texto transcrito o refinado **permanece en el portapapeles activo** del usuario. Si el usuario pierde el foco o habla mientras carga una página, su dictado no se pierde: basta con dar clic y presionar `Ctrl + V` o buscarlo en la cima de `Win + V`.
  - **No-op para cadenas vacías:** Se protegió `set_clipboard_text` con `if not text: return True`. Ya no es posible inyectar cadenas vacías `""` en el broker de Windows, eliminando al 100% las tarjetas en blanco en el historial de `Win + V`.
  - **Filtro estricto en restauración de emergencia:** Si se utiliza respaldo de emergencia, solo se restaura si el contenido previo tiene texto visible real (`_active_backup_text.strip()`).

### B. Depuración de Atajos (Solo Atajos Canónicos)
- En [`config.json`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/config.json) y [`config.example.json`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/config.example.json) se eliminaron `hotkey_diagnostics` y `hotkey_settings`.
- Únicamente se mantienen los dos atajos principales:
  - `hotkey_dictation`: `Win + Space`
  - `hotkey_rewrite`: `Ctrl + Shift + Space`
- En [`run.bat`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/run.bat) se limpió la salida de consola para anunciar únicamente los dos atajos operativos.

### C. Catálogo Activo de Groq LLM
- Se actualizaron los modelos de reserva a `openai/gpt-oss-120b` y `openai/gpt-oss-20b`, manteniendo `qwen/qwen3.8-27b` como el modelo recomendado.

### D. Acceso Directo Zero-Touch con Icono Oficial
- Se generó [`morocovoice.ico`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/morocovoice.ico) en resoluciones múltiples (16 a 256 px) con diseño Telat.
- En [`run.bat`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/run.bat), se integró la auto-creación del acceso directo en el Escritorio (`Moroco Voice.lnk`) si no existe.

### E. Cobertura de Pruebas Automatizadas
- En [`tests/test_injector.py`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/tests/test_injector.py), se añadieron pruebas para:
  - `test_set_clipboard_empty_string_is_noop` (verifica que cadenas vacías no toquen el portapapeles).
  - `test_inject_text_retains_payload_in_clipboard_by_default` (verifica la retención del texto dictado).
- En [`tests/test_llm.py`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/tests/test_llm.py), se verificó el filtrado de etiquetas `<think>`.
- **Certificación:** **46 / 46 pruebas unitarias aprobadas** exitosamente.
