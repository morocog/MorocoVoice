"""Visual settings modal window for MorocoVoice.

Spotify-inspired dark theme UI with a wide 2-column layout (zero unnecessary scroll),
modern keycap chips, interactive shortcut recorder, dark ttk selectors, direct synchronization to config.json,
and crash-proof in-dock status notifications.
"""

from __future__ import annotations

import ctypes
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
COLOR_CARD_BORDER = "#282828"   # Subtle card outline
COLOR_INPUT_BG = "#222222"      # Input fields and selectors
COLOR_INPUT_BORDER = "#333333"  # Subtle input outline
COLOR_INPUT_FOCUS = "#1DB954"   # Active input border (Spotify green)
COLOR_SPOTIFY = "#1DB954"       # Primary brand green
COLOR_SPOTIFY_HOVER = "#1ED760" # Hover green
COLOR_SPOTIFY_ACTIVE = "#169C46"# Pressed green
COLOR_TEXT_WHITE = "#FFFFFF"    # Crisp primary text
COLOR_TEXT_MUTED = "#B3B3B3"    # Subtitles and descriptions
COLOR_TEXT_HINT = "#727272"     # Captions and placeholders
COLOR_DANGER = "#F15E6C"        # Error state
COLOR_GOLD = "#FECA66"          # Telat accent
COLOR_CHIP_BG = "#282828"       # Keycap chip background
COLOR_CHIP_BORDER = "#3A3A3A"   # Keycap chip border

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


def _bind_hover(
    widget: tk.Widget,
    normal_bg: str,
    hover_bg: str,
    normal_fg: str | None = None,
    hover_fg: str | None = None,
) -> None:
    """Attach subtle hover transitions to buttons and pills."""
    def on_enter(_: tk.Event) -> None:
        try:
            widget.configure(bg=hover_bg)
            if hover_fg:
                widget.configure(fg=hover_fg)
        except Exception:
            pass

    def on_leave(_: tk.Event) -> None:
        try:
            widget.configure(bg=normal_bg)
            if normal_fg:
                widget.configure(fg=normal_fg)
        except Exception:
            pass

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


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


def _apply_dark_title_bar(window: tk.Toplevel) -> None:
    """Enable immersive dark mode for the native Windows title bar."""
    try:
        window.update_idletasks()
        hwnd_id = window.winfo_id()
        hwnd = ctypes.windll.user32.GetAncestor(hwnd_id, 2)  # GA_ROOT = 2
        if hwnd:
            value = ctypes.c_int(1)
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Win 11 / Win 10 20H1+), 19 (older Win 10)
            res = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
            if res != 0:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
    except Exception as exc:
        logger.debug("Could not apply dark title bar: %s", exc)


