# Ficha Técnica: Rebranding a MorocoVoice, Gestión Segura de Credenciales e Instalador Zero-Touch

- **Fecha:** 2026-09-14
- **Versión Desplegada:** `MorocoVoice v3.5.0`
- **Autor:** Ricardo García (`morocog`)
- **Estado:** Implementado, Verificado con 26 Pruebas Automatizadas y Documentado

---

## 1. Contexto y Síntomas
La aplicación de dictado por voz y refinamiento semántico contextual requería pasar de una prueba técnica local denominada genéricamente `VoiceFlow-Win` a un producto de código abierto de nivel industrial bautizado como **MorocoVoice** (en honor al alias de GitHub del autor, `morocog`), listo para compartirse públicamente sin fricciones para usuarios de Windows 10/11 x64.
Adicionalmente, se identificó que:
1. La clave de API de Groq requería configuración manual en archivos de texto, exponiéndose a filtraciones accidentales si se guardaba en archivos rastreados por Git (`config.json`) o permitiendo que curiosos o transmisiones de pantalla (*shoulder surfing*) leyeran la clave.
2. Si un usuario externo clonaba el repositorio, carecía de un mecanismo *"Plug & Play"* de un solo clic para inicializar el entorno virtual e instalar las dependencias de forma desatendida.
3. El proyecto carecía de una Licencia estándar (MIT) y de un `README.md` comparativo de mercado que explicara por qué MorocoVoice supera a soluciones comerciales de $144 USD/año como Wispr Flow o Superwhisper.

---

## 2. Causa Raíz
- **Riesgo de Fuga de Credenciales:** Si bien `.env` estaba protegido en `.gitignore`, la interfaz gráfica no contaba con un mecanismo para persistir la clave de Groq directamente en `.env` manteniendo una máscara visual (`show="*"`) en pantalla.
- **Acoplamiento al Entorno Local:** `run.bat` asumía que `.venv` ya existía previamente en la máquina local; en máquinas nuevas o clonadas, el script terminaba con un mensaje de error solicitando intervención manual del usuario.
- **Dispersión de Nombres de Mutex y Logs:** El Named Mutex de Win32 y los registros de log conservaban la denominación anterior (`VoiceFlow`), impidiendo una identidad unificada del producto.

---

## 3. Solución Implementada
1. **Entrada Enmascarada y Persistencia Segura (`app/ui/settings_window.py`):**
   - Se implementó `_create_masked_entry_row()` con `tk.Entry(..., show="*")` y botón alternador `👁️` / `🔒`.
   - Se añadió la rutina de persistencia atómica `_persist_groq_api_key_to_env()`, que actualiza o crea la variable `GROQ_API_KEY` exclusivamente en el archivo local `.env` sin modificar otras variables y sin tocar `config.json` (protegiendo el repositorio de commits accidentales).
   - Inyección en caliente a `os.environ["GROQ_API_KEY"]` y recarga en caliente de `EngineManager` y `SemanticRewriter` sin necesidad de reiniciar la aplicación.
2. **Instalador Zero-Touch Autoportante (`run.bat`):**
   - El script evalúa la existencia de `.venv\Scripts\python.exe`.
   - Si no existe, detecta `python` o `py -3` en el sistema operativo, crea el entorno virtual aislado, actualiza `pip`, instala `requirements.txt` y genera `.env` a partir de la nueva plantilla `.env.example`.
   - Incluye detección y cierre seguro de procesos huérfanos previos para prevenir colisiones de Mutex.
3. **Rebranding Integral a MorocoVoice:**
   - Named Mutex: `Global\MorocoVoice_SingleInstance_Mutex`.
   - Registro en log: `morocovoice.log` (excluido en `.gitignore`).
   - Títulos de ventana, menús de bandeja del sistema (`pystray`), tooltips interactivos y notificaciones toast de Windows calibradas a `MorocoVoice v3.5.0`.
   - Alias de compatibilidad `VoiceFlowApplication = MorocoVoiceApplication` para prevenir regresiones en pruebas existentes.
4. **Licencia MIT y Showcase README:**
   - Creación del archivo formal `LICENSE` (Copyright 2026 Ricardo García).
   - Creación de `.env.example` con comentarios claros.
   - Rediseño completo de `README.md` con badges, matriz comparativa de mercado ($0 vs $144/año de Wispr Flow), guía de inicio rápido en 3 pasos y especificaciones técnicas.

---

## 4. Anti-Patrones / Prohibiciones Establecidas
- **PROHIBICIÓN ABSOLUTA:** NUNCA almacenar `groq_api_key` dentro de `config.json`. `config.json` viaja en el control de versiones de Git; las credenciales sensibles deben residir única y exclusivamente en `.env` o en la memoria volátil del proceso.
- **PROHIBICIÓN:** NUNCA mostrar la clave de API en texto plano por defecto en la interfaz visual. Debe usar siempre `show="*"` para proteger la privacidad del usuario en presentaciones o capturas.
- **PROHIBICIÓN:** NUNCA requerir comandos manuales en terminal a los usuarios finales de Windows para instalar dependencias; `run.bat` debe ser siempre autosuficiente.

---

## 5. Verificación & Evidencia
- **Pruebas Automatizadas Unitarias (`pytest -v`):**
  - Se crearon pruebas dedicadas en `tests/test_settings.py` para validar la persistencia en `.env`, el enmascaramiento y el Mutex.
  - Resultado: **26 pruebas ejecutadas y aprobadas al 100%** en 1.16 segundos.
- **Auditoría de Formato y Estilo (`ruff check`):**
  - Todas las verificaciones de código pasaron exitosamente (`All checks passed!`).
- **Seguridad en Git (`git status` & `git diff`):**
  - Verificado que `.env` no aparece en cambios ni en archivos no rastreados.
  - Verificado que `.env.example` contiene únicamente variables de ejemplo sin credenciales reales.
