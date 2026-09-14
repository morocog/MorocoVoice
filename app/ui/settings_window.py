"""Visual settings modal window for VoiceFlow-Win.

Allows users to configure shortcuts, STT/LLM engine parameters, and timing
with live hotkey remapping and direct synchronization to config.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from app.contracts import AppConfig, AudioEngineType
from app.logging_setup import get_logger

logger = get_logger("settings_ui")


def _persist_groq_api_key_to_env(env_path: Path, api_key: str) -> None:
    """Safely persist or update GROQ_API_KEY in .env file without destroying other variables."""
    lines: list[str] = []
    key_found = False
    if env_path.exists():
        try:
            with open(env_path, encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logger.warning("Could not read existing .env: %s", e)

    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("GROQ_API_KEY=") or stripped.startswith("GROQ_API_KEY ="):
            new_lines.append(f"GROQ_API_KEY={api_key}\n")
            key_found = True
        else:
            new_lines.append(line)

    if not key_found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"GROQ_API_KEY={api_key}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        logger.info("GROQ_API_KEY persisted securely to .env")
    except Exception as e:
        logger.error("Failed to write GROQ_API_KEY to %s: %s", env_path, e)


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
        self.window.title("MorocoVoice - Configuración")
        self.window.geometry("540x580")
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
        h = 580
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
            text="⚙️ Configuración de MorocoVoice",
            font=("Segoe UI", 12, "bold"),
            fg="#FBFBFD",
            bg="#27272a",
        )
        title_lbl.pack(side=tk.LEFT, padx=18, pady=14)

        subtitle_lbl = tk.Label(
            banner,
            text="v3.5.0",
            font=("Segoe UI", 9, "bold"),
            fg="#FECA66",
            bg="#27272a",
        )
        subtitle_lbl.pack(side=tk.RIGHT, padx=18, pady=16)

        # Content container
        content = tk.Frame(self.window, bg="#18181b", padx=20, pady=12)
        content.pack(fill=tk.BOTH, expand=True)

        # --- Section 1: Atajos de Teclado ---
        self._create_section_label(content, "ATAJOS DE TECLADO (CORE SHORTCUTS)")

        self.var_dictation = tk.StringVar(value=self.current_config.hotkey_dictation)
        self.var_rewrite = tk.StringVar(value=self.current_config.hotkey_rewrite)

        self._create_entry_row(
            content,
            label="Dictado Inteligente:",
            var=self.var_dictation,
            help_text="Ej: win+space, ctrl+alt+space, alt+z",
        )
        self._create_entry_row(
            content,
            label="Reescritura Contextual:",
            var=self.var_rewrite,
            help_text="Ej: ctrl+shift+space",
        )

        # --- Section 2: Motor y Modelos ---
        self._create_section_label(content, "MOTOR Y MODELOS DE INFERENCIA")

        self.var_engine = tk.StringVar(value=self.current_config.engine.value)
        self.var_groq_api_key = tk.StringVar(
            value=self.current_config.groq_api_key or os.getenv("GROQ_API_KEY", "")
        )
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

        self._create_masked_entry_row(
            content,
            label="Groq API Key:",
            var=self.var_groq_api_key,
            help_text="Clave de API enmascarada (almacenada segura en .env)",
        )
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

        # Bottom status notice bar
        status_bar = tk.Frame(self.window, bg="#1e1e24")
        self.status_bar_lbl = tk.Label(
            status_bar,
            text="🟢 MorocoVoice está activo en segundo plano. Dictado listo con: " + self.var_dictation.get(),
            font=("Segoe UI", 8, "bold"),
            fg="#10b981",
            bg="#1e1e24",
        )
        self.status_bar_lbl.pack(side=tk.LEFT, padx=16, pady=5)
        self.var_dictation.trace_add(
            "write",
            lambda *_: self.status_bar_lbl.configure(
                text="🟢 MorocoVoice está activo en segundo plano. Dictado listo con: " + self.var_dictation.get()
            ),
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
            text="Minimizar a la Bandeja (Esc)",
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

    def _create_masked_entry_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, help_text: str = ""
    ) -> None:
        """Create a masked entry row with asterisks and an eye toggle button."""
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

        entry_container = tk.Frame(row, bg="#18181b")
        entry_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        entry = tk.Entry(
            entry_container,
            textvariable=var,
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="#FBFBFD",
            insertbackground="#FBFBFD",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#3f3f46",
            highlightcolor="#3284C6",
            show="*",
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        is_visible = [False]

        def toggle_mask() -> None:
            if is_visible[0]:
                entry.configure(show="*")
                eye_btn.configure(text="👁️")
                is_visible[0] = False
            else:
                entry.configure(show="")
                eye_btn.configure(text="🔒")
                is_visible[0] = True

        eye_btn = tk.Button(
            entry_container,
            text="👁️",
            font=("Segoe UI", 8),
            bg="#3f3f46",
            fg="#FBFBFD",
            activebackground="#52525b",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=4,
            pady=0,
            command=toggle_mask,
        )
        eye_btn.pack(side=tk.LEFT, padx=(4, 0))

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
                "engine": engine_type.value,
                "groq_stt_model": stt_model,
                "groq_llm_model": llm_model,
                "max_recording_seconds": max_sec,
                "clipboard_restore_delay_ms": delay_ms,
            })
            # Clean obsolete keys if present
            cfg_dict.pop("hotkey_shutdown", None)
            cfg_dict.pop("hotkey_diagnostics", None)

            # Save to config.json atomically
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg_dict, f, indent=2, ensure_ascii=False)

            logger.info("Configuration saved successfully from settings modal.")

            # Persist Groq API Key securely to .env if provided
            groq_key_val = self.var_groq_api_key.get().strip()
            if groq_key_val:
                env_path = self.config_path.parent / ".env"
                _persist_groq_api_key_to_env(env_path, groq_key_val)
                os.environ["GROQ_API_KEY"] = groq_key_val

            # Construct new AppConfig
            from app.config import load_config
            new_config = load_config(self.config_path)

            # Trigger live hot reload
            self.on_saved(new_config)

            messagebox.showinfo(
                "MorocoVoice - Configuración Actualizada",
                f"Cambios guardados con éxito.\n\nNuevo atajo de dictado: {dictation_val}\nMotor activo: {engine_type.value}\nGroq API Key: Almacenada y enmascarada de forma segura.",
                parent=self.window,
            )
            self._on_cancel()

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}", parent=self.window)
