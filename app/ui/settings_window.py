"""Visual settings modal window for MorocoVoice.

Spotify-inspired dark theme UI with fluid layout, pill tabs, custom dark inputs,
direct synchronization to config.json, and zero stale configuration caches.
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

# Spotify-inspired Design System Palette
COLOR_CANVAS = "#121212"        # Base canvas background
COLOR_PANEL = "#181818"         # Elevated card / panel background
COLOR_PANEL_HOVER = "#242424"   # Hover state for cards / pills
COLOR_INPUT_BG = "#242424"      # Input fields and selectors
COLOR_INPUT_BORDER = "#383838"  # Subtle input outline
COLOR_INPUT_FOCUS = "#1DB954"   # Active input border (Spotify green)
COLOR_SPOTIFY = "#1DB954"       # Primary brand green
COLOR_SPOTIFY_HOVER = "#1ED760" # Hover green
COLOR_SPOTIFY_ACTIVE = "#169C46"# Pressed green
COLOR_TEXT_WHITE = "#FFFFFF"    # Crisp primary text
COLOR_TEXT_MUTED = "#B3B3B3"    # Subtitles and descriptions
COLOR_TEXT_HINT = "#727272"     # Captions and placeholders
COLOR_DANGER = "#E91429"        # Error state
COLOR_GOLD = "#FECA66"          # Telat accent

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


def verify_groq_api_key_online(api_key: str, timeout: float = 2.5) -> tuple[bool, str]:
    """Verify Groq API key by attempting to fetch model list with short timeout and no retries."""
    try:
        from groq import Groq
        client = Groq(api_key=api_key, timeout=timeout, max_retries=0)
        client.models.list()
        return True, "Clave válida y autorizada."
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "invalid_api_key" in err_msg.lower() or "unauthorized" in err_msg.lower():
            return False, "La clave de Groq es inválida o fue revocada (Error 401: Unauthorized)."
        elif (
            "connection" in err_msg.lower()
            or "timeout" in err_msg.lower()
            or "429" in err_msg
            or "500" in err_msg
            or "503" in err_msg
        ):
            return True, "No se pudo verificar la conexión con Groq (sin internet, timeout o límite de tasa), pero la clave fue guardada."
        return False, f"Error al verificar la clave de Groq: {e}"


class SettingsModal:
    """Spotify-styled dark modal for MorocoVoice settings."""

    def __init__(
        self,
        parent: tk.Tk,
        current_config: AppConfig,
        config_file_path: str | Path,
        on_saved: Callable[[AppConfig], None],
    ) -> None:
        self.parent = parent
        self.config_path = Path(config_file_path).resolve()
        self.current_config = current_config
        self.vocab_path = (self.config_path.parent / getattr(self.current_config, "custom_vocabulary_path", "custom_vocabulary.json")).resolve()
        self.on_saved = on_saved

        self.window: tk.Toplevel | None = None
        self.vocab_text: tk.Text | None = None
        self.vocab_counter_lbl: tk.Label | None = None
        self.toast_banner: tk.Frame | None = None
        self.toast_lbl: tk.Label | None = None

        # Variables for form controls
        self.var_dictation = tk.StringVar()
        self.var_rewrite = tk.StringVar()
        self.var_engine = tk.StringVar()
        self.var_groq_api_key = tk.StringVar()
        self.var_stt_language = tk.StringVar()
        self.var_stt_model = tk.StringVar()
        self.var_llm_model = tk.StringVar()
        self.var_max_sec = tk.IntVar()
        self.var_delay_ms = tk.IntVar()

        # Tab containers
        self.active_tab = "general"
        self.tab_general_frame: tk.Frame | None = None
        self.tab_vocab_frame: tk.Frame | None = None
        self.btn_tab_general: tk.Button | None = None
        self.btn_tab_vocab: tk.Button | None = None

    def _sync_inputs_from_config(self, cfg: AppConfig) -> None:
        """Populate all Tkinter variables directly from the passed config object."""
        self.var_dictation.set(cfg.hotkey_dictation or "win+space")
        self.var_rewrite.set(cfg.hotkey_rewrite or "ctrl+shift+space")
        self.var_engine.set(cfg.engine.value if hasattr(cfg.engine, "value") else str(cfg.engine))
        self.var_groq_api_key.set(cfg.groq_api_key or os.getenv("GROQ_API_KEY", ""))
        self.var_stt_language.set(getattr(cfg, "stt_language", "es") or "es")
        self.var_stt_model.set(cfg.groq_stt_model or "whisper-large-v3")
        self.var_llm_model.set(cfg.groq_llm_model or "qwen/qwen3.8-27b")
        self.var_max_sec.set(cfg.max_recording_seconds or 60)
        self.var_delay_ms.set(cfg.clipboard_restore_delay_ms or 80)

    def show(self) -> None:
        """Construct and display the settings modal, always reading fresh config from disk."""
        # 1. CRITICAL: Reload fresh config from disk to eliminate stale cache bugs
        from app.config import load_config
        try:
            self.current_config = load_config(self.config_path)
        except Exception as e:
            logger.warning("Could not refresh config on show: %s", e)

        self._sync_inputs_from_config(self.current_config)

        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            self._load_current_vocabulary_into_ui()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("MorocoVoice - Configuración")
        self.window.geometry("680x760")
        self.window.minsize(620, 680)
        self.window.resizable(True, True)
        self.window.configure(bg=COLOR_CANVAS)

        self.window.attributes("-topmost", True)
        self.window.focus_force()
        self.window.bind("<Escape>", lambda e: self._on_cancel())

        self._center_window()
        self._build_ui()

    def _center_window(self) -> None:
        """Center the modal on the current display monitor."""
        self.window.update_idletasks()
        w = 680
        h = 760
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.window.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        """Build the Spotify-style dark interface."""
        # 1. Top Header Banner
        header = tk.Frame(self.window, bg=COLOR_PANEL, height=64)
        header.pack(fill=tk.X, side=tk.TOP)

        brand_frame = tk.Frame(header, bg=COLOR_PANEL)
        brand_frame.pack(side=tk.LEFT, padx=22, pady=12)

        icon_dot = tk.Label(
            brand_frame,
            text="🎙️",
            font=("Segoe UI", 14),
            bg=COLOR_PANEL,
            fg=COLOR_SPOTIFY,
        )
        icon_dot.pack(side=tk.LEFT, padx=(0, 10))

        title_box = tk.Frame(brand_frame, bg=COLOR_PANEL)
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text="MorocoVoice",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Preferencias de Dictado y Modelos IA",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_PANEL,
        ).pack(anchor="w")

        version_pill = tk.Label(
            header,
            text="● v1.0.5",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_SPOTIFY,
            bg=COLOR_PANEL_HOVER,
            padx=10,
            pady=4,
        )
        version_pill.pack(side=tk.RIGHT, padx=22, pady=16)

        # 2. Spotify Pill Navigation Bar
        nav_bar = tk.Frame(self.window, bg=COLOR_CANVAS, height=44)
        nav_bar.pack(fill=tk.X, padx=22, pady=(14, 6))

        self.btn_tab_general = tk.Button(
            nav_bar,
            text="⚙️ General y Atajos",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=6,
            command=lambda: self._switch_tab("general"),
        )
        self.btn_tab_general.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_tab_vocab = tk.Button(
            nav_bar,
            text="📖 Vocabulario Personalizado",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=6,
            command=lambda: self._switch_tab("vocab"),
        )
        self.btn_tab_vocab.pack(side=tk.LEFT)

        # 3. Bottom Dock Action Bar (Packed before notebook to guarantee zero overlap)
        sep_bottom = tk.Frame(self.window, bg="#282828", height=1)
        sep_bottom.pack(fill=tk.X, side=tk.BOTTOM)

        dock = tk.Frame(self.window, bg=COLOR_PANEL, height=64)
        dock.pack(fill=tk.X, side=tk.BOTTOM)

        btn_open_json = tk.Button(
            dock,
            text="📄 Editar config.json",
            font=("Segoe UI", 8),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_MUTED,
            activebackground=COLOR_PANEL_HOVER,
            activeforeground=COLOR_TEXT_WHITE,
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=6,
            command=self._on_open_json,
        )
        btn_open_json.pack(side=tk.LEFT, padx=22, pady=14)

        btn_cancel = tk.Button(
            dock,
            text="Minimizar (Esc)",
            font=("Segoe UI", 9),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_WHITE,
            activebackground=COLOR_PANEL_HOVER,
            activeforeground=COLOR_TEXT_WHITE,
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=6,
            command=self._on_cancel,
        )
        btn_cancel.pack(side=tk.RIGHT, padx=(6, 22), pady=14)

        btn_save = tk.Button(
            dock,
            text="💾 Guardar y Aplicar",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_SPOTIFY,
            fg="#000000",
            activebackground=COLOR_SPOTIFY_HOVER,
            activeforeground="#000000",
            relief=tk.FLAT,
            cursor="hand2",
            padx=18,
            pady=6,
            command=self._on_save,
        )
        btn_save.pack(side=tk.RIGHT, padx=6, pady=14)

        # 4. Inline Toast Banner (Spotify-style notification directly in the modal)
        self.toast_banner = tk.Frame(self.window, bg=COLOR_SPOTIFY, height=36)
        self.toast_lbl = tk.Label(
            self.toast_banner,
            text="✓ Cambios guardados con éxito en config.json",
            font=("Segoe UI", 9, "bold"),
            fg="#000000",
            bg=COLOR_SPOTIFY,
        )
        self.toast_lbl.pack(pady=7)

        # 5. Central Scrollable Content Area
        content_container = tk.Frame(self.window, bg=COLOR_CANVAS)
        content_container.pack(fill=tk.BOTH, expand=True, padx=22, pady=(0, 6))

        # Tab General Frame
        self.tab_general_frame = tk.Frame(content_container, bg=COLOR_CANVAS)
        self._build_general_tab(self.tab_general_frame)

        # Tab Vocab Frame
        self.tab_vocab_frame = tk.Frame(content_container, bg=COLOR_CANVAS)
        self._build_vocab_tab(self.tab_vocab_frame)

        self._switch_tab("general")

    def _switch_tab(self, tab_name: str) -> None:
        """Switch between General and Vocabulary tabs with Spotify-style pill styling."""
        self.active_tab = tab_name
        if tab_name == "general":
            self.tab_vocab_frame.pack_forget()
            self.tab_general_frame.pack(fill=tk.BOTH, expand=True)

            self.btn_tab_general.configure(
                bg=COLOR_SPOTIFY,
                fg="#000000",
                activebackground=COLOR_SPOTIFY_HOVER,
                activeforeground="#000000",
            )
            self.btn_tab_vocab.configure(
                bg=COLOR_PANEL,
                fg=COLOR_TEXT_MUTED,
                activebackground=COLOR_PANEL_HOVER,
                activeforeground=COLOR_TEXT_WHITE,
            )
        else:
            self.tab_general_frame.pack_forget()
            self.tab_vocab_frame.pack(fill=tk.BOTH, expand=True)

            self.btn_tab_general.configure(
                bg=COLOR_PANEL,
                fg=COLOR_TEXT_MUTED,
                activebackground=COLOR_PANEL_HOVER,
                activeforeground=COLOR_TEXT_WHITE,
            )
            self.btn_tab_vocab.configure(
                bg=COLOR_SPOTIFY,
                fg="#000000",
                activebackground=COLOR_SPOTIFY_HOVER,
                activeforeground="#000000",
            )

    def _build_general_tab(self, parent: tk.Frame) -> None:
        """Build general settings with card-based Spotify aesthetics."""
        # Canvas + Scrollbar for vertical flexibility
        canvas = tk.Canvas(parent, bg=COLOR_CANVAS, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLOR_CANVAS)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel support
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # === CARD 1: ATAJOS DE TECLADO (CORE ONLY: STRICTLY 2 KEYS) ===
        card_shortcuts = self._create_card(scrollable_frame, "⌨️ Atajos de Teclado", "Solo 2 atajos oficiales: hablar y corregir selección.")
        self._create_entry_row(
            card_shortcuts,
            label="Dictado Inteligente:",
            var=self.var_dictation,
            help_text="Habla y transcribe texto en cualquier ventana activa (default: win+space)",
        )
        self._create_entry_row(
            card_shortcuts,
            label="Reescritura Contextual:",
            var=self.var_rewrite,
            help_text="Pule y mejora la selección de texto con IA (default: ctrl+shift+space)",
        )

        # === CARD 2: MOTOR Y MODELOS DE INFERENCIA ===
        card_engine = self._create_card(scrollable_frame, "🧠 Motor y Modelos de Inferencia", "Configura la transcripción por voz y el modelo LLM.")
        
        # Engine Combobox
        self._create_combobox_row(
            card_engine,
            label="Motor de Audio:",
            var=self.var_engine,
            values=["CLOUD", "LOCAL"],
            help_text="CLOUD (Groq Whisper ultra-rápido) o LOCAL (offline por CPU)",
        )
        # STT Language Combobox
        self._create_combobox_row(
            card_engine,
            label="Idioma STT:",
            var=self.var_stt_language,
            values=["es", "en"],
            help_text="Idioma base para reconocimiento de voz (es = Español, en = English)",
        )
        # Groq API Key
        self._create_masked_entry_row(
            card_engine,
            label="Groq API Key:",
            var=self.var_groq_api_key,
            help_text="Clave de API enmascarada (guardada de forma segura en .env)",
        )

        # 1-Click Key helper link
        groq_link_row = tk.Frame(card_engine, bg=COLOR_PANEL)
        groq_link_row.pack(fill=tk.X, pady=(2, 6))
        tk.Label(groq_link_row, text="", bg=COLOR_PANEL, width=22).pack(side=tk.LEFT)
        btn_get_key = tk.Button(
            groq_link_row,
            text="🔑 Obtener clave gratuita en console.groq.com (1 clic)",
            font=("Segoe UI", 8, "underline"),
            fg=COLOR_SPOTIFY,
            bg=COLOR_PANEL,
            activeforeground=COLOR_SPOTIFY_HOVER,
            activebackground=COLOR_PANEL,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: webbrowser.open("https://console.groq.com/keys"),
        )
        btn_get_key.pack(side=tk.LEFT)

        # STT Model
        self._create_entry_row(
            card_engine,
            label="Modelo STT Groq:",
            var=self.var_stt_model,
            help_text="whisper-large-v3 o whisper-large-v3-turbo",
        )
        # LLM Model
        self._create_entry_row(
            card_engine,
            label="Modelo LLM Groq:",
            var=self.var_llm_model,
            help_text="qwen/qwen3.8-27b (Recomendado) o openai/gpt-oss-120b",
        )

        # === CARD 3: COMPORTAMIENTO Y PARÁMETROS ===
        card_behavior = self._create_card(scrollable_frame, "⚡ Comportamiento y Portapapeles", "Parámetros de corte de audio y retardo de pegado.")
        self._create_entry_row(
            card_behavior,
            label="Máx. Grabación (seg):",
            var=self.var_max_sec,
            help_text="Límite máximo por dictado antes de corte automático (default: 60)",
        )
        self._create_entry_row(
            card_behavior,
            label="Retardo Pegado (ms):",
            var=self.var_delay_ms,
            help_text="Retardo post-inyección para estabilidad de portapapeles (default: 80)",
        )

    def _build_vocab_tab(self, parent: tk.Frame) -> None:
        """Build custom vocabulary management with Spotify card aesthetics."""
        card_vocab = self._create_card(
            parent,
            "📖 Diccionario de Jerga Técnica y Términos Propios",
            "Hasta 30 palabras o siglas clave (un término por línea) para guiar la fonética de Whisper.",
        )

        counter_bar = tk.Frame(card_vocab, bg=COLOR_PANEL)
        counter_bar.pack(fill=tk.X, pady=(0, 8))

        self.vocab_counter_lbl = tk.Label(
            counter_bar,
            text="0 / 30 términos",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_SPOTIFY,
            bg=COLOR_PANEL,
        )
        self.vocab_counter_lbl.pack(side=tk.LEFT)

        btn_restore = tk.Button(
            counter_bar,
            text="↩ Restaurar recomendados",
            font=("Segoe UI", 8),
            fg=COLOR_GOLD,
            bg=COLOR_INPUT_BG,
            activeforeground=COLOR_TEXT_WHITE,
            activebackground=COLOR_PANEL_HOVER,
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._restore_recommended_vocabulary,
        )
        btn_restore.pack(side=tk.RIGHT)

        # Text editor container
        text_container = tk.Frame(card_vocab, bg=COLOR_INPUT_BG, highlightthickness=1, highlightbackground=COLOR_INPUT_BORDER)
        text_container.pack(fill=tk.BOTH, expand=True, pady=4)

        scrollbar = tk.Scrollbar(text_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.vocab_text = tk.Text(
            text_container,
            font=("Consolas", 10),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_SPOTIFY,
            relief=tk.FLAT,
            padx=10,
            pady=10,
            yscrollcommand=scrollbar.set,
        )
        self.vocab_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.vocab_text.yview)

        self._load_current_vocabulary_into_ui()
        self.vocab_text.bind("<KeyRelease>", lambda e: self._update_vocab_counter())

    def _create_card(self, parent: tk.Frame, title: str, subtitle: str = "") -> tk.Frame:
        """Create a rounded Spotify-style card with header."""
        outer = tk.Frame(
            parent,
            bg=COLOR_PANEL,
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground="#242424",
        )
        outer.pack(fill=tk.X, pady=(0, 14))

        tk.Label(
            outer,
            text=title,
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
            anchor="w",
        ).pack(fill=tk.X)

        if subtitle:
            tk.Label(
                outer,
                text=subtitle,
                font=("Segoe UI", 8),
                fg=COLOR_TEXT_MUTED,
                bg=COLOR_PANEL,
                anchor="w",
            ).pack(fill=tk.X, pady=(1, 10))
        else:
            tk.Frame(outer, height=6, bg=COLOR_PANEL).pack()

        return outer

    def _create_entry_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, help_text: str = ""
    ) -> None:
        """Create an entry row with Spotify dark styling."""
        row = tk.Frame(parent, bg=COLOR_PANEL)
        row.pack(fill=tk.X, pady=4)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
            width=22,
            anchor="w",
        ).pack(side=tk.LEFT)

        outer_container = tk.Frame(row, bg=COLOR_PANEL)
        outer_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        entry = tk.Entry(
            outer_container,
            textvariable=var,
            font=("Segoe UI", 9),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_SPOTIFY,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLOR_INPUT_BORDER,
            highlightcolor=COLOR_INPUT_FOCUS,
        )
        entry.pack(fill=tk.X, expand=True, ipady=3)

        if help_text:
            tk.Label(
                outer_container,
                text=help_text,
                font=("Segoe UI", 7),
                fg=COLOR_TEXT_HINT,
                bg=COLOR_PANEL,
                anchor="w",
            ).pack(fill=tk.X, pady=(2, 0))

    def _create_masked_entry_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, help_text: str = ""
    ) -> None:
        """Create a masked password/API-key entry with toggle eye button."""
        row = tk.Frame(parent, bg=COLOR_PANEL)
        row.pack(fill=tk.X, pady=4)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
            width=22,
            anchor="w",
        ).pack(side=tk.LEFT)

        outer_container = tk.Frame(row, bg=COLOR_PANEL)
        outer_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        entry_container = tk.Frame(outer_container, bg=COLOR_PANEL)
        entry_container.pack(fill=tk.X, expand=True)

        entry = tk.Entry(
            entry_container,
            textvariable=var,
            font=("Segoe UI", 9),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_SPOTIFY,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLOR_INPUT_BORDER,
            highlightcolor=COLOR_INPUT_FOCUS,
            show="*",
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        is_visible = [False]

        def toggle_mask():
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
            bg=COLOR_PANEL_HOVER,
            fg=COLOR_TEXT_WHITE,
            activebackground="#333333",
            activeforeground=COLOR_TEXT_WHITE,
            relief=tk.FLAT,
            padx=6,
            pady=2,
            cursor="hand2",
            command=toggle_mask,
        )
        eye_btn.pack(side=tk.LEFT, padx=(6, 0))

        if help_text:
            tk.Label(
                outer_container,
                text=help_text,
                font=("Segoe UI", 7),
                fg=COLOR_TEXT_HINT,
                bg=COLOR_PANEL,
                anchor="w",
            ).pack(fill=tk.X, pady=(2, 0))

    def _create_combobox_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, values: list[str], help_text: str = ""
    ) -> None:
        """Create a Combobox row with dark styling."""
        row = tk.Frame(parent, bg=COLOR_PANEL)
        row.pack(fill=tk.X, pady=4)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
            width=22,
            anchor="w",
        ).pack(side=tk.LEFT)

        outer_container = tk.Frame(row, bg=COLOR_PANEL)
        outer_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        combo = ttk.Combobox(
            outer_container,
            textvariable=var,
            values=values,
            state="readonly",
        )
        combo.pack(fill=tk.X, expand=True)

        if help_text:
            tk.Label(
                outer_container,
                text=help_text,
                font=("Segoe UI", 7),
                fg=COLOR_TEXT_HINT,
                bg=COLOR_PANEL,
                anchor="w",
            ).pack(fill=tk.X, pady=(2, 0))

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
        """Reset editor content to canonical recommended terms."""
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
            color = COLOR_SPOTIFY
        elif count <= 30:
            color = COLOR_GOLD
        else:
            color = COLOR_DANGER

        self.vocab_counter_lbl.configure(
            text=f"{count} / 30 términos",
            fg=color,
        )

    def _show_toast(self, message: str, is_error: bool = False) -> None:
        """Display an inline Spotify-style toast notification."""
        if not self.toast_banner or not self.toast_lbl:
            return
        bg_col = COLOR_DANGER if is_error else COLOR_SPOTIFY
        fg_col = "#FFFFFF" if is_error else "#000000"
        self.toast_banner.configure(bg=bg_col)
        self.toast_lbl.configure(text=message, bg=bg_col, fg=fg_col)
        self.toast_banner.pack(fill=tk.X, side=tk.BOTTOM, before=self.window.winfo_children()[-2])
        self.window.after(3500, self._hide_toast)

    def _hide_toast(self) -> None:
        """Dismiss inline toast."""
        if self.toast_banner and self.toast_banner.winfo_ismapped():
            self.toast_banner.pack_forget()

    def _on_open_json(self) -> None:
        """Open config.json directly in Notepad for raw inspection."""
        if not self.config_path.exists():
            self._show_toast("No se encontró el archivo config.json", is_error=True)
            return
        try:
            subprocess.Popen(["notepad.exe", str(self.config_path)], close_fds=True)
        except Exception as e:
            logger.error("Failed to open config.json in notepad: %s", e)

    def _on_cancel(self) -> None:
        """Close modal cleanly."""
        if self.window:
            self.window.destroy()
            self.window = None

    def _on_save(self) -> None:
        """Validate, persist to config.json, update current_config, and apply live hot reload."""
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
                self._show_toast("El atajo de dictado no puede estar vacío.", is_error=True)
                return

            if not rewrite_val:
                self._show_toast("El atajo de reescritura no puede estar vacío.", is_error=True)
                return

            engine_type = AudioEngineType.CLOUD if engine_str == "CLOUD" else AudioEngineType.LOCAL

            # Groq API Key validation for CLOUD mode
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
            elif engine_type == AudioEngineType.CLOUD and not is_placeholder:
                is_valid, auth_msg = verify_groq_api_key_online(groq_key_val, timeout=2.5)
                if not is_valid:
                    warn_msg = (
                        f"La clave de Groq no superó la verificación en línea:\n\n"
                        f"{auth_msg}\n\n"
                        "¿Deseas guardarla de todas formas (por ejemplo si estás sin conexión)?"
                    )
                    if not messagebox.askyesno("Verificación de Groq", warn_msg, parent=self.window):
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

            # Load existing config dictionary
            cfg_dict = {}
            if self.config_path.exists():
                try:
                    with open(self.config_path, encoding="utf-8") as f:
                        cfg_dict = json.load(f)
                except Exception:
                    pass

            # Update ONLY user settings, keeping extra hotkeys empty/clean
            cfg_dict.update({
                "hotkey_dictation": dictation_val,
                "hotkey_rewrite": rewrite_val,
                "hotkey_settings": "",
                "hotkey_diagnostics": "",
                "engine": engine_type.value,
                "stt_language": stt_lang,
                "groq_stt_model": stt_model,
                "groq_llm_model": llm_model,
                "max_recording_seconds": max_sec,
                "clipboard_restore_delay_ms": delay_ms,
            })

            # Save config.json
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg_dict, f, indent=2, ensure_ascii=False)

            logger.info("Configuration saved successfully from settings modal.")

            # Persist Groq API Key securely to .env if provided and real
            if groq_key_val and not is_placeholder:
                env_path = self.config_path.parent / ".env"
                _persist_groq_api_key_to_env(env_path, groq_key_val)
                os.environ["GROQ_API_KEY"] = groq_key_val

            # CRITICAL: Construct new AppConfig and update modal internal state immediately!
            from app.config import load_config
            new_config = load_config(self.config_path)
            self.current_config = new_config

            # Trigger live hot reload on running orchestrator
            self.on_saved(new_config)

            # Spotify-style non-intrusive feedback
            self._show_toast(f"✓ Guardado: Dictado ({dictation_val}) | Reescritura ({rewrite_val})")
            self.window.after(1400, self._on_cancel)

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            self._show_toast(f"Error al guardar: {e}", is_error=True)
