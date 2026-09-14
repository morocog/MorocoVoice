"""Global keyboard hook subsystem with LIFO queue and AltGr conflict suppression.

Uses pynput to capture global shortcut combinations:
- alt+space: Dictation (Push-to-Talk & Toggle)
- ctrl+shift+space: Contextual selection rewrite
- ctrl+shift+q: Graceful shutdown
- ctrl+shift+d: Live log diagnostics
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from pynput import keyboard

from app.logging_setup import get_logger

logger = get_logger("hotkey")


class HotkeyListener:
    """Global keyboard hook listener with debounce and event callbacks."""

    def __init__(
        self,
        on_dictate_toggle: Callable[[], None] | None = None,
        on_rewrite_trigger: Callable[[], None] | None = None,
        on_shutdown_trigger: Callable[[], None] | None = None,
        on_diagnostics_trigger: Callable[[], None] | None = None,
    ) -> None:
        self.on_dictate_toggle = on_dictate_toggle
        self.on_rewrite_trigger = on_rewrite_trigger
        self.on_shutdown_trigger = on_shutdown_trigger
        self.on_diagnostics_trigger = on_diagnostics_trigger

        self._current_keys: set[keyboard.Key | keyboard.KeyCode] = set()
        self._listener: keyboard.Listener | None = None
        self._lock = threading.Lock()
        self._is_running = False

        # Debounce tracking
        self._last_dictate_time = 0.0
        self._last_rewrite_time = 0.0
        self._debounce_interval = 0.35  # seconds

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
            logger.info("Global hotkey listener registered (alt+space, ctrl+shift+space, ctrl+shift+q, ctrl+shift+d).")

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
        """Normalize left/right modifiers to canonical keys."""
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            return keyboard.Key.alt
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            return keyboard.Key.ctrl
        if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            return keyboard.Key.shift
        return key

    def _on_press(self, raw_key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle key down event."""
        if not self._is_running:
            return

        norm_key = self._normalize_key(raw_key)
        with self._lock:
            self._current_keys.add(norm_key)
            keys = set(self._current_keys)

        now = time.perf_counter()

        # 1. Shutdown: Ctrl + Shift + Q
        has_ctrl = keyboard.Key.ctrl in keys
        has_shift = keyboard.Key.shift in keys
        has_alt = keyboard.Key.alt in keys

        is_q = False
        is_d = False
        is_space = False

        if isinstance(raw_key, keyboard.KeyCode):
            char = (raw_key.char or "").lower()
            if char == "q":
                is_q = True
            elif char == "d":
                is_d = True
        elif raw_key == keyboard.Key.space:
            is_space = True

        if has_ctrl and has_shift and is_q:
            logger.info("Shutdown hotkey detected (Ctrl+Shift+Q).")
            if self.on_shutdown_trigger:
                threading.Thread(target=self.on_shutdown_trigger, daemon=True).start()
            return

        # 2. Diagnostics: Ctrl + Shift + D
        if has_ctrl and has_shift and is_d:
            logger.info("Diagnostics hotkey detected (Ctrl+Shift+D).")
            if self.on_diagnostics_trigger:
                threading.Thread(target=self.on_diagnostics_trigger, daemon=True).start()
            return

        # 3. Contextual Rewrite: Ctrl + Shift + Space
        if has_ctrl and has_shift and is_space:
            if now - self._last_rewrite_time >= self._debounce_interval:
                self._last_rewrite_time = now
                logger.info("Rewrite hotkey detected (Ctrl+Shift+Space).")
                if self.on_rewrite_trigger:
                    threading.Thread(target=self.on_rewrite_trigger, daemon=True).start()
            return

        # 4. Dictation: Alt + Space (without Ctrl or Shift)
        if has_alt and is_space and not has_ctrl and not has_shift:
            if now - self._last_dictate_time >= self._debounce_interval:
                self._last_dictate_time = now
                logger.info("Dictation hotkey detected (Alt+Space).")
                if self.on_dictate_toggle:
                    threading.Thread(target=self.on_dictate_toggle, daemon=True).start()
            return

    def _on_release(self, raw_key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle key up event."""
        norm_key = self._normalize_key(raw_key)
        with self._lock:
            self._current_keys.discard(norm_key)
            self._current_keys.discard(raw_key)
