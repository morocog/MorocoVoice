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

#: Virtual-key code for SHIFT. Tapped alone by the capture self-test: it emits no
#: character, fires no shortcut and changes no state, yet travels the full input path.
VK_SHIFT = 0x10

KEY_ALIASES: dict[str, str] = {
    "espacio": "space",
    "barra": "space",
    "spacebar": "space",
    "intro": "enter",
    "return": "enter",
    "escape": "esc",
    "supr": "delete",
    "del": "delete",
}

VK_SPECIAL_MAP: dict[int, str] = {
    8: "backspace",
    9: "tab",
    13: "enter",
    27: "esc",
    32: "space",
    46: "delete",
}


def extract_key_name(key: keyboard.Key | keyboard.KeyCode) -> str:
    """Extract canonical lowercase string representation of a key.

    Handles Windows ASCII control characters when Ctrl is pressed (e.g. Ctrl+S -> 0x13,
    Ctrl+H -> 0x08), Virtual Key (VK) codes for alphanumeric and function keys, and Key enum names.
    """
    if isinstance(key, keyboard.Key):
        return key.name.lower()
    if isinstance(key, keyboard.KeyCode):
        if key.char:
            c = key.char
            if c == " ":
                return "space"
            # On Windows, Ctrl+A .. Ctrl+Z produce ASCII control codes 1..26 (\x01 - \x1a)
            if 1 <= ord(c) <= 26:
                return chr(ord(c) + 96).lower()
            return c.lower()
        if key.vk:
            if key.vk in VK_SPECIAL_MAP:
                return VK_SPECIAL_MAP[key.vk]
            # 65-90: A-Z
            if 65 <= key.vk <= 90:
                return chr(key.vk).lower()
            # 48-57: 0-9
            if 48 <= key.vk <= 57:
                return chr(key.vk)
            # 96-105: Numpad 0-9
            if 96 <= key.vk <= 105:
                return chr(key.vk - 48)
            # 112-123: F1-F12
            if 112 <= key.vk <= 123:
                return f"f{key.vk - 111}"
    return ""


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
        has_ctrl = any(k in active_keys for k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r))
        has_alt = any(k in active_keys for k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr))
        has_shift = any(k in active_keys for k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r))
        has_win = any(k in active_keys for k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r))

        if self.ctrl != has_ctrl:
            return False
        if self.alt != has_alt:
            return False
        if self.shift != has_shift:
            return False
        if self.win != has_win:
            return False

        # Target key check
        pressed_name = extract_key_name(pressed_key)
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

    main_key = KEY_ALIASES.get(main_key, main_key)

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
        hotkey_dictation: str = "win+space",
        hotkey_rewrite: str = "ctrl+shift+space",
        hotkey_shutdown: str = "",
        hotkey_diagnostics: str = "",
        hotkey_settings: str = "",
        on_dictate_toggle: Callable[[], None] | None = None,
        on_rewrite_trigger: Callable[[], None] | None = None,
        on_shutdown_trigger: Callable[[], None] | None = None,
        on_diagnostics_trigger: Callable[[], None] | None = None,
        on_settings_trigger: Callable[[], None] | None = None,
    ) -> None:
        self.on_dictate_toggle = on_dictate_toggle
        self.on_rewrite_trigger = on_rewrite_trigger
        self.on_shutdown_trigger = on_shutdown_trigger
        self.on_diagnostics_trigger = on_diagnostics_trigger
        self.on_settings_trigger = on_settings_trigger

        self.update_shortcuts(
            dictation=hotkey_dictation,
            rewrite=hotkey_rewrite,
            shutdown=hotkey_shutdown,
            diagnostics=hotkey_diagnostics,
            settings=hotkey_settings,
        )

        self._current_keys: set[keyboard.Key | keyboard.KeyCode] = set()
        self._listener: keyboard.Listener | None = None
        self._lock = threading.Lock()
        self._is_running = False

        # Debounce tracking
        self._last_dictate_time = 0.0
        self._last_rewrite_time = 0.0
        self._debounce_interval = 0.35

        # Capture watchdog: counts every key event the hook actually delivers.
        self._event_count = 0

    def update_shortcuts(
        self,
        dictation: str,
        rewrite: str,
        shutdown: str,
        diagnostics: str,
        settings: str = "",
    ) -> None:
        """Update parsed shortcut triggers dynamically without restarting the listener."""
        self._hk_dictation = parse_hotkey_string(dictation)
        self._hk_rewrite = parse_hotkey_string(rewrite)
        self._hk_shutdown = parse_hotkey_string(shutdown)
        self._hk_diagnostics = parse_hotkey_string(diagnostics)
        self._hk_settings = parse_hotkey_string(settings)
        logger.info(
            "Shortcuts mapped: Dictation=%s, Rewrite=%s, Settings=%s, Shutdown=%s, Diagnostics=%s",
            dictation,
            rewrite,
            settings,
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
        threading.Thread(target=self._verify_capture, daemon=True, name="HotkeyWatchdog").start()

    def _verify_capture(self) -> None:
        """Prove the keyboard hook really receives input, not merely that it lives.

        A live listener thread is NOT evidence that keys arrive. At Low integrity
        ``SetWindowsHookEx`` succeeds and the thread pumps messages happily while
        UIPI silently drops every event, so the app logs "listener active" and no
        shortcut ever fires. Liveness checks therefore cannot detect the failure
        that matters, which is why this watchdog taps a harmless lone modifier
        with SendInput and requires the hook to observe it.
        """
        time.sleep(1.2)
        listener = self._listener
        if listener is None:
            return
        if not listener.is_alive():
            logger.error(
                "Keyboard hook FAILED: the listener thread died during startup, so NO "
                "global shortcut will work. Windows most likely refused SetWindowsHookEx."
            )
            return

        baseline = self._event_count
        tapped = False
        try:
            from app.platform.injector import send_vk_tap

            tapped = send_vk_tap(VK_SHIFT)
        except Exception as exc:
            logger.warning("Could not run the keyboard capture self-test: %s", exc)
            return

        if not tapped:
            logger.debug("Keyboard capture self-test skipped: SendInput not available in current session/focus.")
            return

        deadline = time.perf_counter() + 1.0
        while time.perf_counter() < deadline:
            if self._event_count > baseline:
                logger.info(
                    "Keyboard hook verified: it is receiving input "
                    "(self-test keystroke observed)."
                )
                return
            time.sleep(0.05)

        logger.error(
            "Keyboard hook is NOT receiving input: the self-test keystroke was sent "
            "(SendInput accepted=%s) but the hook observed 0 events. Windows is "
            "delivering keyboard input somewhere this process cannot see. This is the "
            "classic signature of an environment-restricted process (Low integrity) or "
            "an AppContainer, and NO global shortcut can work until it is fixed. "
            "Run diagnostico.bat for a full report, and see docs/TROUBLESHOOTING.md.",
            tapped,
        )

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
        # Counted before any gate: the capture watchdog needs to know whether the
        # hook delivers anything at all, regardless of what is currently mapped.
        self._event_count += 1

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

        # 2. Settings check. This is the guaranteed keyboard route into
        #    Configuracion when the tray icon is unavailable or rejected.
        if self._hk_settings and self._hk_settings.matches(active_keys, norm_key):
            logger.info("Settings hotkey triggered (%s).", self._hk_settings.raw_str)
            if self.on_settings_trigger:
                threading.Thread(target=self.on_settings_trigger, daemon=True).start()
            return

        # 3. Diagnostics check
        if self._hk_diagnostics and self._hk_diagnostics.matches(active_keys, norm_key):
            logger.info("Diagnostics hotkey triggered (%s).", self._hk_diagnostics.raw_str)
            if self.on_diagnostics_trigger:
                threading.Thread(target=self.on_diagnostics_trigger, daemon=True).start()
            return

        # 4. Contextual Rewrite check
        if self._hk_rewrite and self._hk_rewrite.matches(active_keys, norm_key):
            if now - self._last_rewrite_time >= self._debounce_interval:
                self._last_rewrite_time = now
                logger.info("Rewrite hotkey triggered (%s).", self._hk_rewrite.raw_str)
                if self.on_rewrite_trigger:
                    threading.Thread(target=self.on_rewrite_trigger, daemon=True).start()
            return

        # 5. Dictation check
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
            if isinstance(raw_key, keyboard.KeyCode) and raw_key.vk:
                self._current_keys = {
                    k for k in self._current_keys
                    if not (isinstance(k, keyboard.KeyCode) and k.vk == raw_key.vk)
                }
