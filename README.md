# MorocoVoice 🎙️

<div align="center">

![Windows 10/11](https://img.shields.io/badge/OS-Windows%2010%20%7C%2011%20x64-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Zero PyTorch](https://img.shields.io/badge/Architecture-Zero%20PyTorch%20(%3C450MB)-10b981?style=for-the-badge)
![Groq In-Cloud](https://img.shields.io/badge/STT%20Latency-~400ms%20(Groq%20Cloud)-f97316?style=for-the-badge)
![License MIT](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**La suite de dictado por voz y reescritura contextual para Windows con paridad frente a Wispr Flow, costo $0 y arquitectura ultraligera.**

[Comenzar en 3 Pasos](#-comenzar-en-3-pasos-instalador-zero-touch) • [Comparativa de Mercado](#-por-qu%C3%A9-morocovoice-comparativa-de-mercado) • [Atajos Globales](#-atajos-globales-de-teclado) • [Seguridad y Privacidad](#-arquitectura-de-seguridad-y-privacidad)

</div>

---

## 💡 ¿Por qué MorocoVoice? (Comparativa de Mercado)

Herramientas comerciales populares como **Wispr Flow** o **Superwhisper** cobran suscripciones recurrentes de entre **$144 y $180 USD al año**, consumen gigabytes de memoria o priorizan exclusivamente el ecosistema macOS.

**MorocoVoice** fue desarrollado por **Ricardo García ([@morocog](https://github.com/morocog))** para resolver esta necesidad de forma nativa en **Windows 10/11 x64**:

| Característica | 🎙️ **MorocoVoice** | ⚡ Wispr Flow | 🦉 Superwhisper |
| :--- | :---: | :---: | :---: |
| **Costo** | **$0 USD (Código Abierto)** | $12 – $15 / mes ($144+/año) | $8 – $20 / mes |
| **Plataforma Principal** | **Windows 10/11 x64 Nativo** | Mac / Windows | Prioridad Mac |
| **Latencia STT** | **~400 ms** (Groq LPU Turbo) | ~500 – 800 ms | ~800 – 1500 ms |
| **Reescritura Contextual** | **Sí (Automática según ventana)** | Sí (Planes superiores) | Sí |
| **Huella en Disco (RAM)** | **< 450 MB (Zero PyTorch)** | ~1.5 GB | ~850 MB |
| **Modo Local Offline** | **Sí (`faster-whisper` int8)** | No (100% dependiente de nube) | Sí |
| **Privacidad de Credenciales**| **100% en tu máquina (`.env` seguro)** | Centralizada en su nube | Centralizada en su nube |
| **Licencia** | **MIT License (Permisiva)** | Comercial Cerrada | Comercial Cerrada |

---

## 🚀 Comenzar en 3 Pasos (Instalador Zero-Touch)

No necesitas compilar modelos pesados ni pelear con comandos de terminal:

### 1. Clonar el Repositorio
```cmd
git clone https://github.com/morocog/MorocoVoice.git
cd MorocoVoice
```

### 2. Doble Clic en `run.bat`
Haz doble clic sobre el archivo **`run.bat`**.
- El lanzador inteligente detectará si es tu primera ejecución.
- Creará automáticamente el entorno virtual aislado (`.venv`).
- Instalará todas las dependencias industriales optimizadas (`onnxruntime`, `faster-whisper`, `groq`, `pystray`, `pywin32`).
- Inicializará **MorocoVoice** y lo dejará listo junto al reloj de Windows.

### 3. Configura tu Clave de Groq (Gratuita)
1. Al arrancar por primera vez, se abrirá la ventana de **Configuración de MorocoVoice**.
2. Obtén tu clave API gratuita en [console.groq.com/keys](https://console.groq.com/keys).
3. Pégala en el campo **Groq API Key**. Verás que la clave se enmascara automáticamente con asteriscos (`••••••••••••`) para protegerla de miradas indiscretas o transmisiones de pantalla.
4. Haz clic en **💾 Guardar y Aplicar**. ¡Listo!

---

## 🎯 Atajos Globales de Teclado

Diseñados con ergonomía y protección contra conflictos en teclados latinoamericanos e internacionales:

| Atajo | Función | Modo de Uso |
| :--- | :--- | :--- |
| **`Win + Space`** | **Dictado Inteligente** | Presiona para comenzar a hablar. Una cápsula flotante (HUD) translúcida te indicará `Escuchando...`. Vuelve a presionar al terminar y tu texto será transcrito e inyectado en la aplicación activa en ~400 ms. |
| **`Ctrl + Shift + Space`** | **Reescritura Contextual** | Selecciona cualquier texto crudo o informal con el ratón o teclado. Presiona el atajo y MorocoVoice detectará si estás en Outlook, Slack, Teams o VS Code para redactar una versión profesional y reemplazar la selección. |

> 💡 *Para ver los registros de depuración o cerrar la aplicación de forma limpia, simplemente haz clic derecho en el icono de MorocoVoice en la bandeja del sistema (junto al reloj de Windows).*

---

## 🖥️ Modos de Inferencia: Cloud First o 100% Local

MorocoVoice ofrece arquitectura dual según tus necesidades de conectividad o privacidad:

1. **Modo Cloud (Recomendado - Paridad Wispr Flow):**
   - Transcripción con `whisper-large-v3-turbo` en Groq Cloud (~400 ms de latencia).
   - Reescritura semántica contextual con `qwen/qwen3.8-27b` o `llama-3.3-70b-versatile`.
2. **Modo Local Offline (Privacidad Absoluta):**
   - Inferencia de voz local en CPU utilizando `faster-whisper` (cuantización `int8`, motor CTranslate2 optimizado con AVX2/AVX512).
   - Fallback semántico local compatible con **Ollama** (`http://localhost:11434`).

---

## 🔒 Arquitectura de Seguridad y Privacidad

- **Enmascaramiento de Credenciales Anti-Shoulder Surfing:** La API Key se muestra como asteriscos en la UI y se almacena localmente en el archivo `.env`, el cual está estrictamente excluido por `.gitignore`.
- **Logs Libres de PII (Privacy by Design):** El sistema de logging estructurado (`app/logging_setup.py`) tiene un filtro activo que **prohíbe tajantemente registrar transcripciones crudas, prompts o textos de usuario**. Solo se auditan tiempos de latencia y nombres de procesos activos.
- **Inyección por Fases no Destructiva:** `app/platform/injector.py` utiliza `SendInput` con liberación de modificadores residuales y respaldo del portapapeles original con bloqueo reentrante (`threading.RLock`), restaurando el contenido previo del usuario a los 120 ms.
- **Compatibilidad UIPI (User Interface Privilege Isolation):** Detecta automáticamente si una ventana destino corre con permisos de Administrador para prevenir fallos silenciosos de inyección en Windows.

---

## 📦 Estructura del Proyecto

```text
MorocoVoice/
├── app/
│   ├── audio/              # Captura de micrófono y VAD Silero ONNX
│   ├── engine/             # Motores STT (Groq Cloud Turbo & Local int8)
│   ├── llm/                # Reescritura semántica contextual y prompts
│   ├── platform/           # Hooks Win32, SendInput y atajos globales
│   ├── ui/                 # HUD flotante, Bandeja de sistema y Configuración
│   ├── contracts.py        # Esquemas de configuración inmutables
│   └── main.py             # Orquestador principal y mutex de instancia única
├── tests/                  # Suite de pruebas unitarias (24+ tests)
├── .env.example            # Plantilla de variables de entorno
├── config.json             # Ajustes de usuario sincronizados
├── custom_vocabulary.json  # Vocabulario especializado (jerga técnica, nombres)
├── LICENSE                 # Licencia MIT
├── requirements.txt        # Dependencias industriales (Zero PyTorch)
└── run.bat                 # Lanzador e instalador automatizado
```

---

## 🧪 Pruebas Unitarias

MorocoVoice incluye una suite de pruebas automatizadas que validan inyección, detección de modificadores, compatibilidad de teclado y parsing de atajos:

```powershell
.\.venv\Scripts\pytest -v
```

---

## 📄 Licencia y Reconocimientos

Distribuido bajo la Licencia **MIT**. Consulta [`LICENSE`](LICENSE) para más detalles.

Desarrollado con dedicación por **Ricardo García** ([GitHub: @morocog](https://github.com/morocog) / `rgarcia@telat-group.com`).
Si MorocoVoice te ahorra tiempo y dinero, ¡no dudes en dejarle una ⭐ estrella al repositorio!
