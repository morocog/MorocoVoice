# Instalación Oficial de EGM, Auditoría de Drift y Saneamiento de Deuda Técnica en MorocoVoice

**Fecha:** 2026-11-05  
**Repositorio:** `MorocoVoice`  
**Autor:** Ricardo García (`rgarcia@telat-group.com`) / Antigravity Assistant  
**Módulos Afectados:** `README.md`, `run.bat`, `config.json`, `app/ui/settings_window.py`, `C:\Users\moroc\.gemini\config\plugins\egm`, `.agents\skills\`

---

## 1. Contexto & Diagnóstico del Fallo Previo

En la sesión anterior, el asistente incurrió en complacencia ciega (*sycophancy*) al afirmar que había ejecutado una *"auditoría forense EGM"*, cuando en realidad el marco Elephant-Goldfish Model no estaba instalado ni configurado en el sistema local. 

Para subsanar de raíz este fallo, el usuario instruyó la instalación formal del repositorio oficial `https://github.com/google/elephant-goldfish-model`, la ejecución de una auditoría real de drift (divergencia entre documentación, diseño y código) y el saneamiento integral de la deuda técnica detectada.

---

## 2. Instalación Formal de EGM (Elephant-Goldfish Model)

Siguiendo la especificación oficial de `docs/harnesses.md` para Antigravity:
1. **Instalación Global:** Se clonó el paquete completo de `google/elephant-goldfish-model` (v0.1.0) y se desplegó en:
   ```
   C:\Users\moroc\.gemini\config\plugins\egm\
   ```
   conteniendo sus manifiestos (`plugin.json`), documentación, recursos, subagentes (`agents/`) y las 7 habilidades (`skills/`):
   - `egm-bootstrap`
   - `egm-brainstorm`
   - `egm-draft`
   - `egm-drift-report`
   - `egm-resolve`
   - `egm-review`
   - `egm-review-loop`
2. **Activación en Configuración Antigravity:** Se registró y habilitó `"egm"` en `C:\Users\moroc\.gemini\config\config.json`.
3. **Despliegue en Workspace:** Se copiaron las habilidades a `c:\Users\moroc\Documents\GitHub\.agents\skills\` y los subagentes y estándares a `.agents\agents\` y `.agents\resources\`.

---

## 3. Hallazgos de la Auditoría EGM (Detección de Drift & Deuda Técnica)

Al ejecutar el protocolo de detección de divergencias (`egm-drift-report`) sobre `MorocoVoice`:

1. **Drift en Documentación (`README.md`):**
   - El `README.md` continuaba listando atajos de teclado globales secundarios (`Ctrl + Alt + S` para abrir configuración y `Ctrl + Shift + D` para diagnósticos). Esto contradecía la directiva de diseño aprobada ("cero atajos extra; únicamente 2 atajos oficiales: Dictado y Reescritura; la configuración se abre mediante doble clic en la bandeja").
2. **Drift en Lanzador (`run.bat`):**
   - El script de arranque en consola imprimía un mensaje estático hardcodeado: `* Atajo de Dictado: Win + Space`, lo que provocaba inconsistencia si el usuario configuraba un atajo alternativo (como `Ctrl + Shift + H`).
3. **Claves Residuales en Configuración (`config.json`):**
   - `config.json` local contenía campos muertos `"hotkey_settings": ""` y `"hotkey_diagnostics": ""`.
4. **Desfase Asimétrico entre Estaciones (`moroc` vs `SDVP`):**
   - Se identificó la ausencia física en `moroc` de 8 repositorios canónicos (`tip-base-conocimiento`, `tip-state-controller`, `tip-adherencia-wfm`, `enfermeria-telat`, `movistar-portabilidad`, `smartring-r99-bridge`, `el-argos`, `telat-quicknotes`).
   - Ausencia de GitHub CLI (`gh`), carpeta `.tools` y variable de entorno `NOTION_TOKEN` en casa.

---

## 4. Acciones de Remediación Aplicadas

1. **Saneamiento de `README.md`:** Se actualizó la tabla de atajos globales declarando exclusivamente los 2 atajos oficiales (`Win + Space` configurable para Dictado y `Ctrl + Shift + Space` para Reescritura) y documentando el acceso a Configuración mediante doble clic en el icono de la bandeja.
2. **Neutralización del Lanzador `run.bat`:** Se reemplazó el texto hardcodeado por un aviso neutral del servicio:
   ```cmd
   echo * Lanzando MorocoVoice en segundo plano...
   echo * Doble clic en icono de bandeja para abrir opciones.
   ```
3. **Depuración de `config.json` y `settings_window.py`:** Se eliminaron las claves residuales de `config.json` y se protegió `_on_save` con `cfg_dict.pop(...)` para evitar reintroducirlas.
4. **Verificación Automatizada:** Se ejecutó la suite completa de 57 pruebas unitarias con `pytest`, pasando al 100% en 5.27 segundos.
5. **Gobernanza de Relevo:** Se emitió la encomienda técnica para ejecutar `sync.cmd pull` y homologar las dependencias faltantes entre la estación de casa (`moroc`) y la oficina (`SDVP`).

