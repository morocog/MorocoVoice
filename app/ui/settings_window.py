"""Visual settings modal window for MorocoVoice.

Spotify-inspired dark theme UI with a wide 2-column layout (zero unnecessary scroll),
interactive keycap chips with spacious non-clipping controls, Canvas-drawn pill buttons,
dark ttk selectors, direct synchronization to config.json, and crash-proof in-dock notifications.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from app import __version__
from app.config import (
    is_valid_groq_api_key,
    load_config,
    persist_groq_api_key_to_env,
    verify_groq_api_key_online,
)
from app.contracts import AppConfig, AudioEngineType
from app.engine.engine_manager import MAX_VOCABULARY_TERMS, load_raw_vocabulary_terms
from app.logging_setup import get_logger

logger = get_logger("settings_ui")

# Backward-compatible alias for unit tests importing _persist_groq_api_key_to_env
_persist_groq_api_key_to_env = persist_groq_api_key_to_env

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
COLOR_TEXT_WHITE = "#FFFFFF"    # Crisp primary text
COLOR_TEXT_MUTED = "#B3B3B3"    # Subtitles and descriptions
COLOR_TEXT_HINT = "#727272"     # Captions and placeholders
COLOR_DANGER = "#F15E6C"        # Error state
COLOR_GOLD = "#FECA66"          # Telat accent
COLOR_CHIP_BG = "#282828"       # Keycap chip background
COLOR_CHIP_BORDER = "#3E3E3E"   # Keycap chip border

# Win32 Virtual-Key codes for Left/Right Windows keys
VK_LWIN = 0x5B
VK_RWIN = 0x5C

MODIFIER_KEYSYM_MAP: dict[str, str] = {
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

KEYSYM_NORMALIZATION_MAP: dict[str, str] = {
    "return": "enter",
    "prior": "page up",
    "next": "page down",
    "back_space": "backspace",
}

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


def _is_win_key_hardware_pressed() -> bool:
    """Query Win32 GetAsyncKeyState to detect held Left/Right Windows keys."""
    try:
        lwin = ctypes.windll.user32.GetAsyncKeyState(VK_LWIN) & 0x8000
        rwin = ctypes.windll.user32.GetAsyncKeyState(VK_RWIN) & 0x8000
        return bool(lwin or rwin)
    except Exception:
        return False


def resolve_captured_hotkey_event(
    event: tk.Event, held_mods: set[str] | None = None
) -> str | None:
    """Resolve a Tkinter KeyPress event into a normalized shortcut string.

    Returns:
        - `"CANCEL"` if Escape was pressed.
        - `None` if only a modifier key was pressed (waiting for main key).
        - Normalized shortcut string (e.g. `"win+space"`, `"ctrl+shift+space"`) when complete.
    """
    sym = (getattr(event, "keysym", "") or "").lower()
    if not sym:
        return None
    if sym == "escape":
        return "CANCEL"

    if sym in MODIFIER_KEYSYM_MAP:
        if held_mods is not None:
            held_mods.add(MODIFIER_KEYSYM_MAP[sym])
        return None

    state = int(getattr(event, "state", 0) or 0)
    active_mods: set[str] = set(held_mods) if held_mods else set()

    # Tkinter event.state bitmask: 0x4 = Control, 0x1 = Shift, 0x20000 / 0x8 = Alt
    if state & 0x4:
        active_mods.add("ctrl")
    if state & 0x1:
        active_mods.add("shift")
    if (state & 0x8) or (state & 0x20000):
        active_mods.add("alt")
    if _is_win_key_hardware_pressed():
        active_mods.add("win")

    ordered_mods = [m for m in ("ctrl", "alt", "shift", "win") if m in active_mods]
    key_name = KEYSYM_NORMALIZATION_MAP.get(sym, sym)
    combo_parts = ordered_mods + ([key_name] if key_name not in ordered_mods else [])
    return "+".join(combo_parts)


class PillButton(tk.Canvas):
    """Authentic Spotify-styled pill button drawn natively on Canvas with smooth hover and keyboard support."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None] | None = None,
        bg_color: str = COLOR_SPOTIFY,
        fg_color: str = "#000000",
        hover_bg: str = COLOR_SPOTIFY_HOVER,
        hover_fg: str = "#000000",
        border_color: str | None = None,
        font: tuple = ("Segoe UI", 9, "bold"),
        padx: int = 22,
        pady: int = 7,
        canvas_bg: str = COLOR_PANEL,
        **kwargs,
    ) -> None:
        self.parent_widget = parent
        self.text_str = text
        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_bg = hover_bg
        self.hover_fg = hover_fg
        self.border_color = border_color
        self.fnt = font
        self.padx = padx
        self.pady = pady
        self.canvas_bg = canvas_bg
        self._has_focus = False

        text_w, text_h = self._measure_text(text)
        self.w = max(40, text_w + padx * 2)
        self.h = max(24, text_h + pady * 2)

        super().__init__(
            parent,
            width=self.w,
            height=self.h,
            bg=canvas_bg,
            highlightthickness=0,
            takefocus=1,
            cursor="hand2",
            **kwargs,
        )

        self.draw(self.bg_color, self.fg_color)
        self.bind("<Enter>", lambda e: self.draw(self.hover_bg, self.hover_fg))
        self.bind("<Leave>", lambda e: self.draw(self.bg_color, self.fg_color))
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Button-1>", self._on_button_press)
        self.bind("<ButtonRelease-1>", self._on_button_release)
        self.bind("<Return>", lambda e: self._on_click())
        self.bind("<space>", lambda e: self._on_click())

    def _measure_text(self, text: str) -> tuple[int, int]:
        """Measure text width and line height using DPI-aware font metrics."""
        fnt_family = self.fnt[0]
        fnt_size = self.fnt[1]
        fnt_weight = self.fnt[2] if len(self.fnt) > 2 else "normal"
        try:
            tk_fnt = tkfont.Font(
                root=self.parent_widget,
                family=fnt_family,
                size=fnt_size,
                weight=fnt_weight,
            )
            return int(tk_fnt.measure(text)), int(tk_fnt.metrics("linespace"))
        except Exception:
            return len(text) * 8, 16

    def _on_focus_in(self, _: tk.Event) -> None:
        self._has_focus = True
        self.draw(self.bg_color, self.fg_color)

    def _on_focus_out(self, _: tk.Event) -> None:
        self._has_focus = False
        self.draw(self.bg_color, self.fg_color)

    def _on_button_press(self, _: tk.Event) -> None:
        try:
            self.focus_set()
        except Exception:
            pass

    def _on_button_release(self, event: tk.Event) -> None:
        x = getattr(event, "x", 0)
        y = getattr(event, "y", 0)
        if 0 <= x <= self.w and 0 <= y <= self.h:
            self._on_click()

    def draw(self, bg_col: str, fg_col: str) -> None:
        """Render rounded pill capsule geometry and centered label."""
        self.delete("all")
        r = self.h // 2
        w, h = self.w, self.h
        active_border = COLOR_TEXT_WHITE if self._has_focus else self.border_color
        if active_border:
            # Outer border pill
            self.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=180, fill=active_border, outline="")
            self.create_arc(w - 2 * r, 0, w, 2 * r, start=270, extent=180, fill=active_border, outline="")
            self.create_rectangle(r, 0, w - r, h, fill=active_border, outline="")
            # Inner body pill
            self.create_arc(1, 1, 2 * r - 1, 2 * r - 1, start=90, extent=180, fill=bg_col, outline="")
            self.create_arc(w - 2 * r + 1, 1, w - 1, 2 * r - 1, start=270, extent=180, fill=bg_col, outline="")
            self.create_rectangle(r, 1, w - r, h - 1, fill=bg_col, outline="")
        else:
            self.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=180, fill=bg_col, outline="")
            self.create_arc(w - 2 * r, 0, w, 2 * r, start=270, extent=180, fill=bg_col, outline="")
            self.create_rectangle(r, 0, w - r, h, fill=bg_col, outline="")
        self.create_text(w // 2, h // 2, text=self.text_str, fill=fg_col, font=self.fnt)

    def set_text(
        self,
        text: str,
        bg_color: str | None = None,
        fg_color: str | None = None,
        hover_bg: str | None = None,
        hover_fg: str | None = None,
    ) -> None:
        """Update button text and recalculate capsule width smoothly."""
        self.text_str = text
        if bg_color:
            self.bg_color = bg_color
        if fg_color:
            self.fg_color = fg_color
        if hover_bg:
            self.hover_bg = hover_bg
        if hover_fg:
            self.hover_fg = hover_fg

        text_w, text_h = self._measure_text(text)
        self.w = max(40, text_w + self.padx * 2)
        self.h = max(24, text_h + self.pady * 2)
        self.configure(width=self.w, height=self.h)
        self.draw(self.bg_color, self.fg_color)

    def set_colors(
        self,
        bg_color: str,
        fg_color: str,
        hover_bg: str | None = None,
        hover_fg: str | None = None,
        border_color: str | None = "__keep__",
    ) -> None:
        """Change normal, hover, and border color states dynamically."""
        self.bg_color = bg_color
        self.fg_color = fg_color
        if hover_bg:
            self.hover_bg = hover_bg
        if hover_fg:
            self.hover_fg = hover_fg
        if border_color != "__keep__":
            self.border_color = border_color
        self.draw(self.bg_color, self.fg_color)

    def cget(self, key: str):
        """Allow introspection for tests."""
        if key == "text":
            return self.text_str
        return super().cget(key)

    def _on_click(self) -> None:
        if callable(self.command):
            self.command()


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


def _apply_dark_title_bar(window: tk.Toplevel) -> None:
    """Enable immersive dark mode for the native Windows title bar."""
    try:
        window.update_idletasks()
        hwnd_id = window.winfo_id()
        hwnd = ctypes.windll.user32.GetAncestor(hwnd_id, 2)  # GA_ROOT = 2
        if hwnd:
            value = ctypes.c_int(1)
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Win 11 / Win 10 20H1+), 19 (older Win 10)
            res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
            )
            if res != 0:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 19, ctypes.byref(value), ctypes.sizeof(value)
                )
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
        self.vocab_path = (
            self.config_path.parent
            / getattr(self.current_config, "custom_vocabulary_path", "custom_vocabulary.json")
        ).resolve()
        self.on_saved = on_saved

        self.window: tk.Toplevel | None = None
        self.vocab_text: tk.Text | None = None
        self.vocab_counter_lbl: tk.Label | None = None
        self.toast_lbl: tk.Label | None = None
        self._toast_timer_id: str | None = None
        self._close_timer_id: str | None = None
        self._active_capture_cleanup: Callable[[], None] | None = None
        self._had_valid_key_on_open: bool = False

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
        self.btn_tab_general: PillButton | None = None
        self.btn_tab_vocab: PillButton | None = None

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
        """Construct and display the settings modal, preserving unsaved edits if already open."""
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        try:
            self.current_config = load_config(self.config_path)
        except Exception as e:
            logger.warning("Could not refresh config on show: %s", e)

        self._had_valid_key_on_open = is_valid_groq_api_key(self.current_config.groq_api_key)
        self._sync_inputs_from_config(self.current_config)

        self.window = tk.Toplevel(self.parent)
        self.window.title("MorocoVoice - Configuración")
        # Spacious wide layout: 1140x740 for 2-column view with zero scrolling
        self.window.geometry("1140x740")
        self.window.minsize(1020, 680)
        self.window.resizable(True, True)
        self.window.configure(bg=COLOR_CANVAS)

        # Pulse -topmost briefly so the modal surfaces in front of all apps, then release
        # so external windows (browser for Groq console, Notepad for config.json) are not hidden behind it
        self.window.attributes("-topmost", True)
        self.window.focus_force()
        self.window.after(
            250,
            lambda: self.window is not None
            and self.window.winfo_exists()
            and self.window.attributes("-topmost", False),
        )
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

            # Configure Dark.Vertical.TScrollbar
            style.configure(
                "Dark.Vertical.TScrollbar",
                troughcolor=COLOR_CANVAS,
                background=COLOR_PANEL_HOVER,
                darkcolor=COLOR_PANEL,
                lightcolor=COLOR_PANEL,
                bordercolor=COLOR_CARD_BORDER,
                arrowcolor=COLOR_TEXT_MUTED,
                relief="flat",
            )
            style.map(
                "Dark.Vertical.TScrollbar",
                background=[("active", COLOR_SPOTIFY), ("pressed", COLOR_SPOTIFY_HOVER)],
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
        """Build the Spotify-style dark 2-column interface with rounded pill buttons."""
        # 1. Top Header Banner
        header = tk.Frame(self.window, bg=COLOR_PANEL, height=68)
        header.pack(fill=tk.X, side=tk.TOP)

        brand_frame = tk.Frame(header, bg=COLOR_PANEL)
        brand_frame.pack(side=tk.LEFT, padx=24, pady=12)

        icon_badge = tk.Frame(
            brand_frame,
            bg="#242424",
            padx=8,
            pady=6,
            highlightthickness=1,
            highlightbackground=COLOR_CARD_BORDER,
        )
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
            text="Centro de control de dictado y modelos de IA",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_PANEL,
        ).pack(anchor="w")

        version_pill = tk.Label(
            header,
            text=f"● v{__version__}",
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

        self.btn_tab_general = PillButton(
            nav_bar,
            text="⚙️ General y atajos",
            font=("Segoe UI", 9, "bold"),
            bg_color=COLOR_SPOTIFY,
            fg_color="#000000",
            hover_bg=COLOR_SPOTIFY_HOVER,
            hover_fg="#000000",
            padx=20,
            pady=6,
            canvas_bg=COLOR_CANVAS,
            command=lambda: self._switch_tab("general"),
        )
        self.btn_tab_general.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_tab_vocab = PillButton(
            nav_bar,
            text="📖 Vocabulario personalizado",
            font=("Segoe UI", 9, "bold"),
            bg_color=COLOR_PANEL,
            fg_color=COLOR_TEXT_MUTED,
            hover_bg=COLOR_PANEL_HOVER,
            hover_fg=COLOR_TEXT_WHITE,
            border_color=COLOR_CARD_BORDER,
            padx=20,
            pady=6,
            canvas_bg=COLOR_CANVAS,
            command=lambda: self._switch_tab("vocab"),
        )
        self.btn_tab_vocab.pack(side=tk.LEFT)

        # 3. Bottom Dock Action Bar
        sep_bottom = tk.Frame(self.window, bg=COLOR_CARD_BORDER, height=1)
        sep_bottom.pack(fill=tk.X, side=tk.BOTTOM)

        dock = tk.Frame(self.window, bg=COLOR_PANEL, height=64)
        dock.pack(fill=tk.X, side=tk.BOTTOM)

        btn_open_json = PillButton(
            dock,
            text="📄 Editar config.json",
            font=("Segoe UI", 9),
            bg_color=COLOR_INPUT_BG,
            fg_color=COLOR_TEXT_MUTED,
            hover_bg=COLOR_PANEL_HOVER,
            hover_fg=COLOR_TEXT_WHITE,
            border_color=COLOR_CARD_BORDER,
            padx=16,
            pady=7,
            canvas_bg=COLOR_PANEL,
            command=self._on_open_json,
        )
        btn_open_json.pack(side=tk.LEFT, padx=24, pady=14)

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

        btn_cancel = PillButton(
            dock,
            text="Cerrar sin guardar (Esc)",
            font=("Segoe UI", 9),
            bg_color=COLOR_INPUT_BG,
            fg_color=COLOR_TEXT_WHITE,
            hover_bg=COLOR_PANEL_HOVER,
            hover_fg=COLOR_TEXT_WHITE,
            border_color=COLOR_CARD_BORDER,
            padx=18,
            pady=7,
            canvas_bg=COLOR_PANEL,
            command=self._on_cancel,
        )
        btn_cancel.pack(side=tk.RIGHT, padx=(8, 24), pady=14)

        btn_save = PillButton(
            dock,
            text="💾 Guardar y aplicar",
            font=("Segoe UI", 9, "bold"),
            bg_color=COLOR_SPOTIFY,
            fg_color="#000000",
            hover_bg=COLOR_SPOTIFY_HOVER,
            hover_fg="#000000",
            padx=24,
            pady=7,
            canvas_bg=COLOR_PANEL,
            command=self._on_save,
        )
        btn_save.pack(side=tk.RIGHT, padx=8, pady=14)

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

    def _cancel_active_capture(self) -> None:
        """Cancel any in-progress hotkey capture session."""
        if self._active_capture_cleanup is not None:
            cleanup_fn = self._active_capture_cleanup
            self._active_capture_cleanup = None
            try:
                cleanup_fn()
            except Exception:
                pass

    def _switch_tab(self, tab_name: str) -> None:
        """Switch between General and Vocabulary tabs with smooth Spotify pill transitions."""
        self._cancel_active_capture()
        self.active_tab = tab_name
        if tab_name == "general":
            self.tab_vocab_frame.pack_forget()
            self.tab_general_frame.pack(fill=tk.BOTH, expand=True)

            self.btn_tab_general.set_colors(
                bg_color=COLOR_SPOTIFY,
                fg_color="#000000",
                hover_bg=COLOR_SPOTIFY_HOVER,
                hover_fg="#000000",
                border_color=None,
            )
            self.btn_tab_vocab.set_colors(
                bg_color=COLOR_PANEL,
                fg_color=COLOR_TEXT_MUTED,
                hover_bg=COLOR_PANEL_HOVER,
                hover_fg=COLOR_TEXT_WHITE,
                border_color=COLOR_CARD_BORDER,
            )
        else:
            self.tab_general_frame.pack_forget()
            self.tab_vocab_frame.pack(fill=tk.BOTH, expand=True)

            self.btn_tab_general.set_colors(
                bg_color=COLOR_PANEL,
                fg_color=COLOR_TEXT_MUTED,
                hover_bg=COLOR_PANEL_HOVER,
                hover_fg=COLOR_TEXT_WHITE,
                border_color=COLOR_CARD_BORDER,
            )
            self.btn_tab_vocab.set_colors(
                bg_color=COLOR_SPOTIFY,
                fg_color="#000000",
                hover_bg=COLOR_SPOTIFY_HOVER,
                hover_fg="#000000",
                border_color=None,
            )

    def _build_general_tab(self, parent: tk.Frame) -> None:
        """Build general settings with a 2-column grid layout for zero-scroll comfort."""
        parent.grid_columnconfigure(0, weight=1, uniform="group1")
        parent.grid_columnconfigure(1, weight=1, uniform="group1")
        parent.grid_rowconfigure(0, weight=1)

        # Left Column: Atajos de teclado + Comportamiento
        col_left = tk.Frame(parent, bg=COLOR_CANVAS)
        col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Right Column: Motor y modelos de inferencia
        col_right = tk.Frame(parent, bg=COLOR_CANVAS)
        col_right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # === CARD 1 (LEFT): ATAJOS DE TECLADO (CORE ONLY: 2 KEYS) ===
        card_shortcuts = self._create_card(
            col_left,
            "⌨️ Atajos de teclado",
            "Solo 2 atajos oficiales: hablar para dictar y corregir texto seleccionado.",
        )
        self.keycaps_dictation_frame = self._create_hotkey_row(
            card_shortcuts,
            label="Dictado inteligente",
            var=self.var_dictation,
            help_text="Habla y escribe en cualquier ventana activa (por omisión: win+space)",
        )
        self.keycaps_rewrite_frame = self._create_hotkey_row(
            card_shortcuts,
            label="Reescritura contextual",
            var=self.var_rewrite,
            help_text="Pule y mejora el texto seleccionado con IA (por omisión: ctrl+shift+space)",
        )

        # === CARD 2 (LEFT): COMPORTAMIENTO DE GRABACIÓN ===
        card_behavior = self._create_card(
            col_left,
            "⚡ Comportamiento de grabación",
            "El texto dictado también permanece disponible en tu portapapeles (Ctrl+V).",
        )
        self._create_unit_entry_row(
            card_behavior,
            label="Duración máxima:",
            var=self.var_max_sec,
            unit="segundos",
            help_text="Tiempo máximo por dictado antes del corte automático (entre 5 y 300 s, por omisión: 60)",
        )

        # === CARD 3 (RIGHT): MOTOR Y MODELOS DE INFERENCIA ===
        card_engine = self._create_card(
            col_right,
            "🧠 Motor y modelos de inferencia",
            "Configura el motor de reconocimiento de voz y el modelo de lenguaje.",
        )

        # Engine Combobox
        self._create_combobox_row(
            card_engine,
            label="Motor de audio:",
            var=self.var_engine,
            values=["CLOUD", "LOCAL"],
            help_text="CLOUD (Groq Whisper en la nube, ultrarrápido) o LOCAL (en tu equipo sin internet)",
        )
        # STT Language Combobox
        self._create_combobox_row(
            card_engine,
            label="Idioma de voz (STT):",
            var=self.var_stt_language,
            values=["es", "en"],
            help_text="Idioma principal al dictar (es = Español, en = Inglés)",
        )
        # Groq API Key
        self._create_masked_entry_row(
            card_engine,
            label="Clave API de Groq:",
            var=self.var_groq_api_key,
            help_text="Tu clave privada de Groq (se guarda de forma segura en el archivo .env)",
        )

        # 1-Click Key helper link
        groq_link_row = tk.Frame(card_engine, bg=COLOR_PANEL)
        groq_link_row.pack(fill=tk.X, pady=(2, 6))
        tk.Label(groq_link_row, text="", bg=COLOR_PANEL, width=26).pack(side=tk.LEFT, padx=(0, 10))
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
            label="Modelo de voz (STT):",
            var=self.var_stt_model,
            help_text="Ejemplos: whisper-large-v3 (máxima precisión) o whisper-large-v3-turbo",
        )
        # LLM Model
        self._create_entry_row(
            card_engine,
            label="Modelo de lenguaje (LLM):",
            var=self.var_llm_model,
            help_text="Ejemplos: qwen/qwen3.8-27b (recomendado) u openai/gpt-oss-120b",
        )

    def _build_vocab_tab(self, parent: tk.Frame) -> None:
        """Build custom vocabulary management with Spotify card aesthetics."""
        card_vocab = self._create_card(
            parent,
            "📖 Diccionario de jerga técnica y términos propios",
            f"Hasta {MAX_VOCABULARY_TERMS} palabras, nombres o siglas (un término por línea) para mejorar el reconocimiento fonético.",
        )

        counter_bar = tk.Frame(card_vocab, bg=COLOR_PANEL)
        counter_bar.pack(fill=tk.X, pady=(0, 8))

        self.vocab_counter_lbl = tk.Label(
            counter_bar,
            text=f"0 / {MAX_VOCABULARY_TERMS} términos",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_SPOTIFY,
            bg=COLOR_PANEL,
            padx=8,
            pady=3,
        )
        self.vocab_counter_lbl.pack(side=tk.LEFT)

        btn_restore = PillButton(
            counter_bar,
            text="↩ Restaurar recomendados",
            font=("Segoe UI", 8, "bold"),
            bg_color=COLOR_INPUT_BG,
            fg_color=COLOR_GOLD,
            hover_bg=COLOR_PANEL_HOVER,
            hover_fg=COLOR_TEXT_WHITE,
            border_color=COLOR_CARD_BORDER,
            padx=14,
            pady=4,
            canvas_bg=COLOR_PANEL,
            command=self._restore_recommended_vocabulary,
        )
        btn_restore.pack(side=tk.RIGHT)

        # Text editor container
        text_container = tk.Frame(
            card_vocab,
            bg=COLOR_INPUT_BG,
            highlightthickness=1,
            highlightbackground=COLOR_CARD_BORDER,
        )
        text_container.pack(fill=tk.BOTH, expand=True, pady=4)

        scrollbar = ttk.Scrollbar(
            text_container,
            orient=tk.VERTICAL,
            style="Dark.Vertical.TScrollbar",
        )
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
                    fg=COLOR_TEXT_HINT,
                    bg=COLOR_PANEL,
                ).pack(side=tk.LEFT, padx=3)

            chip = tk.Label(
                container,
                text=tok,
                font=("Segoe UI", 8, "bold"),
                fg=COLOR_TEXT_WHITE,
                bg=COLOR_CHIP_BG,
                padx=8,
                pady=3,
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
        """Create an interactive hotkey configuration row with spacious Spotify styling and zero clipping."""
        container = tk.Frame(parent, bg=COLOR_PANEL)
        container.pack(fill=tk.X, pady=(4, 14))

        # Title and description row on top
        header_row = tk.Frame(container, bg=COLOR_PANEL)
        header_row.pack(fill=tk.X, anchor="w")

        tk.Label(
            header_row,
            text=label,
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
        ).pack(side=tk.LEFT)

        if help_text:
            desc_lbl = tk.Label(
                container,
                text=help_text,
                font=("Segoe UI", 8),
                fg=COLOR_TEXT_MUTED,
                bg=COLOR_PANEL,
                anchor="w",
                justify=tk.LEFT,
            )
            desc_lbl.pack(fill=tk.X, anchor="w", pady=(2, 0))

            def _update_desc_wraplength(event: tk.Event) -> None:
                avail_w = max(240, event.width - 10)
                desc_lbl.configure(wraplength=avail_w)

            container.bind("<Configure>", _update_desc_wraplength)

        # Controls row: keycaps on the left, manual input & capture button on the right
        controls_row = tk.Frame(container, bg=COLOR_PANEL)
        controls_row.pack(fill=tk.X, pady=(6, 0))

        chips_frame = tk.Frame(controls_row, bg=COLOR_PANEL)
        chips_frame.pack(side=tk.LEFT, anchor="w")

        actions_box = tk.Frame(controls_row, bg=COLOR_PANEL)
        actions_box.pack(side=tk.RIGHT, anchor="e")

        entry = tk.Entry(
            actions_box,
            textvariable=var,
            font=("Segoe UI", 8),
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_SPOTIFY,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLOR_INPUT_BORDER,
            highlightcolor=COLOR_INPUT_FOCUS,
            width=16,
        )
        entry.pack(side=tk.LEFT, padx=(0, 8), ipady=3)

        # Initial render of keycaps
        self._render_keycap_chips(chips_frame, var.get())
        entry.bind("<KeyRelease>", lambda e: self._render_keycap_chips(chips_frame, var.get()))

        # Interactive Capture Pill Button
        btn_capture = PillButton(
            actions_box,
            text="Capturar",
            font=("Segoe UI", 8, "bold"),
            bg_color=COLOR_INPUT_BG,
            fg_color=COLOR_TEXT_WHITE,
            hover_bg=COLOR_PANEL_HOVER,
            hover_fg=COLOR_TEXT_WHITE,
            border_color=COLOR_INPUT_BORDER,
            padx=14,
            pady=4,
            canvas_bg=COLOR_PANEL,
        )
        btn_capture.pack(side=tk.RIGHT)

        def start_capture() -> None:
            if not self.window or not self.window.winfo_exists():
                return
            self._cancel_active_capture()
            btn_capture.set_text(
                "● Presiona teclas...",
                bg_color=COLOR_GOLD,
                fg_color="#000000",
                hover_bg=COLOR_GOLD,
                hover_fg="#000000",
            )
            held_mods: set[str] = set()

            def on_key_release(event: tk.Event) -> str:
                sym = (getattr(event, "keysym", "") or "").lower()
                if sym in MODIFIER_KEYSYM_MAP:
                    held_mods.discard(MODIFIER_KEYSYM_MAP[sym])
                return "break"

            def on_key(event: tk.Event) -> str:
                result = resolve_captured_hotkey_event(event, held_mods)
                if result == "CANCEL":
                    cleanup()
                    return "break"
                if result:
                    var.set(result)
                    self._render_keycap_chips(chips_frame, result)
                    cleanup()
                return "break"

            def cleanup() -> None:
                self._active_capture_cleanup = None
                try:
                    if self.window and self.window.winfo_exists():
                        self.window.unbind("<KeyPress>")
                        self.window.unbind("<KeyRelease>")
                        self.window.bind("<Escape>", lambda e: self._on_cancel())
                except Exception:
                    pass
                try:
                    btn_capture.set_text(
                        "Capturar",
                        bg_color=COLOR_INPUT_BG,
                        fg_color=COLOR_TEXT_WHITE,
                        hover_bg=COLOR_PANEL_HOVER,
                        hover_fg=COLOR_TEXT_WHITE,
                    )
                except Exception:
                    pass

            self._active_capture_cleanup = cleanup
            self.window.unbind("<Escape>")
            self.window.bind("<KeyPress>", on_key)
            self.window.bind("<KeyRelease>", on_key_release)
            self.window.focus_set()

        btn_capture.command = start_capture
        return chips_frame

    def _create_labeled_row(
        self, parent: tk.Frame, label: str, help_text: str = ""
    ) -> tuple[tk.Frame, Callable[[], None]]:
        """Create standardized left label and right control container with crisp, unified vertical alignment."""
        row = tk.Frame(parent, bg=COLOR_PANEL)
        row.pack(fill=tk.X, pady=5)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL,
            width=26,
            anchor="w",
        ).pack(side=tk.LEFT, padx=(0, 10))

        outer_container = tk.Frame(row, bg=COLOR_PANEL)
        outer_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def pack_help() -> None:
            if help_text:
                help_lbl = tk.Label(
                    outer_container,
                    text=help_text,
                    font=("Segoe UI", 7),
                    fg=COLOR_TEXT_HINT,
                    bg=COLOR_PANEL,
                    anchor="w",
                    justify=tk.LEFT,
                )
                help_lbl.pack(fill=tk.X, pady=(2, 0))

                def _update_wraplength(event: tk.Event) -> None:
                    avail_w = max(180, event.width - 4)
                    help_lbl.configure(wraplength=avail_w)

                outer_container.bind("<Configure>", _update_wraplength)

        return outer_container, pack_help

    def _create_unit_entry_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, unit: str, help_text: str = ""
    ) -> None:
        """Create a numeric entry row with adjacent unit pill."""
        outer_container, pack_help = self._create_labeled_row(parent, label, help_text)

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
        pack_help()

    def _create_entry_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, help_text: str = ""
    ) -> None:
        """Create a clean dark text entry row."""
        outer_container, pack_help = self._create_labeled_row(parent, label, help_text)

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
        pack_help()

    def _create_masked_entry_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, help_text: str = ""
    ) -> None:
        """Create a masked password/API-key entry with toggle eye button."""
        outer_container, pack_help = self._create_labeled_row(parent, label, help_text)

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
        pack_help()

    def _create_combobox_row(
        self, parent: tk.Frame, label: str, var: tk.Variable, values: list[str], help_text: str = ""
    ) -> None:
        """Create a Combobox row with Dark.TCombobox styling."""
        outer_container, pack_help = self._create_labeled_row(parent, label, help_text)

        combo = ttk.Combobox(
            outer_container,
            textvariable=var,
            values=values,
            state="readonly",
            style="Dark.TCombobox",
        )
        combo.pack(fill=tk.X, expand=True)
        pack_help()

    def _load_current_vocabulary_into_ui(self) -> None:
        """Read custom_vocabulary.json and populate editor."""
        if not self.vocab_text:
            return
        terms = load_raw_vocabulary_terms(self.vocab_path)
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
        elif count <= MAX_VOCABULARY_TERMS:
            color = COLOR_GOLD
        else:
            color = COLOR_DANGER

        self.vocab_counter_lbl.configure(
            text=f"{count} / {MAX_VOCABULARY_TERMS} términos",
            fg=color,
        )

    def _show_toast(self, message: str, is_error: bool = False) -> None:
        """Display an inline status notification directly in the bottom dock bar."""
        if not self.toast_lbl:
            return
        fg_col = COLOR_DANGER if is_error else COLOR_SPOTIFY
        self.toast_lbl.configure(text=message, fg=fg_col)
        if self.window and self.window.winfo_exists():
            if self._toast_timer_id is not None:
                try:
                    self.window.after_cancel(self._toast_timer_id)
                except Exception:
                    pass
            self._toast_timer_id = self.window.after(4000, self._hide_toast)

    def _hide_toast(self) -> None:
        """Clear inline status notification."""
        self._toast_timer_id = None
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
        """Close modal cleanly and cancel pending timers."""
        self._cancel_active_capture()
        if self.window:
            for timer_id in (self._toast_timer_id, self._close_timer_id):
                if timer_id is not None:
                    try:
                        self.window.after_cancel(timer_id)
                    except Exception:
                        pass
            self._toast_timer_id = None
            self._close_timer_id = None
            self.window.destroy()
            self.window = None

    def _on_save(self) -> None:
        """Validate, persist to config.json, update current_config, and apply live hot reload."""
        self._cancel_active_capture()
        try:
            dictation_val = self.var_dictation.get().strip()
            rewrite_val = self.var_rewrite.get().strip()
            engine_str = self.var_engine.get().strip().upper()
            stt_lang = self.var_stt_language.get().strip() or "es"
            stt_model = self.var_stt_model.get().strip()
            llm_model = self.var_llm_model.get().strip()

            try:
                max_sec = int(self.var_max_sec.get())
            except (tk.TclError, ValueError):
                self._show_toast(
                    "La duración máxima debe ser un número entero entre 5 y 300 segundos.",
                    is_error=True,
                )
                return

            if not (5 <= max_sec <= 300):
                self._show_toast(
                    "La duración máxima debe estar entre 5 y 300 segundos.",
                    is_error=True,
                )
                return

            try:
                delay_ms = int(self.var_delay_ms.get())
            except (tk.TclError, ValueError):
                delay_ms = 80

            if not dictation_val:
                self._show_toast("El atajo de dictado no puede estar vacío.", is_error=True)
                return

            if not rewrite_val:
                self._show_toast("El atajo de reescritura no puede estar vacío.", is_error=True)
                return

            if dictation_val.lower() == rewrite_val.lower():
                self._show_toast(
                    "Los atajos de dictado y reescritura deben ser distintos.",
                    is_error=True,
                )
                return

            engine_type = (
                AudioEngineType.CLOUD if engine_str == "CLOUD" else AudioEngineType.LOCAL
            )

            # Groq API Key validation using canonical helper
            groq_key_val = self.var_groq_api_key.get().strip()
            has_valid_key = is_valid_groq_api_key(groq_key_val)

            if (
                engine_type == AudioEngineType.LOCAL
                and has_valid_key
                and not self._had_valid_key_on_open
            ):
                # First-time onboarding: user entered a valid Groq key while engine defaulted to LOCAL
                engine_type = AudioEngineType.CLOUD
                self.var_engine.set("CLOUD")

            if engine_type == AudioEngineType.CLOUD and not has_valid_key:
                msg = (
                    "Has seleccionado el motor CLOUD pero no has ingresado una clave válida de Groq (debe iniciar con 'gsk_').\n\n"
                    "• Haz clic en '🔑 Obtener clave gratuita...' para generar una en 1 clic.\n"
                    "• O cambia el motor de audio a 'LOCAL' para dictar sin internet.\n\n"
                    "¿Deseas cambiar automáticamente el motor a LOCAL para continuar?"
                )
                if messagebox.askyesno("Clave de Groq requerida", msg, parent=self.window):
                    engine_type = AudioEngineType.LOCAL
                    self.var_engine.set("LOCAL")
                else:
                    return
            elif engine_type == AudioEngineType.CLOUD and has_valid_key:
                is_valid, auth_msg = verify_groq_api_key_online(groq_key_val, timeout=2.5)
                if not is_valid:
                    warn_msg = (
                        f"La clave de Groq no superó la verificación en línea:\n\n"
                        f"{auth_msg}\n\n"
                        "¿Deseas guardarla de todas formas (por ejemplo si estás sin conexión)?"
                    )
                    if not messagebox.askyesno(
                        "Verificación de Groq", warn_msg, parent=self.window
                    ):
                        return

            # Validate vocabulary terms
            terms = self._get_current_terms_from_ui()
            if len(terms) > MAX_VOCABULARY_TERMS:
                msg = (
                    f"Has configurado {len(terms)} términos en el vocabulario.\n\n"
                    f"Para proteger la precisión de Whisper, el límite estricto es de {MAX_VOCABULARY_TERMS} términos.\n\n"
                    f"¿Deseas guardar únicamente los primeros {MAX_VOCABULARY_TERMS} términos y descartar los sobrantes?"
                )
                if not messagebox.askyesno(
                    "Límite de vocabulario excedido", msg, parent=self.window
                ):
                    return
                terms = terms[:MAX_VOCABULARY_TERMS]

            # Save custom_vocabulary.json
            try:
                with open(self.vocab_path, "w", encoding="utf-8") as f:
                    json.dump(terms, f, indent=2, ensure_ascii=False)
                logger.info(
                    "Custom vocabulary saved with %d terms to %s", len(terms), self.vocab_path
                )
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

            # Update user settings and clean legacy keys
            cfg_dict.pop("hotkey_settings", None)
            cfg_dict.pop("hotkey_diagnostics", None)
            cfg_dict.update(
                {
                    "hotkey_dictation": dictation_val,
                    "hotkey_rewrite": rewrite_val,
                    "engine": engine_type.value,
                    "stt_language": stt_lang,
                    "groq_stt_model": stt_model,
                    "groq_llm_model": llm_model,
                    "max_recording_seconds": max_sec,
                    "clipboard_restore_delay_ms": delay_ms,
                }
            )

            # Save config.json
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg_dict, f, indent=2, ensure_ascii=False)

            logger.info("Configuration saved successfully from settings modal.")

            # Persist Groq API Key securely to .env if provided and valid
            if has_valid_key:
                env_path = self.config_path.parent / ".env"
                persist_groq_api_key_to_env(env_path, groq_key_val)
                os.environ["GROQ_API_KEY"] = groq_key_val
                self._had_valid_key_on_open = True

            # Construct new AppConfig and update modal internal state immediately
            new_config = load_config(self.config_path)
            self.current_config = new_config

            # Trigger live hot reload on running orchestrator
            self.on_saved(new_config)

            # Spotify-style non-intrusive feedback
            self._show_toast(
                f"✓ Guardado: Dictado ({dictation_val}) | Reescritura ({rewrite_val})"
            )
            if self.window and self.window.winfo_exists():
                if self._close_timer_id is not None:
                    try:
                        self.window.after_cancel(self._close_timer_id)
                    except Exception:
                        pass
                self._close_timer_id = self.window.after(1100, self._on_cancel)

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            self._show_toast(f"Error al guardar: {e}", is_error=True)
