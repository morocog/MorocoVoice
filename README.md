# MorocoVoice 🎙️

<div align="center">

![Version](https://img.shields.io/badge/Version-v1.0.5-22c55e?style=for-the-badge)
![Windows 10/11](https://img.shields.io/badge/OS-Windows%2010%20%7C%2011%20x64-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Zero PyTorch](https://img.shields.io/badge/Architecture-Zero%20PyTorch%20(%3C450MB)-10b981?style=for-the-badge)
![Latencia Pipeline](https://img.shields.io/badge/Latencia-~1.2s%20(Pipeline%20Completo)-f97316?style=for-the-badge)
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
| **Latencia STT** | **~400 ms API / ~1.2s Total** | ~500 – 800 ms | ~800 – 1500 ms |
| **Reescritura Contextual** | **Sí (Automática según ventana)** | Sí (Planes superiores) | Sí |
| **Huella en Disco (RAM)** | **< 450 MB (Zero PyTorch)** | ~1.5 GB | ~850 MB |
| **Modo Local Offline** | **Sí (`faster-whisper` int8)** | No (100% dependiente de nube) | Sí |
| **Privacidad de Credenciales**| **100% en tu máquina (`.env` seguro)** | Centralizada en su nube | Centralizada en su nube |
| **Licencia** | **MIT License (Permisiva)** | Comercial Cerrada | Comercial Cerrada |

---

## 🚀 Comenzar en 3 Pasos (Instalador Zero-Touch)

No necesitas compilar modelos pesados ni conocimientos técnicos:

### 1. Descargar o Clonar el Repositorio
- **Opción A (Directa, sin Git):** Haz clic en el botón verde **Code ➔ Download ZIP** arriba en GitHub y descomprime la carpeta en tu equipo.
- **Opción B (Con terminal Git):**
```cmd
git clone https://github.com/morocog/MorocoVoice.git
cd MorocoVoice
```

### 2. Doble Clic en `run.bat`
Haz doble clic sobre el archivo **`run.bat`**.
- El lanzador inteligente detectará si es tu primera ejecución.
- Verificará que cuentes con **Python 3.11 o superior**.
- Creará automáticamente el entorno virtual aislado (`.venv`).
- Instalará todas las dependencias industriales optimizadas (`onnxruntime`, `faster-whisper`, `groq`, `pystray`, `pywin32`).
- Inicializará **MorocoVoice** y lo dejará listo junto al reloj de Windows.

### 3. Configura tu Clave de Groq (Gratuita)
1. Al arrancar por primera vez, se abrirá la ventana de **Configuración de MorocoVoice**.
2. Haz clic en el botón **🔑 Obtener clave gratuita en console.groq.com (1 clic)** que aparece en pantalla para abrir la consola de Groq en tu navegador.
3. Crea tu cuenta gratuita en Groq, genera tu API Key y cópiala.
4. Pégala en el campo **Groq API Key** (se enmascara automáticamente con asteriscos `••••••••••••`).
5. Haz clic en **💾 Guardar y Aplicar**. ¡Listo!

### 4. (Opcional) Enséñale tus Palabras Técnicas y Jerga
En la pestaña **📖 Vocabulario Personalizado** dentro de Configuración:
- Ingresa hasta **30 palabras técnicas, acrónimos o nombres propios** (ej: `GitHub`, `API`, `Python`, `WFM`, o nombres de tus clientes).
- Whisper y el **corrector determinista con difflib** de MorocoVoice priorizarán estos términos para garantizar transcripciones exactas (evitando errores fonéticos como `GITCOP` en lugar de `GitHub`).

---

## 🎯 Atajos Globales de Teclado

Diseñados con ergonomía y protección contra conflictos en teclados latinoamericanos e internacionales:

| Atajo | Función | Modo de Uso |
| :--- | :--- | :--- |
| **`Win + Space`** | **Dictado Inteligente** | Presiona para comenzar a hablar. Una cápsula flotante (HUD) translúcida te indicará `Escuchando...`. Vuelve a presionar al terminar y tu texto será transcrito e inyectado en la aplicación activa. |
| **`Ctrl + Shift + Space`** | **Reescritura Contextual** | Selecciona cualquier texto crudo o informal con el ratón o teclado. Presiona el atajo y MorocoVoice detectará si estás en Outlook, Slack, Teams o VS Code para redactar una versión profesional y reemplazar la selección. |
| **`Ctrl + Alt + S`** | **Abrir Configuración** | Vía de teclado a la ventana de configuración. Existe porque el icono de la bandeja puede no estar disponible (Windows 11 esconde los iconos nuevos en el cajón `^`, y un entorno restringido puede rechazarlos). Nunca te deja sin acceso. |
| **`Ctrl + Shift + D`** | **Diagnóstico (Logs)** | Abre `morocovoice.log` en el Bloc de notas para inspeccionar qué está pasando. |

> 💡 *El icono de la bandeja del sistema (junto al reloj) ofrece el menú completo: Configuración, Abrir Logs y Salir. Si no lo ves, búscalo en el cajón de desbordamiento `^` y arrástralo hacia fuera — o usa `Ctrl + Alt + S`.*
>
> ⚠️ **`Win + Space` es también el atajo nativo de Windows para cambiar de idioma de teclado.** MorocoVoice lo escucha sin suprimirlo, así que en equipos con más de un idioma instalado conviene cambiar el atajo de dictado por otro libre (por ejemplo `Ctrl + Alt + Space`) desde la ventana de Configuración.

---

## 🖥️ Modos de Inferencia: Cloud First o 100% Local

MorocoVoice ofrece arquitectura dual según tus necesidades de conectividad o privacidad:

1. **Modo Cloud (Recomendado - Paridad Wispr Flow):**
   - Transcripción con `whisper-large-v3-turbo` en Groq Cloud (~400 ms de latencia API).
   - Reescritura semántica contextual ultrarrápida con `qwen/qwen3.8-27b`.
2. **Modo Local Offline (Privacidad Absoluta):**
   - Inferencia de voz local en CPU utilizando `faster-whisper` (cuantización `int8`, motor CTranslate2 optimizado con AVX2/AVX512).
   - Fallback semántico local compatible con **Ollama** (`http://localhost:11434`).

---

## 🔒 Arquitectura de Seguridad y Privacidad

- **Enmascaramiento de Credenciales Anti-Shoulder Surfing:** La API Key se muestra como asteriscos en la UI y se almacena localmente en el archivo `.env`, el cual está estrictamente excluido por `.gitignore`.
- **Logs Libres de PII (Privacy by Design):** El sistema de logging estructurado (`app/logging_setup.py`) tiene un filtro activo que **prohíbe tajantemente registrar transcripciones crudas, prompts o textos de usuario**. Solo se auditan tiempos de latencia y nombres de procesos activos.
- **Inyección por Fases no Destructiva:** `app/platform/injector.py` utiliza `SendInput` con liberación de modificadores residuales y respaldo del contenido textual Unicode (`CF_UNICODETEXT`) del portapapeles con bloqueo reentrante (`threading.RLock`), restaurando el texto previo del usuario a los 120 ms (formatos no textuales ricos como capas gráficas u objetos OLE no se preservan por diseño de la API Win32).
- **Compatibilidad UIPI (User Interface Privilege Isolation):** Detecta automáticamente si una ventana destino corre con permisos de Administrador para prevenir fallos silenciosos de inyección en Windows.

---

## 📦 Estructura del Proyecto

```text
MorocoVoice/
├── app/
│   ├── audio/              # Captura de micrófono y VAD Silero ONNX
│   ├── engine/             # Motores STT (Groq Cloud Turbo & Local int8)
│   ├── llm/                # Reescritura semántica contextual y prompts
│   ├── platform/           # Hooks Win32, SendInput, atajos globales y
│   │                       #   environment.py (sonda de seguridad de Windows)
│   ├── ui/                 # HUD flotante, Bandeja de sistema y Configuración
│   ├── contracts.py        # Esquemas de configuración inmutables
│   ├── logging_setup.py    # Logging sin PII + captura de errores de hilos
│   └── main.py             # Orquestador principal y mutex de instancia única
├── docs/                   # Auditorías, notas de versión y TROUBLESHOOTING.md
├── tests/                  # Suite de pruebas unitarias (43 tests)
├── .env.example            # Plantilla de variables de entorno
├── config.example.json     # Plantilla de configuración de usuario
├── custom_vocabulary.json  # Vocabulario especializado (jerga técnica, nombres)
├── diagnostico.bat         # Diagnóstico del sistema en un clic
├── verify_install.py       # Preflight: audio, hardware y entorno de seguridad
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

## 🩺 Solución de Problemas

Si el icono no aparece junto al reloj, o `Win + Space` no hace nada, **no asumas que la
aplicación está rota**. La causa más habitual es el **entorno de seguridad de Windows**,
no el código.

**Ejecuta primero:**

```cmd
diagnostico.bat
```

Analiza audio, hardware y —lo más importante— el **entorno de seguridad**, con veredicto
claro y el comando exacto para arreglarlo.

| Síntoma | Causa más probable |
| :--- | :--- |
| La app arranca, pero **ni icono ni atajos** | El proceso corre en integridad **Low** (carpeta etiquetada por un sandbox de agente de IA). Windows deniega la bandeja y el hook de teclado queda ciego |
| El icono está pero escondido en el cajón `^` | Windows 11 no coloca los iconos nuevos junto al reloj: arrástralo fuera |
| `Win + Space` **cambia el idioma** del teclado | Colisión con el atajo nativo de Windows: cambia el atajo de dictado |
| Sale el HUD pero no escribe | La ventana destino corre como Administrador (UIPI) |

👉 **Guía completa y detallada: [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)**

### Por qué existe esta sección

Un usuario reportó que la aplicación «se apagaba» y «ya no dejaba las opciones junto al
reloj». La investigación demostró que el código era correcto: la carpeta del proyecto
tenía una **etiqueta de integridad `Low` heredable** (puesta por el sandbox de un agente
de IA), y por eso Windows lanzaba el proceso en Low, donde **deniega el icono de bandeja
y descarta todas las pulsaciones** del hook de teclado. Como la app corre con `pythonw`,
las excepciones se descartaban sin dejar rastro: parecía viva y no funcionaba.

Desde la **v1.0.5** MorocoVoice detecta ese contexto al arrancar, lo explica en el log con
el comando de solución, verifica de verdad que el teclado se captura, y garantiza el
atajo `Ctrl + Alt + S` para que **nunca** te quedes sin acceso a Configuración.

---

## 📄 Licencia y Reconocimientos

Distribuido bajo la Licencia **MIT**. Consulta [`LICENSE`](LICENSE) para más detalles.

Desarrollado con dedicación por **Ricardo García** ([GitHub: @morocog](https://github.com/morocog) / `rgarcia@telat-group.com`).
Si MorocoVoice te ahorra tiempo y dinero, ¡no dudes en dejarle una ⭐ estrella al repositorio!
