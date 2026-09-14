# 📌 PENDIENTES & CONTINUIDAD MULTI-AGENTE: VOICEFLOW-WIN

> 💡 **Validación Rápida con 1 Clic en Obsidian:** Haz clic directamente sobre la casilla `[ ]` para marcarla como `[x]` una vez probada en producción.

---

## 🔴 1. VERIFICACIONES PENDIENTES EN CALIENTE (seguras, no urgentes)

- [x] **Prueba de Dictado en Caliente (`Win + Space` / `Alt + Space`) [v3.4.1]:** Probado y validado en caliente en Antigravity IDE con Groq Cloud (~1.2s de latencia por 350 caracteres).
- [x] **Prueba de Reescritura Contextual (`Ctrl + Shift + Space`) [v3.4.1]:** Probado y validado en caliente en texto crudo seleccionado; reemplazo contextual sin conflictos con la terminal.
- [ ] **Prueba de Atajo de Diagnóstico (`Ctrl + Shift + D`):** Pulsar `Ctrl + Shift + D` y corroborar que se abra `voiceflow.log` en el Bloc de Notas.
- [ ] **Prueba de Salida Ordenada (`Ctrl + Shift + Q`):** Pulsar `Ctrl + Shift + Q` y verificar que el icono desaparezca de la bandeja del sistema y el proceso finalice limpiamente.
- [x] **Configuración de `GROQ_API_KEY` (Completado):** Clave `MorocoVoice` configurada en `.env` y validada en caliente con `whisper-large-v3-turbo` y `qwen/qwen3.8-27b` (~400 ms de latencia).

---

## 🟡 2. MEJORAS FUTURAS (ROADMAP)

- [ ] **Soporte Directo CUDA 12 para Laptop `moroc`:** Configurar auto-detección de GPU NVIDIA para cambiar automáticamente a `device="cuda"` y `compute_type="float16"` cuando se ejecute en la estación personal.
- [ ] **Empaquetado Binario Standalone (`PyInstaller` / `Nuitka`):** Crear un ejecutable `VoiceFlow.exe` portable de 1 solo archivo para no requerir entorno de Python visible.
- [x] **Panel de Configuración GUI Minimalista [v3.4.1]:** Ventana visual reactiva con recarga en caliente, guardado atómico en `config.json` y personalización de atajos y modelos.
- [ ] **Modo Push-to-Talk Opcional (Mantener presionado):** Permitir alternar entre modo Toggle y Push-to-Talk desde el panel de configuración.

---

## 🟢 3. DEUDA TÉCNICA CONOCIDA & DECISIONES ARQUITECTÓNICAS

- **Exclusión de PyTorch:** Se mantiene la política estricta de Cero-PyTorch utilizando exclusivamente ONNX Runtime y CTranslate2 para reducir el footprint de instalación de ~4.5 GB a menos de 450 MB.
- **Auditoría UIPI:** Se implementó verificación obligatoria de `TokenElevation` para evitar que Windows bloquee silenciosamente la inyección de teclado cuando una ventana activa corre como Administrador.
- **Protección de Portapapeles con Verificación de Secuestro:** Restauración diferida a los 80 ms que se aborta automáticamente si herramientas como Ditto o Windows Clipboard History alteran el búfer durante la ventana de inyección.
