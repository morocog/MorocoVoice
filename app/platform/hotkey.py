"""Dynamic global keyboard hook subsystem supporting customizable hotkeys.

Parses arbitrary shortcut string combinations (e.g., 'ctrl+alt+space', 'alt+z', 'ctrl+shift+v')
and matches them against currently pressed keys with debouncing and safe thread dispatching.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from pynput import keyboard

from app.logging_setup import get_logger

logger = get_logger("hotkey")


@dataclass(frozen=True)
class ParsedHotkey:
    """Representation of a parsed key combination."""
    raw_str: str
    ctrl: bool
    alt: bool
    shift: bool
    win: bool
    key_name: str

    def matches(self, active_keys: set[keyboard.Key | keyboard.KeyCode], pressed_key: keyboard.Key | keyboard.KeyCode) -> bool:
        """Evaluate if the currently active keys satisfy this hotkey combination."""
        # Modifiers check
        has_ctrl = keyboard.Key.ctrl in active_keys
        has_alt = keyboard.Key.alt in active_keys
        has_shift = keyboard.Key.shift in active_keys
        has_win = keyboard.Key.cmd in active_keys

        if self.ctrl != has_ctrl:
            return False
        if self.alt != has_alt:
            return False
        if self.shift != has_shift:
            return False
        if self.win != has_win:
            return False

        # Target key check
        pressed_name = ""
        if isinstance(pressed_key, keyboard.Key):
            pressed_name = pressed_key.name.lower()
        elif isinstance(pressed_key, keyboard.KeyCode):
            pressed_name = (pressed_key.char or "").lower()

        return pressed_name == self.key_name.lower()


def parse_hotkey_string(hotkey_str: str) -> ParsedHotkey | None:
    """Parse string representation into a ParsedHotkey object."""
    tokens = [t.strip().lower() for t in hotkey_str.split("+") if t.strip()]
    if not tokens:
        return None

    ctrl = False
    alt = False
    shift = False
    win = False
    main_key = ""

    for token in tokens:
        if token in ("ctrl", "control"):
            ctrl = True
        elif token in ("alt", "menu"):
            alt = True
        elif token == "shift":
            shift = True
        elif token in ("win", "windows", "cmd", "super"):
            win = True
        else:
            main_key = token

    if not main_key:
        return None

    return ParsedHotkey(
        raw_str=hotkey_str,
        ctrl=ctrl,
        alt=alt,
        shift=shift,
        win=win,
        key_name=main_key,
    )


class HotkeyListener:
    """Global keyboard hook listener with dynamic hotkey mapping and debounce."""

    def __init__(
        self,
        hotkey_dictation: str = "ctrl+alt+space",
        hotkey_rewrite: str = "ctrl+shift+space",
        hotkey_shutdown: str = "ctrl+shift+q",
        hotkey_diagnostics: str = "ctrl+shift+d",
        on_dictate_toggle: Callable[[], None] | None = None,
        on_rewrite_trigger: Callable[[], None] | None = None,
        on_shutdown_trigger: Callable[[], None] | None = None,
        on_diagnostics_trigger: Callable[[], None] | None = None,
    ) -> None:
        self.on_dictate_toggle = on_dictate_toggle
        self.on_rewrite_trigger = on_rewrite_trigger
        self.on_shutdown_trigger = on_shutdown_trigger
        self.on_diagnostics_trigger = on_diagnostics_trigger

        self.update_shortcuts(
            dictation=hotkey_dictation,
            rewrite=hotkey_rewrite,
            shutdown=hotkey_shutdown,
            diagnostics=hotkey_diagnostics,
        )

        self._current_keys: set[keyboard.Key | keyboard.KeyCode] = set()
        self._listener: keyboard.Listener | None = None
        self._lock = threading.Lock()
        self._is_running = False

        # Debounce tracking
        self._last_dictate_time = 0.0
        self._last_rewrite_time = 0.0
        self._debounce_interval = 0.35

    def update_shortcuts(
        self,
        dictation: str,
        rewrite: str,
        shutdown: str,
        diagnostics: str,
    ) -> None:
        """Update parsed shortcut triggers dynamically without restarting the listener."""
        self._hk_dictation = parse_hotkey_string(dictation)
        self._hk_rewrite = parse_hotkey_string(rewrite)
        self._hk_shutdown = parse_hotkey_string(shutdown)
        self._hk_diagnostics = parse_hotkey_string(diagnostics)
        logger.info(
            "Shortcuts mapped: Dictation=%s, Rewrite=%s, Shutdown=%s, Diagnostics=%s",
            dictation,
            rewrite,
            shutdown,
            diagnostics,
        )

    def start(self) -> None:
        """Start the background pynput keyboard listener."""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._current_keys.clear()
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.daemon = True
            self._listener.start()
            logger.info("Global hotkey listener registered and active.")

    def stop(self) -> None:
        """Stop the background keyboard listener safely."""
        with self._lock:
            self._is_running = False
            listener = self._listener
            self._listener = None
            self._current_keys.clear()

        if listener is not None:
            try:
                listener.stop()
                logger.info("Global hotkey listener stopped.")
            except Exception as e:
                logger.warning("Error stopping hotkey listener: %s", e)

    def _normalize_key(self, key: keyboard.Key | keyboard.KeyCode) -> keyboard.Key | keyboard.KeyCode:
        """Normalize left/right/AltGr modifiers to canonical modifier keys."""
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            return keyboard.Key.alt
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            return keyboard.Key.ctrl
        if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            return keyboard.Key.shift
        if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
            return keyboard.Key.cmd
        return key

    def _on_press(self, raw_key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle key down event."""
        if not self._is_running:
            return

        norm_key = self._normalize_key(raw_key)
        with self._lock:
            self._current_keys.add(norm_key)
            active_keys = set(self._current_keys)

        now = time.perf_counter()

        # 1. Shutdown check
        if self._hk_shutdown and self._hk_shutdown.matches(active_keys, norm_key):
            logger.info("Shutdown hotkey triggered (%s).", self._hk_shutdown.raw_str)
            if self.on_shutdown_trigger:
                threading.Thread(target=self.on_shutdown_trigger, daemon=True).start()
            return

        # 2. Diagnostics check
        if self._hk_diagnostics and self._hk_diagnostics.matches(active_keys, norm_key):
            logger.info("Diagnostics hotkey triggered (%s).", self._hk_diagnostics.raw_str)
            if self.on_diagnostics_trigger:
                threading.Thread(target=self.on_diagnostics_trigger, daemon=True).start()
            return

        # 3. Contextual Rewrite check
        if self._hk_rewrite and self._hk_rewrite.matches(active_keys, norm_key):
            if now - self._last_rewrite_time >= self._debounce_interval:
                self._last_rewrite_time = now
                logger.info("Rewrite hotkey triggered (%s).", self._hk_rewrite.raw_str)
                if self.on_rewrite_trigger:
                    threading.Thread(target=self.on_rewrite_trigger, daemon=True).start()
            return

        # 4. Dictation check
        if self._hk_dictation and self._hk_dictation.matches(active_keys, norm_key):
            if now - self._last_dictate_time >= self._debounce_interval:
                self._last_dictate_time = now
                logger.info("Dictation hotkey triggered (%s).", self._hk_dictation.raw_str)
                if self.on_dictate_toggle:
                    threading.Thread(target=self.on_dictate_toggle, daemon=True).start()
            return

    def _on_release(self, raw_key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle key up event."""
        norm_key = self._normalize_key(raw_key)
        with self._lock:
            self._current_keys.discard(norm_key)
            self._current_keys.discard(raw_key)
