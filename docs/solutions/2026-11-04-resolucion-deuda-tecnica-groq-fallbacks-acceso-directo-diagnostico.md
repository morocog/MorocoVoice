# Ficha Técnica: Resolución de Deuda Técnica, Fallbacks de Groq y Acceso Directo Zero-Touch

**Fecha:** 2026-11-04  
**Repositorio:** `MorocoVoice`  
**Versión:** `v1.0.5`  
**Autor:** Antigravity AI & Ricardo García  

---

## 1. Contexto y Diagnóstico

Durante la auditoría de deuda técnica de la estación de trabajo se identificaron las siguientes oportunidades de mejora:
1. **Modelos inexistentes en la cadena de contingencia de Groq:** [`app/llm/rewriter.py`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/app/llm/rewriter.py) intentaba como alternativas `groq/compound-mini` y `qwen/qwen3.6-27b`, nombres no soportados en el catálogo de Groq que desencadenaban excepciones HTTP 404 en caso de contingencia.
2. **Falso positivo crítico en `verify_install.py`:** Al ejecutarse en consolas de segundo plano o sin foco de ventana de escritorio activo, la llamada Win32 a `SendInput` para simular la pulsación de prueba devolvía 0 (`ERROR_ACCESS_DENIED` / 5). El verificador asumía erróneamente un contexto de integridad `Low` y emitía un fallo crítico (`exit 1`) aun cuando el token del proceso reportaba integridad `Medium` (0x2000) y el hook de teclado estaba completamente vivo.
3. **Ausencia de acceso directo automatizado e icono oficial:** No existía un archivo de icono `.ico` empaquetado para Windows ni un mecanismo en `run.bat` que garantizara la presencia del acceso directo en el Escritorio.
4. **Desfase de llaves en configuración local:** [`config.json`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/config.json) no declaraba `hotkey_settings` ni `hotkey_diagnostics`.

---

## 2. Soluciones Implementadas

### A. Corrección del Catálogo de Fallback en Groq LLM
- Se consultó directamente el endpoint `/models` de la API de Groq para obtener el catálogo activo.
- En [`app/llm/rewriter.py`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/app/llm/rewriter.py), se actualizaron los modelos de reserva a `openai/gpt-oss-120b` y `openai/gpt-oss-20b`, manteniendo `qwen/qwen3.8-27b` como modelo principal recomendado.
- En [`app/ui/settings_window.py`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/app/ui/settings_window.py), se ajustó el texto de ayuda correspondiente.

### B. Diagnóstico Resiliente en `verify_install.py`
- En [`verify_install.py`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/verify_install.py), se valida el valor de retorno de `send_vk_tap(VK_SHIFT)`.
- Si `SendInput` no puede sintetizarse debido a la ejecución en una consola sin ventana de escritorio activa pero el listener de `pynput` y el contexto de seguridad son válidos (`Medium`), el diagnóstico lo reporta con precisión informativa en lugar de abortar con fallo crítico.

### C. Generación de Icono Oficial y Acceso Directo Zero-Touch
- Se generó [`morocovoice.ico`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/morocovoice.ico) con resoluciones 16x16, 32x32, 48x48, 64x64, 128x128 y 256x256, respetando el branding Telat (azul `#3284C6`, aro dorado `#FECA66` y micrófono nítido).
- En [`run.bat`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/run.bat), se integró una comprobación para auto-crear el acceso directo en el Escritorio (`Moroco Voice.lnk`) si no existe, asegurando una experiencia zero-touch en cualquier equipo.

### D. Alineación de Esquema de Configuración y Cobertura de Pruebas
- Se actualizaron las llaves `hotkey_settings` y `hotkey_diagnostics` en [`config.json`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/config.json).
- En [`tests/test_llm.py`](file:///c:/Users/moroc/Documents/GitHub/MorocoVoice/tests/test_llm.py), se añadió una prueba unitaria para validar el filtrado de etiquetas `<think>` provenientes de modelos con razonamiento.
- Se ejecutó la suite completa de pruebas: **44/44 pruebas pasadas exitosamente**.
