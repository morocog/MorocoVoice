"""Visual settings modal window for MorocoVoice.

Allows users to configure shortcuts, STT/LLM engine parameters, custom technical vocabulary,
and timing with live hotkey remapping and direct synchronization to config.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from app.contracts import AppConfig, AudioEngineType
from app.logging_setup import get_logger

logger = get_logger("settings_ui")

RECOMMENDED_VOCABULARY: list[str] = [
    "GitHub",
    "Whisper",
    "WFM",
    "Workforce Management",
    "Antigravity",
    "DeepSeek",
    "Google Apps Script",
    "Dashboard",
    "Omnicanal",
    "NICE",
    "IEX",
    "Verint",
    "DevOps",
    "PostgreSQL",
    "Python",
    "Win32",
    "API",
    "Webhook",
    "KPI",
    "SLA",
    "CSAT",
    "FCR",
    "AHT",
    "Shrinkage",
    "Adherence",
    "Forecasting",
    "Scheduling",
    "Groq",
    "MorocoVoice",
    "Backend",
]


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
    """Modern dark-themed Tkinter settings modal with Telat executive styling and tabs."""

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
        self.vocab_path = (self.config_path.parent / getattr(self.current_config, "custom_vocabulary_path", "custom_vocabulary.json")).resolve()
        self.on_saved = on_saved

        self.window: tk.Toplevel | None = None
        self.vocab_text: tk.Text | None = None
        self.vocab_counter_lbl: tk.Label | None = None

    def show(self) -> None:
        """Construct and display the settings modal."""
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("MorocoVoice - Configuración")
        self.window.geometry("580x640")
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
        w = 580
        h = 640
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.window.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        """Build the tabbed modal interface."""
        # Top banner
        banner = tk.Frame(self.window, bg="#27272a", height=56)
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
            text="v1.0.1",
            font=("Segoe UI", 9, "bold"),
            fg="#FECA66",
            bg="#27272a",
        )
        subtitle_lbl.pack(side=tk.RIGHT, padx=18, pady=16)

        # Style notebook
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background="#18181b", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#27272a",
            foreground="#FBFBFD",
            padding=[14, 6],
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#3284C6"), ("active", "#3f3f46")],
            foreground=[("selected", "#FFFFFF"), ("active", "#FFFFFF")],
        )

        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=14, pady=(8, 0))

        tab_general = tk.Frame(notebook, bg="#18181b", padx=16, pady=10)
        tab_vocab = tk.Frame(notebook, bg="#18181b", padx=16, pady=10)

        notebook.add(tab_general, text="⚙️ General y Modelos")
        notebook.add(tab_vocab, text="📖 Vocabulario Personalizado")

        self._build_general_tab(tab_general)
        self._build_vocab_tab(tab_vocab)

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

    def _build_general_tab(self, parent: tk.Frame) -> None:
        """Build general settings tab content."""
        # --- Section 1: Atajos de Teclado ---
        self._create_section_label(parent, "ATAJOS DE TECLADO (CORE SHORTCUTS)")

        self.var_dictation = tk.StringVar(value=self.current_config.hotkey_dictation)
        self.var_rewrite = tk.StringVar(value=self.current_config.hotkey_rewrite)

        self._create_entry_row(
            parent,
            label="Dictado Inteligente:",
            var=self.var_dictation,
            help_text="Atajo global para hablar (default: win+space)",
        )
        self._create_entry_row(
            parent,
            label="Reescritura Contextual:",
            var=self.var_rewrite,
            help_text="Atajo para pulir selección activa (default: ctrl+shift+space)",
        )

        # --- Section 2: Motor y Modelos ---
        self._create_section_label(parent, "MOTOR Y MODELOS DE INFERENCIA")

        self.var_engine = tk.StringVar(value=self.current_config.engine.value)
        self.var_groq_api_key = tk.StringVar(
            value=self.current_config.groq_api_key or os.getenv("GROQ_API_KEY", "")
        )
        self.var_stt_language = tk.StringVar(
            value=getattr(self.current_config, "stt_language", "es")
        )
        self.var_stt_model = tk.StringVar(value=self.current_config.groq_stt_model)
        self.var_llm_model = tk.StringVar(value=self.current_config.groq_llm_model)

        # Engine selector row
        engine_row = tk.Frame(parent, bg="#18181b")
        engine_row.pack(fill=tk.X, pady=2)
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

        # Language selector row
        lang_row = tk.Frame(parent, bg="#18181b")
        lang_row.pack(fill=tk.X, pady=2)
        tk.Label(
            lang_row,
            text="Idioma STT:",
            font=("Segoe UI", 9),
            fg="#FBFBFD",
            bg="#18181b",
            width=20,
            anchor="w",
        ).pack(side=tk.LEFT)

        lang_menu = ttk.Combobox(
            lang_row,
            textvariable=self.var_stt_language,
            values=["es", "en"],
            state="readonly",
            width=28,
        )
        lang_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._create_masked_entry_row(
            parent,
            label="Groq API Key:",
            var=self.var_groq_api_key,
            help_text="Clave de API enmascarada (almacenada segura en .env)",
        )

        # 1-Click direct browser helper
        groq_link_row = tk.Frame(parent, bg="#18181b")
        groq_link_row.pack(fill=tk.X, pady=(0, 3))
        tk.Label(groq_link_row, text="", bg="#18181b", width=20).pack(side=tk.LEFT)
        btn_get_key = tk.Button(
            groq_link_row,
            text="🔑 Obtener clave gratuita en console.groq.com (1 clic)",
            font=("Segoe UI", 8, "underline"),
            fg="#3284C6",
            bg="#18181b",
            activeforeground="#FECA66",
            activebackground="#18181b",
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: webbrowser.open("https://console.groq.com/keys"),
        )
        btn_get_key.pack(side=tk.LEFT)

        self._create_entry_row(
            parent,
            label="Modelo STT Groq:",
            var=self.var_stt_model,
            help_text="whisper-large-v3-turbo o whisper-large-v3",
        )
        self._create_entry_row(
            parent,
            label="Modelo LLM Groq:",
            var=self.var_llm_model,
            help_text="llama-3.1-8b-instant",
        )

        # --- Section 3: Comportamiento ---
        self._create_section_label(parent, "COMPORTAMIENTO Y PARÁMETROS")

        self.var_max_sec = tk.IntVar(value=self.current_config.max_recording_seconds)
        self.var_delay_ms = tk.IntVar(value=self.current_config.clipboard_restore_delay_ms)

        self._create_entry_row(
            parent,
            label="Máx. Grabación (seg):",
            var=self.var_max_sec,
            help_text="Límite de corte automático (default: 60)",
        )
        self._create_entry_row(
            parent,
            label="Restaurar Clipboard (ms):",
            var=self.var_delay_ms,
            help_text="Retardo seguro post-pegado (default: 80)",
        )

    def _build_vocab_tab(self, parent: tk.Frame) -> None:
        """Build custom vocabulary management tab content."""
        self._create_section_label(parent, "DICCIONARIO DE PALABRAS Y JERGA TÉCNICA")

        desc_lbl = tk.Label(
            parent,
            text=(
                "Ingresa hasta 30 palabras técnicas, nombres propios o siglas (un término por línea).\n"
                "Whisper y el corrector determinista de MorocoVoice priorizarán estos términos para\n"
                "evitar errores fonéticos (ejemplo: 'GitHub' en lugar de 'GITCOP')."
            ),
            font=("Segoe UI", 8),
            fg="#a1a1aa",
            bg="#18181b",
            justify=tk.LEFT,
            anchor="w",
        )
        desc_lbl.pack(fill=tk.X, pady=(0, 6))

        # Counter and restore bar
        counter_bar = tk.Frame(parent, bg="#18181b")
        counter_bar.pack(fill=tk.X, pady=(0, 4))

        self.vocab_counter_lbl = tk.Label(
            counter_bar,
            text="0 / 30 términos",
            font=("Segoe UI", 9, "bold"),
            fg="#10b981",
            bg="#18181b",
        )
        self.vocab_counter_lbl.pack(side=tk.LEFT)

        btn_restore_vocab = tk.Button(
            counter_bar,
            text="↩ Restaurar recomendados",
            font=("Segoe UI", 8),
            fg="#FECA66",
            bg="#27272a",
            activeforeground="#FFFFFF",
            activebackground="#3f3f46",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._restore_recommended_vocabulary,
        )
        btn_restore_vocab.pack(side=tk.RIGHT)

        # Text editor container with scrollbar
        text_container = tk.Frame(parent, bg="#27272a", highlightthickness=1, highlightbackground="#3f3f46")
        text_container.pack(fill=tk.BOTH, expand=True, pady=4)

        scrollbar = tk.Scrollbar(text_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.vocab_text = tk.Text(
            text_container,
            font=("Consolas", 10),
            bg="#1e1e24",
            fg="#FBFBFD",
            insertbackground="#FBFBFD",
            relief=tk.FLAT,
            padx=8,
            pady=8,
            yscrollcommand=scrollbar.set,
        )
        self.vocab_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.vocab_text.yview)

        # Load existing vocabulary terms
        self._load_current_vocabulary_into_ui()
        self.vocab_text.bind("<KeyRelease>", lambda e: self._update_vocab_counter())

    def _load_current_vocabulary_into_ui(self) -> None:
        """Read custom_vocabulary.json and populate editor."""
        if not self.vocab_text:
            return
        terms: list[str] = []
        if self.vocab_path.exists():
            try:
                with open(self.vocab_path, encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, list):
                        terms = [str(t).strip() for t in loaded if str(t).strip()]
            except Exception as e:
                logger.warning("Could not load vocabulary file: %s", e)

        if not terms:
            terms = RECOMMENDED_VOCABULARY

        self.vocab_text.delete("1.0", tk.END)
        self.vocab_text.insert(tk.END, "\n".join(terms))
        self._update_vocab_counter()

    def _restore_recommended_vocabulary(self) -> None:
        """Reset editor content to the canonical recommended terms."""
        if not self.vocab_text:
            return
        self.vocab_text.delete("1.0", tk.END)
        self.vocab_text.insert(tk.END, "\n".join(RECOMMENDED_VOCABULARY))
        self._update_vocab_counter()

    def _get_current_terms_from_ui(self) -> list[str]:
        """Parse non-empty lines from the vocabulary text area."""
        if not self.vocab_text:
            return []
        raw = self.vocab_text.get("1.0", tk.END)
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def _update_vocab_counter(self) -> None:
        """Update live terms counter and color coding."""
        if not self.vocab_counter_lbl:
            return
        terms = self._get_current_terms_from_ui()
        count = len(terms)
        if count <= 25:
            color = "#10b981"  # Emerald
        elif count <= 30:
            color = "#FECA66"  # Amber warning
        else:
            color = "#ef4444"  # Red limit exceeded

        self.vocab_counter_lbl.configure(
            text=f"{count} / 30 términos",
            fg=color,
        )

    def _create_section_label(self, parent: tk.Frame, title: str) -> None:
        """Create a section header with accent line."""
        sec_frame = tk.Frame(parent, bg="#18181b")
        sec_frame.pack(fill=tk.X, pady=(10, 3))

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
        """Create a label + entry row with rendered inline help text."""
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
        )
        entry.pack(fill=tk.X, expand=True)

        if help_text:
            help_lbl = tk.Label(
                entry_container,
                text=help_text,
                font=("Segoe UI", 7),
                fg="#71717a",
                bg="#18181b",
                anchor="w",
            )
            help_lbl.pack(fill=tk.X, pady=(1, 0))

    def _create_masked_entry_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, help_text: str = ""
    ) -> None:
        """Create a masked entry row with asterisks, eye toggle button and help text."""
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

        outer_container = tk.Frame(row, bg="#18181b")
        outer_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        entry_container = tk.Frame(outer_container, bg="#18181b")
        entry_container.pack(fill=tk.X, expand=True)

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

        if help_text:
            help_lbl = tk.Label(
                outer_container,
                text=help_text,
                font=("Segoe UI", 7),
                fg="#71717a",
                bg="#18181b",
                anchor="w",
            )
            help_lbl.pack(fill=tk.X, pady=(1, 0))

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
        """Validate, persist to config.json and custom_vocabulary.json, and apply updates."""
        try:
            dictation_val = self.var_dictation.get().strip()
            rewrite_val = self.var_rewrite.get().strip()
            engine_str = self.var_engine.get().strip().upper()
            stt_lang = self.var_stt_language.get().strip() or "es"
            stt_model = self.var_stt_model.get().strip()
            llm_model = self.var_llm_model.get().strip()
            max_sec = int(self.var_max_sec.get())
            delay_ms = int(self.var_delay_ms.get())

            if not dictation_val:
                messagebox.showerror("Error de validación", "El atajo de dictado no puede estar vacío.", parent=self.window)
                return

            engine_type = AudioEngineType.CLOUD if engine_str == "CLOUD" else AudioEngineType.LOCAL

            # Detect placeholder or empty key for CLOUD engine
            groq_key_val = self.var_groq_api_key.get().strip()
            is_placeholder = (
                not groq_key_val
                or "tu_clave" in groq_key_val.lower()
                or "placeholder" in groq_key_val.lower()
                or len(groq_key_val) < 20
            )

            if engine_type == AudioEngineType.CLOUD and is_placeholder:
                msg = (
                    "Has seleccionado el motor CLOUD pero no has ingresado una clave real de Groq.\n\n"
                    "• Haz clic en '🔑 Obtener clave gratuita...' para generar una en 1 clic.\n"
                    "• O cambia el Motor de Audio a 'LOCAL' para dictar sin internet.\n\n"
                    "¿Deseas cambiar automáticamente el motor a LOCAL para continuar?"
                )
                if messagebox.askyesno("Clave de Groq requerida", msg, parent=self.window):
                    engine_type = AudioEngineType.LOCAL
                    self.var_engine.set("LOCAL")
                else:
                    return

            # Validate vocabulary terms
            terms = self._get_current_terms_from_ui()
            if len(terms) > 30:
                msg = (
                    f"Has configurado {len(terms)} términos en el vocabulario.\n\n"
                    "Para proteger la precisión y el Word Error Rate (WER) de Whisper, el límite "
                    "estricto es de 30 términos.\n\n"
                    "¿Deseas guardar únicamente los primeros 30 términos y descartar los sobrantes?"
                )
                if not messagebox.askyesno("Límite de Vocabulario Excedido", msg, parent=self.window):
                    return
                terms = terms[:30]

            # Save custom_vocabulary.json
            try:
                with open(self.vocab_path, "w", encoding="utf-8") as f:
                    json.dump(terms, f, indent=2, ensure_ascii=False)
                logger.info("Custom vocabulary saved with %d terms to %s", len(terms), self.vocab_path)
            except Exception as e:
                logger.error("Failed to save vocabulary: %s", e)

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
                "stt_language": stt_lang,
                "groq_stt_model": stt_model,
                "groq_llm_model": llm_model,
                "max_recording_seconds": max_sec,
                "clipboard_restore_delay_ms": delay_ms,
            })
            cfg_dict.pop("hotkey_shutdown", None)
            cfg_dict.pop("hotkey_diagnostics", None)

            # Save to config.json atomically
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg_dict, f, indent=2, ensure_ascii=False)

            logger.info("Configuration saved successfully from settings modal.")

            # Persist Groq API Key securely to .env if provided and real
            if groq_key_val and not is_placeholder:
                env_path = self.config_path.parent / ".env"
                _persist_groq_api_key_to_env(env_path, groq_key_val)
                os.environ["GROQ_API_KEY"] = groq_key_val

            # Construct new AppConfig
            from app.config import load_config
            new_config = load_config(self.config_path)

            # Trigger live hot reload
            self.on_saved(new_config)

            key_status = "Almacenada de forma segura." if not is_placeholder else "No configurada (usando LOCAL)."
            messagebox.showinfo(
                "MorocoVoice - Configuración Actualizada",
                f"Cambios guardados con éxito.\n\n"
                f"• Atajo de dictado: {dictation_val}\n"
                f"• Motor activo: {engine_type.value}\n"
                f"• Idioma STT: {stt_lang}\n"
                f"• Vocabulario activo: {len(terms)} términos\n"
                f"• Groq API Key: {key_status}",
                parent=self.window,
            )
            self._on_cancel()

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}", parent=self.window)