class SettingsModal:
    """Spotify-styled dark modal for MorocoVoice settings with spacious 2-column layout."""

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

        # Keycap preview frames
        self.keycaps_dictation_frame: tk.Frame | None = None
        self.keycaps_rewrite_frame: tk.Frame | None = None

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
            self._refresh_all_keycaps()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("MorocoVoice - Configuración")
        # Spacious wide layout: 1140x740 for 2-column view with zero scrolling
        self.window.geometry("1140x740")
        self.window.minsize(1020, 680)
        self.window.resizable(True, True)
        self.window.configure(bg=COLOR_CANVAS)

        self.window.attributes("-topmost", True)
        self.window.focus_force()
        self.window.bind("<Escape>", lambda e: self._on_cancel())

        self._center_window()
        _apply_dark_title_bar(self.window)
        ico_path = (self.config_path.parent / "morocovoice.ico").resolve()
        if ico_path.exists():
            try:
                self.window.iconbitmap(str(ico_path))
            except Exception:
                pass
        self._setup_ttk_styles()
        self._build_ui()
        self._refresh_all_keycaps()

    def _apply_dark_title_bar(self) -> None:
        """Alias for module level dark title bar applicator."""
        if self.window:
            _apply_dark_title_bar(self.window)

    def _setup_ttk_styles(self) -> None:
        """Apply dark Spotify styling to ttk widgets using clam theme."""
        try:
            style = ttk.Style()
            if "clam" in style.theme_names():
                style.theme_use("clam")

            # Configure Dark.TCombobox
            style.configure(
                "Dark.TCombobox",
                fieldbackground=COLOR_INPUT_BG,
                background=COLOR_PANEL_HOVER,
                foreground=COLOR_TEXT_WHITE,
                darkcolor=COLOR_INPUT_BORDER,
                lightcolor=COLOR_INPUT_BORDER,
                bordercolor=COLOR_INPUT_BORDER,
                arrowcolor=COLOR_SPOTIFY,
                arrowsize=13,
                padding=6,
                relief="flat",
            )
            style.map(
                "Dark.TCombobox",
                fieldbackground=[("readonly", COLOR_INPUT_BG), ("focus", COLOR_INPUT_BG)],
                foreground=[("readonly", COLOR_TEXT_WHITE)],
                bordercolor=[("focus", COLOR_SPOTIFY)],
                lightcolor=[("focus", COLOR_SPOTIFY)],
                darkcolor=[("focus", COLOR_SPOTIFY)],
                arrowcolor=[("active", COLOR_SPOTIFY_HOVER), ("focus", COLOR_SPOTIFY)],
            )

            # Dropdown popup listbox dark theme options
            self.window.option_add("*TCombobox*Listbox.background", "#1A1A1A")
            self.window.option_add("*TCombobox*Listbox.foreground", COLOR_TEXT_WHITE)
            self.window.option_add("*TCombobox*Listbox.selectBackground", COLOR_SPOTIFY)
            self.window.option_add("*TCombobox*Listbox.selectForeground", "#000000")
            self.window.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))
            self.window.option_add("*TCombobox*Listbox.relief", "flat")
            self.window.option_add("*TCombobox*Listbox.borderWidth", "0")
        except Exception as e:
            logger.debug("TTK styling setup note: %s", e)

    def _center_window(self) -> None:
        """Center the modal on the current display monitor."""
        self.window.update_idletasks()
        w = 1140
        h = 740
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.window.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        """Build the Spotify-style dark 2-column interface."""
        # 1. Top Header Banner
        header = tk.Frame(self.window, bg=COLOR_PANEL, height=68)
        header.pack(fill=tk.X, side=tk.TOP)

        brand_frame = tk.Frame(header, bg=COLOR_PANEL)
        brand_frame.pack(side=tk.LEFT, padx=24, pady=12)

        icon_badge = tk.Frame(brand_frame, bg="#242424", padx=8, pady=6, highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)
        icon_badge.pack(side=tk.LEFT, padx=(0, 14))

        icon_dot = tk.Label(
            icon_badge,
            text="🎙️",
            font=("Segoe UI", 14),
            bg="#242424",
            fg=COLOR_SPOTIFY,
        )
        icon_dot.pack()

        title_box = tk.Frame(brand_frame, bg=COLOR_PANEL)
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text="MorocoVoice",
            font=("Segoe UI", 13, "bold"),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Centro de Control de Dictado y Modelos IA",
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
            padx=12,
            pady=4,
            highlightthickness=1,
            highlightbackground=COLOR_CARD_BORDER,
        )
        version_pill.pack(side=tk.RIGHT, padx=24, pady=16)

        # Header separator
        tk.Frame(self.window, bg=COLOR_CARD_BORDER, height=1).pack(fill=tk.X, side=tk.TOP)

        # 2. Spotify Pill Navigation Bar
        nav_bar = tk.Frame(self.window, bg=COLOR_CANVAS, height=44)
        nav_bar.pack(fill=tk.X, padx=24, pady=(14, 10))

        self.btn_tab_general = tk.Button(
            nav_bar,
            text="⚙️ General y Atajos",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=7,
            command=lambda: self._switch_tab("general"),
        )
        self.btn_tab_general.pack(side=tk.LEFT, padx=(0, 10))
        _bind_hover(self.btn_tab_general, COLOR_SPOTIFY, COLOR_SPOTIFY_HOVER)

        self.btn_tab_vocab = tk.Button(
            nav_bar,
            text="📖 Vocabulario Personalizado",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=7,
            command=lambda: self._switch_tab("vocab"),
        )
        self.btn_tab_vocab.pack(side=tk.LEFT)
        _bind_hover(self.btn_tab_vocab, COLOR_PANEL, COLOR_PANEL_HOVER, COLOR_TEXT_MUTED, COLOR_TEXT_WHITE)

        # 3. Bottom Dock Action Bar
        sep_bottom = tk.Frame(self.window, bg=COLOR_CARD_BORDER, height=1)
        sep_bottom.pack(fill=tk.X, side=tk.BOTTOM)

        dock = tk.Frame(self.window, bg=COLOR_PANEL, height=64)
        dock.pack(fill=tk.X, side=tk.BOTTOM)

        btn_open_json = tk.Button(
            dock,
            text="📄 Editar config.json",
            font=("Segoe UI", 9),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_MUTED,
            activebackground=COLOR_PANEL_HOVER,
            activeforeground=COLOR_TEXT_WHITE,
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=7,
            command=self._on_open_json,
        )
        btn_open_json.pack(side=tk.LEFT, padx=24, pady=14)
        _bind_hover(btn_open_json, COLOR_INPUT_BG, COLOR_PANEL_HOVER, COLOR_TEXT_MUTED, COLOR_TEXT_WHITE)

        # In-dock persistent status / toast label (Crash-proof, zero DOM re-packing)
        self.toast_lbl = tk.Label(
            dock,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_PANEL,
            fg=COLOR_SPOTIFY,
            anchor="w",
        )
        self.toast_lbl.pack(side=tk.LEFT, padx=16, fill=tk.X, expand=True)

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
            padx=18,
            pady=7,
            command=self._on_cancel,
        )
        btn_cancel.pack(side=tk.RIGHT, padx=(8, 24), pady=14)
        _bind_hover(btn_cancel, COLOR_INPUT_BG, COLOR_PANEL_HOVER, COLOR_TEXT_WHITE, COLOR_TEXT_WHITE)

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
            padx=22,
            pady=7,
            command=self._on_save,
        )
        btn_save.pack(side=tk.RIGHT, padx=8, pady=14)
        _bind_hover(btn_save, COLOR_SPOTIFY, COLOR_SPOTIFY_HOVER, "#000000", "#000000")

        # 4. Central Content Container
        content_container = tk.Frame(self.window, bg=COLOR_CANVAS)
        content_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 10))

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
        """Build general settings with a 2-column grid layout for zero-scroll comfort."""
        parent.grid_columnconfigure(0, weight=1, uniform="group1")
        parent.grid_columnconfigure(1, weight=1, uniform="group1")
        parent.grid_rowconfigure(0, weight=1)

        # Left Column: Atajos de Teclado + Comportamiento
        col_left = tk.Frame(parent, bg=COLOR_CANVAS)
        col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Right Column: Motor y Modelos de Inferencia
        col_right = tk.Frame(parent, bg=COLOR_CANVAS)
        col_right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # === CARD 1 (LEFT): ATAJOS DE TECLADO (CORE ONLY: 2 KEYS) ===
        card_shortcuts = self._create_card(
            col_left, "⌨️ Atajos de Teclado", "Solo 2 atajos oficiales: hablar y corregir selección."
        )
        self.keycaps_dictation_frame = self._create_hotkey_row(
            card_shortcuts,
            label="Dictado Inteligente:",
            var=self.var_dictation,
            help_text="Habla y transcribe texto en cualquier app activa (default: win+space)",
        )
        self.keycaps_rewrite_frame = self._create_hotkey_row(
            card_shortcuts,
            label="Reescritura Contextual:",
            var=self.var_rewrite,
            help_text="Pule y mejora la selección de texto con IA (default: ctrl+shift+space)",
        )

        # === CARD 2 (LEFT): COMPORTAMIENTO Y PORTAPAPELES ===
        card_behavior = self._create_card(
            col_left, "⚡ Comportamiento y Portapapeles", "Parámetros de corte de audio y retardo de pegado."
        )
        self._create_unit_entry_row(
            card_behavior,
            label="Máx. Grabación:",
            var=self.var_max_sec,
            unit="segundos",
            help_text="Límite máximo por dictado antes de corte automático (default: 60)",
        )
        self._create_unit_entry_row(
            card_behavior,
            label="Retardo Pegado:",
            var=self.var_delay_ms,
            unit="milisegundos",
            help_text="Retardo post-inyección para estabilidad de portapapeles (default: 80)",
        )

        # === CARD 3 (RIGHT): MOTOR Y MODELOS DE INFERENCIA ===
        card_engine = self._create_card(
            col_right, "🧠 Motor y Modelos de Inferencia", "Configura la transcripción por voz y el modelo LLM."
        )

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
            help_text="Idioma base de reconocimiento de voz (es = Español, en = English)",
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
        tk.Label(groq_link_row, text="", bg=COLOR_PANEL, width=18).pack(side=tk.LEFT)
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
        _bind_hover(btn_get_key, COLOR_PANEL, COLOR_PANEL, COLOR_SPOTIFY, COLOR_SPOTIFY_HOVER)

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
            padx=8,
            pady=3,
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
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._restore_recommended_vocabulary,
        )
        btn_restore.pack(side=tk.RIGHT)
        _bind_hover(btn_restore, COLOR_INPUT_BG, COLOR_PANEL_HOVER, COLOR_GOLD, COLOR_TEXT_WHITE)

        # Text editor container
        text_container = tk.Frame(
            card_vocab,
            bg=COLOR_INPUT_BG,
            highlightthickness=1,
            highlightbackground=COLOR_CARD_BORDER,
        )
        text_container.pack(fill=tk.BOTH, expand=True, pady=4)

        scrollbar = tk.Scrollbar(text_container, bg=COLOR_PANEL, troughcolor=COLOR_CANVAS)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.vocab_text = tk.Text(
            text_container,
            font=("Consolas", 10),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_SPOTIFY,
            relief=tk.FLAT,
            padx=12,
            pady=12,
            yscrollcommand=scrollbar.set,
        )
        self.vocab_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.vocab_text.yview)

        self._load_current_vocabulary_into_ui()
        self.vocab_text.bind("<KeyRelease>", lambda e: self._update_vocab_counter())

    def _create_card(self, parent: tk.Frame, title: str, subtitle: str = "") -> tk.Frame:
        """Create an elevated Spotify-style card with subtle border and crisp headers."""
        outer = tk.Frame(
            parent,
            bg=COLOR_PANEL,
            padx=20,
            pady=16,
            highlightthickness=1,
            highlightbackground=COLOR_CARD_BORDER,
        )
        outer.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

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
            ).pack(fill=tk.X, pady=(2, 10))
        else:
            tk.Frame(outer, height=6, bg=COLOR_PANEL).pack()

        return outer

    def _render_keycap_chips(self, container: tk.Frame, hotkey_str: str) -> None:
        """Render stylish pill keycaps for each key in the hotkey combination."""
        for w in container.winfo_children():
            w.destroy()

        tokens = [t.strip().upper() for t in hotkey_str.split("+") if t.strip()]
        if not tokens:
            tk.Label(
                container,
                text="(sin asignar)",
                font=("Segoe UI", 8),
                fg=COLOR_TEXT_HINT,
                bg=COLOR_PANEL,
            ).pack(side=tk.LEFT)
            return

        for i, tok in enumerate(tokens):
            if i > 0:
                tk.Label(
                    container,
                    text="+",
                    font=("Segoe UI", 8, "bold"),
                    fg=COLOR_TEXT_MUTED,
                    bg=COLOR_PANEL,
                ).pack(side=tk.LEFT, padx=3)

            chip = tk.Label(
                container,
                text=tok,
                font=("Segoe UI", 8, "bold"),
                fg=COLOR_TEXT_WHITE,
                bg=COLOR_CHIP_BG,
                padx=7,
                pady=2,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=COLOR_CHIP_BORDER,
            )
            chip.pack(side=tk.LEFT, padx=1)

    def _refresh_all_keycaps(self) -> None:
        """Update both hotkey keycap preview containers."""
        if self.keycaps_dictation_frame:
            self._render_keycap_chips(self.keycaps_dictation_frame, self.var_dictation.get())
        if self.keycaps_rewrite_frame:
            self._render_keycap_chips(self.keycaps_rewrite_frame, self.var_rewrite.get())

    def _create_hotkey_row(
        self, parent: tk.Frame, label: str, var: tk.StringVar, help_text: str = ""
    ) -> tk.Frame:
        """Create an interactive hotkey configuration row with live keycap chips and capture button."""
        row = tk.Frame(parent, bg=COLOR_PANEL)
        row.pack(fill=tk.X, pady=5)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
            width=18,
            anchor="w",
        ).pack(side=tk.LEFT)

        outer_container = tk.Frame(row, bg=COLOR_PANEL)
        outer_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        controls_box = tk.Frame(outer_container, bg=COLOR_PANEL)
        controls_box.pack(fill=tk.X)

        entry = tk.Entry(
            controls_box,
            textvariable=var,
            font=("Segoe UI", 9),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_SPOTIFY,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLOR_INPUT_BORDER,
            highlightcolor=COLOR_INPUT_FOCUS,
            width=16,
        )
        entry.pack(side=tk.LEFT, ipady=4)

        # Chips container
        chips_frame = tk.Frame(controls_box, bg=COLOR_PANEL)
        chips_frame.pack(side=tk.LEFT, padx=8)

        # Initial render of keycaps
        self._render_keycap_chips(chips_frame, var.get())

        # Update keycaps live when user edits entry manually
        entry.bind("<KeyRelease>", lambda e: self._render_keycap_chips(chips_frame, var.get()))

        # Interactive Capture Button
        btn_capture = tk.Button(
            controls_box,
            text="Capturar",
            font=("Segoe UI", 8, "bold"),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_WHITE,
            activebackground=COLOR_PANEL_HOVER,
            activeforeground=COLOR_TEXT_WHITE,
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=2,
        )
        btn_capture.pack(side=tk.RIGHT)
        _bind_hover(btn_capture, COLOR_INPUT_BG, COLOR_PANEL_HOVER, COLOR_TEXT_WHITE, COLOR_TEXT_WHITE)

        def start_capture() -> None:
            btn_capture.configure(
                text="● Presiona teclas...",
                bg=COLOR_GOLD,
                fg="#000000",
            )
            captured_keys: list[str] = []

            def on_key(event: tk.Event) -> str:
                sym = event.keysym.lower()
                if sym == "escape":
                    cleanup()
                    return "break"

                mod_map = {
                    "control_l": "ctrl",
                    "control_r": "ctrl",
                    "shift_l": "shift",
                    "shift_r": "shift",
                    "alt_l": "alt",
                    "alt_r": "alt",
                    "win_l": "win",
                    "win_r": "win",
                    "super_l": "win",
                    "super_r": "win",
                }

                current_mods: list[str] = []
                state = int(event.state)
                # Tkinter event.state bitmask: 0x4 = Control, 0x1 = Shift, 0x20000 / 0x8 = Alt
                if state & 0x4 or sym in ("control_l", "control_r"):
                    if "ctrl" not in current_mods:
                        current_mods.append("ctrl")
                if state & 0x1 or sym in ("shift_l", "shift_r"):
                    if "shift" not in current_mods:
                        current_mods.append("shift")
                if state & 0x8 or state & 0x20000 or sym in ("alt_l", "alt_r"):
                    if "alt" not in current_mods:
                        current_mods.append("alt")

                key_name = mod_map.get(sym, sym)
                if key_name not in ("ctrl", "shift", "alt", "win"):
                    # Non-modifier key was pressed: finalize shortcut!
                    combo_parts = list(current_mods)
                    if key_name not in combo_parts:
                        combo_parts.append(key_name)
                    final_combo = "+".join(combo_parts)
                    var.set(final_combo)
                    self._render_keycap_chips(chips_frame, final_combo)
                    cleanup()
                    return "break"
                return "break"

            def cleanup() -> None:
                try:
                    btn_capture.unbind("<KeyPress>")
                    self.window.unbind("<KeyPress>")
                except Exception:
                    pass
                btn_capture.configure(
                    text="Capturar",
                    bg=COLOR_INPUT_BG,
                    fg=COLOR_TEXT_WHITE,
                )
                self.window.bind("<Escape>", lambda e: self._on_cancel())

            self.window.unbind("<Escape>")
            btn_capture.focus_set()
            btn_capture.bind("<KeyPress>", on_key)
            self.window.bind("<KeyPress>", on_key)

        btn_capture.configure(command=start_capture)

        if help_text:
            tk.Label(
                outer_container,
                text=help_text,
                font=("Segoe UI", 7),
                fg=COLOR_TEXT_HINT,
                bg=COLOR_PANEL,
                anchor="w",
            ).pack(fill=tk.X, pady=(2, 0))

        return chips_frame

    def _create_unit_entry_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, unit: str, help_text: str = ""
    ) -> None:
        """Create a numeric entry row with adjacent unit pill."""
        row = tk.Frame(parent, bg=COLOR_PANEL)
        row.pack(fill=tk.X, pady=5)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
            width=18,
            anchor="w",
        ).pack(side=tk.LEFT)

        outer_container = tk.Frame(row, bg=COLOR_PANEL)
        outer_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        entry_box = tk.Frame(outer_container, bg=COLOR_PANEL)
        entry_box.pack(fill=tk.X)

        entry = tk.Entry(
            entry_box,
            textvariable=var,
            font=("Segoe UI", 9),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_SPOTIFY,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLOR_INPUT_BORDER,
            highlightcolor=COLOR_INPUT_FOCUS,
            width=12,
        )
        entry.pack(side=tk.LEFT, ipady=4)

        unit_pill = tk.Label(
            entry_box,
            text=unit,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_INPUT_BG,
            padx=8,
            pady=3,
            highlightthickness=1,
            highlightbackground=COLOR_CARD_BORDER,
        )
        unit_pill.pack(side=tk.LEFT, padx=8)

        if help_text:
            tk.Label(
                outer_container,
                text=help_text,
                font=("Segoe UI", 7),
                fg=COLOR_TEXT_HINT,
                bg=COLOR_PANEL,
                anchor="w",
            ).pack(fill=tk.X, pady=(2, 0))

    def _create_entry_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, help_text: str = ""
    ) -> None:
        """Create a clean dark text entry row."""
        row = tk.Frame(parent, bg=COLOR_PANEL)
        row.pack(fill=tk.X, pady=5)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
            width=18,
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
        entry.pack(fill=tk.X, expand=True, ipady=4)

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
        row.pack(fill=tk.X, pady=5)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
            width=18,
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
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

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
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_WHITE,
            activebackground=COLOR_PANEL_HOVER,
            activeforeground=COLOR_TEXT_WHITE,
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            command=toggle_mask,
        )
        eye_btn.pack(side=tk.LEFT, padx=(6, 0))
        _bind_hover(eye_btn, COLOR_INPUT_BG, COLOR_PANEL_HOVER, COLOR_TEXT_WHITE, COLOR_TEXT_WHITE)

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
        """Create a Combobox row with Dark.TCombobox styling."""
        row = tk.Frame(parent, bg=COLOR_PANEL)
        row.pack(fill=tk.X, pady=5)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
            width=18,
            anchor="w",
        ).pack(side=tk.LEFT)

        outer_container = tk.Frame(row, bg=COLOR_PANEL)
        outer_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        combo = ttk.Combobox(
            outer_container,
            textvariable=var,
            values=values,
            state="readonly",
            style="Dark.TCombobox",
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
        """Display an inline status notification directly in the bottom dock bar."""
        if not self.toast_lbl:
            return
        fg_col = COLOR_DANGER if is_error else COLOR_SPOTIFY
        self.toast_lbl.configure(text=message, fg=fg_col)
        if self.window and self.window.winfo_exists():
            self.window.after(4000, self._hide_toast)

    def _hide_toast(self) -> None:
        """Clear inline status notification."""
        if self.toast_lbl:
            try:
                self.toast_lbl.configure(text="")
            except Exception:
                pass

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

            # Update ONLY user settings, strictly keeping extra hotkeys empty
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

            # Construct new AppConfig and update modal internal state immediately
            from app.config import load_config
            new_config = load_config(self.config_path)
            self.current_config = new_config

            # Trigger live hot reload on running orchestrator
            self.on_saved(new_config)

            # Spotify-style non-intrusive feedback
            self._show_toast(f"✓ Guardado: Dictado ({dictation_val}) | Reescritura ({rewrite_val})")
            if self.window:
                self.window.after(1100, self._on_cancel)

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            self._show_toast(f"Error al guardar: {e}", is_error=True)
