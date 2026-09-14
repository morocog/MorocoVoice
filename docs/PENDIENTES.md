# 📌 PENDIENTES & CONTINUIDAD MULTI-AGENTE: MOROCOVOICE

> 💡 **Validación Rápida con 1 Clic en Obsidian:** Haz clic directamente sobre la casilla `[ ]` para marcarla como `[x]` una vez probada en producción.

---

## 🔴 1. VERIFICACIONES PENDIENTES EN CALIENTE (seguras, no urgentes)

- [x] **Prueba de Dictado en Caliente (`Win + Space`) [v3.4.1]:** Probado y validado en caliente en Antigravity IDE con Groq Cloud (~1.2s de latencia por 350 caracteres).
- [x] **Prueba de Reescritura Contextual (`Ctrl + Shift + Space`) [v3.4.1]:** Probado y validado en caliente en texto crudo seleccionado; reemplazo contextual sin conflictos con la terminal.
- [x] **Enmascaramiento de Credenciales Groq (`SettingsModal`) [v3.5.0]:** Campo con asteriscos `••••••••`, botón alternador `👁️` y persistencia atómica en `.env` sin riesgo de exposición en Git.
- [x] **Instalador Zero-Touch en `run.bat` [v3.5.0]:** Detección automática de `.venv`, instalación desatendida de dependencias y arranque inmediato sin comandos de terminal.
- [ ] **Prueba de Atajo de Diagnóstico (`Ctrl + Shift + D`):** Pulsar `Ctrl + Shift + D` y corroborar que se abra `morocovoice.log` en el Bloc de Notas.
- [ ] **Prueba de Salida Ordenada (`Ctrl + Shift + Q`):** Pulsar `Ctrl + Shift + Q` y verificar que el icono desaparezca de la bandeja del sistema y el proceso finalice limpiamente.

---

## 🟡 2. MEJORAS FUTURAS (ROADMAP)

- [ ] **Soporte Directo CUDA 12 para Laptop Personal (`moroc`):** Configurar auto-detección de GPU NVIDIA para cambiar automáticamente a `device="cuda"` y `compute_type="float16"` cuando se ejecute en la estación personal.
- [ ] **Empaquetado Binario Standalone (`PyInstaller` / `Nuitka`):** Crear un ejecutable `MorocoVoice.exe` portable de 1 solo archivo para no requerir Python visible en máquinas de terceros.
- [x] **Panel de Configuración GUI Minimalista con Enmascaramiento [v3.5.0]:** Ventana visual reactiva con recarga en caliente, gestión protegida de Groq API Key y personalización de atajos.
- [ ] **Modo Push-to-Talk Opcional (Mantener presionado):** Permitir alternar entre modo Toggle y Push-to-Talk desde el panel de configuración.

---

## 🟢 3. DEUDA TÉCNICA CONOCIDA & DECISIONES ARQUITECTÓNICAS

- **Rebranding Canónico MorocoVoice:** Named Mutex `Global\MorocoVoice_SingleInstance_Mutex`, log canónico `morocovoice.log`, UI y bandeja actualizados con metadatos a nombre de Ricardo García (`morocog`).
- **Exclusión de PyTorch:** Se mantiene la política estricta de Cero-PyTorch utilizando exclusivamente ONNX Runtime y CTranslate2 para reducir el footprint de instalación de ~4.5 GB a menos de 450 MB.
- **Auditoría UIPI:** Verificación obligatoria de `TokenElevation` para evitar que Windows bloquee silenciosamente la inyección de teclado cuando una ventana activa corre como Administrador.
- **Inyección por Fases no Destructiva:** `SendInput` con 3 fases, liberación de modificadores residuales y respaldo del portapapeles con bloqueo reentrante (`threading.RLock`), restaurando a los 120 ms.
