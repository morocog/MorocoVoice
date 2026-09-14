# VoiceFlow-Win (Arquitectura Industrial v3.4.1)

Suite universal de dictado por voz y refinamiento semántico contextual para **Windows 10/11 x64 (Python 3.11+)**, diseñada para ofrecer paridad de experiencia frente a **Wispr Flow**, sin suscripciones mensuales ni límites arbitrarios de palabras.

---

## 🎯 Atajos Globales de Teclado

Los atajos globales están calibrados para evitar colisiones con teclados latinoamericanos (`AltGr`) e IDEs de desarrollo:

| Atajo | Acción | Descripción |
| :--- | :--- | :--- |
| **`Alt + Space`** | **Dictado Inteligente** | Alterna la grabación (Push-to-Talk o Toggle). Inicia con un `blip` procedural, muestra el HUD flotante, transcribe y pega el texto automáticamente con respaldo y restauración de portapapeles en 80 ms. |
| **`Ctrl + Shift + Space`** | **Reescritura Contextual** | Captura la selección de texto en la aplicación activa, la pule con el modelo semántico respetando el contexto (Outlook, VS Code, Slack, Teams) y reemplaza el texto seleccionado. |
| **`Ctrl + Shift + D`** | **Diagnóstico en Vivo** | Abre `voiceflow.log` en el Bloc de Notas para inspección en caliente. |
| **`Ctrl + Shift + Q`** | **Apagado Ordenado** | Ejecuta el protocolo `shutdown_ordered()`: restaura el portapapeles original, detiene los hooks de teclado y finaliza el proceso de forma segura. |

---

## 🖥️ Matriz de Hardware y Aceleración

> [!IMPORTANT]
> **Alcance de Hardware (v1) y Exclusión de GPUs AMD/Intel Integradas**:
> La aceleración local por hardware en v1 está optimizada para **GPUs NVIDIA con CUDA 12 y controladores >= 525**.
> Las GPUs AMD e Intel (como Intel UHD Graphics 630) **no están soportadas para aceleración local en v1** y realizan un fallback automático a:
> 1. **Modo Híbrido Cloud (Groq Whisper-large-v3)**: Latencia ultra-rápida (~300-500 ms, paridad real Wispr Flow).
> 2. **Modo CPU int8 (`faster-whisper`)**: Inferencia local en CPU con cuantización `int8` (latencia ~1.5 - 2.5 s).

### Matriz de Selección por VRAM

| VRAM Detectada | Modelo Whisper Local | Modelo LLM Contextual | Keep Alive | Modo de Operación |
| :--- | :--- | :--- | :--- | :--- |
| **>= 12 GB** | `large-v3` | `llama3.1:8b` | `30m` o `-1` | Local Máxima Precisión |
| **8–11 GB** | `medium` | `qwen2.5:3b` | `30m` | Local Equilibrado |
| **6–7 GB** | `small` | `qwen2.5:1.5b` | `15m` | Local Compacto |
| **4–5 GB** | `base` | `qwen2.5:1.5b` | `10m` | Local Ligero |
| **< 4 GB / CPU** | `base` / `small` (int8) | Fast-path puro (o Groq Cloud) | N/A | CPU Fallback / Cloud First |

---

## 🚀 Instalación y Despliegue en Windows 11

### 1. Requisitos Previos
- Windows 10/11 x64.
- Python 3.11 x64 (instalado en el entorno de usuario).
- Micrófono o auricular USB compatible con WASAPI.

### 2. Configuración del Entorno
```powershell
# Clonar o ubicarse en el directorio
cd c:\Users\SDVP\Documents\GitHub\VoiceFlow-Win

# Crear entorno virtual (si no existe)
py -3.11 -m venv .venv

# Instalar dependencias industriales
.\.venv\Scripts\pip install -r requirements.txt
```

### 3. Configuración de API Keys (Opcional pero Recomendado para Paridad Wispr Flow)
Copia `.env.example` a `.env`:
```env
# Clave gratuita de Groq Cloud para transcripción sub-segundo:
GROQ_API_KEY=gsk_...
```
*Si no defines `GROQ_API_KEY`, VoiceFlow arrancará de forma predeterminada en modo CPU Local (`faster-whisper int8`), 100% privado y desconectado.*

### 4. Diagnóstico de Sistema
Ejecuta la herramienta de auditoría de hardware y dependencias:
```powershell
.\.venv\Scripts\python verify_install.py
```
O con salida JSON:
```powershell
.\.venv\Scripts\python verify_install.py --json
```

### 5. Iniciar la Aplicación
Haz doble clic en `run.bat` o ejecútalo en la terminal:
```powershell
.\run.bat
```
VoiceFlow-Win se cargará discretamente en la bandeja del sistema (System Tray junto al reloj).

---

## 🔒 Arquitectura de Seguridad y Privacidad

1. **Privacidad PII en Logs**: El módulo `app/logging_setup.py` utiliza un `RotatingFileHandler` (5 MB, 3 backups) que **prohíbe estrictamente registrar texto transcrito crudo, respuestas del LLM, prompts o términos de vocabulario**. Solo se registran metadatos técnicos (duración en ms, conteo de caracteres, nombre de la aplicación activa).
2. **Integridad del Portapapeles**: La inyección por `SendInput` respalda el portapapeles original, pega el texto y lo restaura a los 80 ms. Si detecta que un gestor externo (como Ditto o Win+V) modificó el portapapeles en ese lapso, cancela la restauración para no sobreescribir datos del usuario. Además, se registra un hook de seguridad en `atexit` (`emergency_restore`).
3. **Prevención UIPI (User Interface Privilege Isolation)**: Antes de inyectar texto, `app/llm/context.py` verifica si la aplicación destino corre como Administrador (`TokenElevation`). Si VoiceFlow corre como usuario estándar y la app destino es Administrador, el sistema muestra una advertencia en el HUD y cancela la inyección para evitar excepciones Win32 silenciosas.
4. **Filtro de Alucinaciones**: El subsistema `app/engine/stt_local.py` implementa coincidencia difusa (`difflib > 0.85`) contra créditos de subtítulos conocidos ("amara.org", "gracias por ver el video") y detecta bucles repetitivos de n-gramas (>= 4 palabras repetidas >= 3 veces).
5. **Truncado de Vocabulario**: `custom_vocabulary.json` se trunca automáticamente a un máximo estricto de 30 términos para no degradar el Word Error Rate (WER) de Whisper.

---

## 🛡️ Exclusiones de Antivirus / Microsoft Defender (Si Aplica)
Dado que VoiceFlow-Win utiliza hooks globales de teclado (`pynput`) e inyección Win32 (`SendInput`), algunas suites corporativas de EDR o Defender pueden requerir añadir la carpeta del proyecto como exclusión:
```powershell
# En PowerShell elevado (si fuera necesario):
Add-MpPreference -ExclusionPath "c:\Users\SDVP\Documents\GitHub\VoiceFlow-Win"
```

---

## 🧪 Ejecución de Pruebas Automatizadas

La suite completa de pruebas unitarias valida la síntesis de sonido, VAD, inyección Win32, filtros de vocabulario, contexto y guardarraíles de LLM:

```powershell
.\.venv\Scripts\pytest
```
Resultado esperado: **100% de pruebas pasando**.
