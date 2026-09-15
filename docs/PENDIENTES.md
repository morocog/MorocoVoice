# PENDIENTES — MorocoVoice

> **Historial de Auditorías Independientes:**
> - 📄 **Auditoría Base v1.0.0:** [`docs/MOROCOVOICE_AUDIT_v1.0.0.md`](./MOROCOVOICE_AUDIT_v1.0.0.md) · Calificación inicial: **4.5 / 10**
> - 📄 **Auditoría Verificada v1.0.1:** [`docs/MOROCOVOICE_AUDIT_v1.0.1.md`](./MOROCOVOICE_AUDIT_v1.0.1.md) · Calificación auditada: **7.5 / 10**
> - 📄 **Auditoría Maestra v1.0.2:** [`docs/MOROCOVOICE_AUDIT_v1.0.2.md`](./MOROCOVOICE_AUDIT_v1.0.2.md) · Calificación auditada: **8.4 / 10** (CONDICIONADO)
> - 📄 **Auditoría Final v1.0.3:** [`docs/MOROCOVOICE_AUDIT_v1.0.3.md`](./MOROCOVOICE_AUDIT_v1.0.3.md) · Calificación auditada: **9.3 / 10** — **✅ APROBADO PARA PRODUCCIÓN GENERAL**

---

## 🟢 1. HITOS DE HARDENING Y AUDITORÍA ALCANZADOS (v1.0.3)

> 💡 **Validación Rápida con 1 Clic en Obsidian:** Haz clic directamente sobre la casilla `[x]` para consultar los ítems consolidados en producción.

- [x] **[APROBACIÓN FORMAL PARA PRODUCCIÓN GENERAL]** DeepSeek Harness emitió el veredicto definitivo de aprobación masiva con 9.3/10 ponderado y 9.5/10 en Funcionalidad Core y Seguridad. *(Certificado v1.0.3)*
- [x] **[UNIFICACIÓN DE VERSIONES VISIBLES]** Sincronizada la versión `v1.0.3` de forma homogénea en `tray.py`, `settings_window.py`, `run.bat`, `pyproject.toml`, `README.md` y `verify_install.py`. *(Resuelto v1.0.3)*
- [x] **[FILTRO PII MULTIPATRÓN & PRUEBA REALISTA]** `PIISafeFilter` en `logging_setup.py` detecta prefijos de fuga real (`adjusted text:`, `transcription:`, etc.). En `test_audio.py` se validó empíricamente contra frases confidenciales reales (7/7 fugas redactadas, 0/7 falsos positivos). *(Resuelto v1.0.3)*
- [x] **[TKINTER THREAD-SAFETY EN HUD]** Invocación de `hud.hide()` enrutada mediante `self.root.after(0, self.hud.hide)` al descartar audios sin habla. *(Resuelto v1.0.3)*
- [x] **[GROQ PING NO BLOQUEANTE (`max_retries=0`)]** `verify_groq_api_key_online` configurado con `max_retries=0` (espera máxima de 2.5s). Códigos transitorios (429, 500, 503) tratados como avisos no bloqueantes. *(Resuelto v1.0.3)*
- [x] **[AISLAMIENTO DEL PORTAPAPELES EN PYTEST]** `test_clipboard_roundtrip` respalda y restaura el portapapeles del host. Aserciones reales en lugar de `assert True`. *(Resuelto v1.0.3)*
- [x] **[DECISIONES EXPLÍCITAS DE RICARDO GARCÍA RATIFICADAS]**:
  - `Win + Space` conservado como atajo principal de dictado.
  - Portapapeles (`CF_UNICODETEXT`) conservado con `Ctrl+V` y guardado en historial de Windows (`Win + V`).
  - Documentado con 100% de transparencia en `README.md`.

---

## 🟡 2. BACKLOG FUTURO (v1.1.0 / v1.2.0 — No bloqueante)

### 2A · Limpieza Residual y Cobertura (Cosmética / Baja)
- [ ] **Limpieza de residuo en argparse:** Actualizar descripción en `verify_install.py:148` (visible solo en `--help`).
- [ ] **Limpieza de comentarios en gitignore:** Saneamiento de comentarios obsoletos en `.gitignore:18,21-22`.
- [ ] **Pruebas de cobertura para prefijos PII:** Formalizar pruebas unitarias adicionales para los nuevos prefijos del filtro PII y casos 429/500 en `test_settings.py`.

### 2B · Arquitectura y Rendimiento (Media)
- [ ] **Liberación de memoria en recarga en caliente:** Al guardar ajustes repetidamente en modo LOCAL, liberar explícitamente el modelo CTranslate2 previo para evitar retención transitoria de RAM.
- [ ] **Alineación de contexto Silero V5:** Evaluar paso del tensor `_context` (64 muestras) según la referencia oficial de Silero V5.
- [ ] **Aceleración CUDA Opcional:** Permitir selección de GPU NVIDIA en `LocalWhisperEngine` cuando `ctranslate2` detecte hardware compatible con cuDNN.

### 2C · UX Avanzada
- [ ] **Selector de Dispositivo de Audio en Ajustes:** Permitir elegir el micrófono deseado en lugar del predeterminado de Windows.
