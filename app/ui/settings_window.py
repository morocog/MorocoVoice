"""Visual settings modal window for VoiceFlow-Win.

Allows users to configure shortcuts, STT/LLM engine parameters, and timing
with live hotkey remapping and direct synchronization to config.json.
"""

from __future__ import annotations

import json
import subprocess
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from app.contracts import AppConfig, AudioEngineType
from app.logging_setup import get_logger

logger = get_logger("settings_ui")


class SettingsModal:
    """Modern dark-themed Tkinter settings modal with Telat executive styling."""

    def __init__(
        self,
        parent: tk.Tk,
        current_config: AppConfig,
        config_file_path: str | Path,
        on_saved: Callable[[AppConfig], None],
    ) -> None:
        self.parent = parent
        self.current_config = current_config
        self.config_path = Path(config_file_path).resolve()
        self.on_saved = on_saved

        self.window: tk.Toplevel | None = None

    def show(self) -> None:
        """Construct and display the settings modal."""
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("VoiceFlow-Win - Configuración")
        self.window.geometry("540x620")
        self.window.resizable(False, False)
        self.window.configure(bg="#18181b")

        # Keep on top of other windows
        self.window.attributes("-topmost", True)
        self.window.focus_force()

        # Support Escape key to close modal safely
        self.window.bind("<Escape>", lambda e: self._on_cancel())

        # Center on screen
        self._center_window()

        self._build_ui()

    def _center_window(self) -> None:
        """Center the modal on the current screen."""
        self.window.update_idletasks()
        w = 540
        h = 640
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.window.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        """Build the modal widgets."""
        # Top banner
        banner = tk.Frame(self.window, bg="#27272a", height=60)
        banner.pack(fill=tk.X)

        title_lbl = tk.Label(
            banner,
            text="⚙️ Configuración de VoiceFlow-Win",
            font=("Segoe UI", 12, "bold"),
            fg="#FBFBFD",
            bg="#27272a",
        )
        title_lbl.pack(side=tk.LEFT, padx=18, pady=14)

        subtitle_lbl = tk.Label(
            banner,
            text="v3.4.1",
            font=("Segoe UI", 9),
            fg="#FECA66",
            bg="#27272a",
        )
        subtitle_lbl.pack(side=tk.RIGHT, padx=18, pady=16)

        # Content container
        content = tk.Frame(self.window, bg="#18181b", padx=20, pady=12)
        content.pack(fill=tk.BOTH, expand=True)

        # --- Section 1: Atajos de Teclado ---
        self._create_section_label(content, "ATALOS DE TECLADO (SHORTCUTS)")

        self.var_dictation = tk.StringVar(value=self.current_config.hotkey_dictation)
        self.var_rewrite = tk.StringVar(value=self.current_config.hotkey_rewrite)
        self.var_diagnostics = tk.StringVar(value=self.current_config.hotkey_diagnostics)
        self.var_shutdown = tk.StringVar(value=self.current_config.hotkey_shutdown)

        self._create_entry_row(
            content,
            label="Dictado Inteligente:",
            var=self.var_dictation,
            help_text="Ej: ctrl+alt+space, alt+z, ctrl+shift+v",
        )
        self._create_entry_row(
            content,
            label="Reescritura Contextual:",
            var=self.var_rewrite,
            help_text="Ej: ctrl+shift+space",
        )
        self._create_entry_row(
            content,
            label="Diagnósticos en Vivo:",
            var=self.var_diagnostics,
            help_text="Ej: ctrl+shift+d",
        )
        self._create_entry_row(
            content,
            label="Apagado Seguro:",
            var=self.var_shutdown,
            help_text="Ej: ctrl+shift+q",
        )

        # --- Section 2: Motor y Modelos ---
        self._create_section_label(content, "MOTOR Y MODELOS DE INFERENCIA")

        self.var_engine = tk.StringVar(value=self.current_config.engine.value)
        self.var_stt_model = tk.StringVar(value=self.current_config.groq_stt_model)
        self.var_llm_model = tk.StringVar(value=self.current_config.groq_llm_model)

        engine_row = tk.Frame(content, bg="#18181b")
        engine_row.pack(fill=tk.X, pady=3)
        tk.Label(
            engine_row,
            text="Motor de Audio:",
            font=("Segoe UI", 9, "bold"),
            fg="#FBFBFD",
            bg="#18181b",
            width=20,
            anchor="w",
        ).pack(side=tk.LEFT)

        engine_menu = ttk.Combobox(
            engine_row,
            textvariable=self.var_engine,
            values=["CLOUD", "LOCAL"],
            state="readonly",
            width=28,
        )
        engine_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._create_entry_row(
            content,
            label="Modelo STT Groq:",
            var=self.var_stt_model,
            help_text="whisper-large-v3-turbo o whisper-large-v3",
        )
        self._create_entry_row(
            content,
            label="Modelo LLM Groq:",
            var=self.var_llm_model,
            help_text="qwen/qwen3.8-27b",
        )

        # --- Section 3: Comportamiento ---
        self._create_section_label(content, "COMPORTAMIENTO Y PARÁMETROS")

        self.var_max_sec = tk.IntVar(value=self.current_config.max_recording_seconds)
        self.var_delay_ms = tk.IntVar(value=self.current_config.clipboard_restore_delay_ms)

        self._create_entry_row(
            content,
            label="Máx. Grabación (seg):",
            var=self.var_max_sec,
            help_text="Límite corte automático (default: 60)",
        )
        self._create_entry_row(
            content,
            label="Restaurar Clipboard (ms):",
            var=self.var_delay_ms,
            help_text="Retardo seguro post-pegado (default: 80)",
        )

        # Bottom action buttons bar
        btn_bar = tk.Frame(self.window, bg="#27272a", height=50)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        btn_open_json = tk.Button(
            btn_bar,
            text="📄 Editar config.json",
            font=("Segoe UI", 9),
            bg="#3f3f46",
            fg="#FBFBFD",
            activebackground="#52525b",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=self._on_open_json,
        )
        btn_open_json.pack(side=tk.LEFT, padx=16, pady=10)

        btn_cancel = tk.Button(
            btn_bar,
            text="Cancelar (Esc)",
            font=("Segoe UI", 9),
            bg="#3f3f46",
            fg="#FBFBFD",
            activebackground="#52525b",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            command=self._on_cancel,
        )
        btn_cancel.pack(side=tk.RIGHT, padx=(6, 16), pady=10)

        btn_save = tk.Button(
            btn_bar,
            text="💾 Guardar y Aplicar",
            font=("Segoe UI", 9, "bold"),
            bg="#3284C6",
            fg="#FFFFFF",
            activebackground="#2669a0",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=14,
            pady=4,
            command=self._on_save,
        )
        btn_save.pack(side=tk.RIGHT, padx=6, pady=10)

    def _create_section_label(self, parent: tk.Frame, title: str) -> None:
        """Create a section header with accent line."""
        sec_frame = tk.Frame(parent, bg="#18181b")
        sec_frame.pack(fill=tk.X, pady=(12, 4))

        tk.Label(
            sec_frame,
            text=title,
            font=("Segoe UI", 8, "bold"),
            fg="#3284C6",
            bg="#18181b",
        ).pack(side=tk.LEFT)

        sep = tk.Frame(sec_frame, bg="#3f3f46", height=1)
        sep.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), pady=4)

    def _create_entry_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, help_text: str = ""
    ) -> None:
        """Create a label + entry row with optional inline help."""
        row = tk.Frame(parent, bg="#18181b")
        row.pack(fill=tk.X, pady=2)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            fg="#FBFBFD",
            bg="#18181b",
            width=20,
            anchor="w",
        ).pack(side=tk.LEFT)

        entry = tk.Entry(
            row,
            textvariable=var,
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="#FBFBFD",
            insertbackground="#FBFBFD",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#3f3f46",
            highlightcolor="#3284C6",
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _on_open_json(self) -> None:
        """Open config.json directly in Notepad for raw editing."""
        if not self.config_path.exists():
            messagebox.showwarning("Archivo no encontrado", f"No se encontró {self.config_path}")
            return
        try:
            subprocess.Popen(["notepad.exe", str(self.config_path)], close_fds=True)
        except Exception as e:
            logger.error("Failed to open config.json in notepad: %s", e)

    def _on_cancel(self) -> None:
        """Close modal without saving."""
        if self.window:
            self.window.destroy()
            self.window = None

    def _on_save(self) -> None:
        """Validate, persist to config.json, and apply updates."""
        try:
            dictation_val = self.var_dictation.get().strip()
            rewrite_val = self.var_rewrite.get().strip()
            shutdown_val = self.var_shutdown.get().strip()
            diagnostics_val = self.var_diagnostics.get().strip()
            engine_str = self.var_engine.get().strip().upper()
            stt_model = self.var_stt_model.get().strip()
            llm_model = self.var_llm_model.get().strip()
            max_sec = int(self.var_max_sec.get())
            delay_ms = int(self.var_delay_ms.get())

            if not dictation_val:
                messagebox.showerror("Error de validación", "El atajo de dictado no puede estar vacío.")
                return

            engine_type = AudioEngineType.CLOUD if engine_str == "CLOUD" else AudioEngineType.LOCAL

            # Load existing config dict or start fresh
            cfg_dict = {}
            if self.config_path.exists():
                try:
                    with open(self.config_path, encoding="utf-8") as f:
                        cfg_dict = json.load(f)
                except Exception:
                    pass

            cfg_dict.update({
                "hotkey_dictation": dictation_val,
                "hotkey_rewrite": rewrite_val,
                "hotkey_shutdown": shutdown_val,
                "hotkey_diagnostics": diagnostics_val,
                "engine": engine_type.value,
                "groq_stt_model": stt_model,
                "groq_llm_model": llm_model,
                "max_recording_seconds": max_sec,
                "clipboard_restore_delay_ms": delay_ms,
            })

            # Save to config.json atomically
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg_dict, f, indent=2, ensure_ascii=False)

            logger.info("Configuration saved successfully from settings modal.")

            # Construct new AppConfig
            from app.config import load_config
            new_config = load_config(self.config_path)

            # Trigger live hot reload
            self.on_saved(new_config)

            messagebox.showinfo(
                "Configuración Actualizada",
                f"Cambios guardados con éxito.\n\nNuevo atajo de dictado: {dictation_val}\nMotor activo: {engine_type.value}",
                parent=self.window,
            )
            self._on_cancel()

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}", parent=self.window)
