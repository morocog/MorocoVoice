"""Unit tests for hotkey parsing and combination matching."""

import threading

from pynput import keyboard

from app.platform.hotkey import HotkeyListener, parse_hotkey_string


def test_parse_hotkey_modifiers():
    """Verify parsing of various modifier combinations."""
    hk = parse_hotkey_string("win+space")
    assert hk is not None
    assert hk.win is True
    assert hk.ctrl is False
    assert hk.alt is False
    assert hk.shift is False
    assert hk.key_name == "space"

    hk_rewrite = parse_hotkey_string("ctrl+shift+space")
    assert hk_rewrite is not None
    assert hk_rewrite.ctrl is True
    assert hk_rewrite.shift is True
    assert hk_rewrite.alt is False
    assert hk_rewrite.win is False
    assert hk_rewrite.key_name == "space"


def test_space_alone_does_not_match_win_space():
    """Verify that pressing Spacebar alone does NOT trigger win+space hotkey."""
    hk = parse_hotkey_string("win+space")
    assert hk is not None
    # No modifiers active, only Space pressed
    assert hk.matches(set(), keyboard.Key.space) is False
    # Win modifier active and Space pressed
    assert hk.matches({keyboard.Key.cmd}, keyboard.Key.space) is True


def test_custom_single_key_hotkey():
    """Verify single function key like F8 parses without modifiers."""
    hk = parse_hotkey_string("f8")
    assert hk is not None
    assert hk.ctrl is False
    assert hk.alt is False
    assert hk.shift is False
    assert hk.win is False
    assert hk.key_name == "f8"
    assert hk.matches(set(), keyboard.Key.f8) is True


def test_settings_hotkey_dispatches_callback():
    """The Settings combination must actually call the Settings callback.

    This is the keyboard escape hatch that keeps MorocoVoice usable when the
    tray icon cannot be created (a restricted environment rejects it) or when
    Windows 11 parks it in the overflow flyout. If this dispatch breaks, a user
    with no tray icon has no route into the Settings window at all.
    """
    fired = threading.Event()
    listener = HotkeyListener(
        hotkey_settings="ctrl+alt+s",
        on_settings_trigger=fired.set,
    )
    # Drive the key handler directly; no real hook or event loop is involved.
    listener._is_running = True

    listener._on_press(keyboard.Key.ctrl_l)
    assert not fired.is_set(), "Ctrl alone must not trigger the Settings shortcut"

    listener._on_press(keyboard.Key.alt_l)
    assert not fired.is_set(), "Ctrl+Alt alone must not trigger the Settings shortcut"

    listener._on_press(keyboard.KeyCode.from_char("s"))
    assert fired.wait(timeout=2.0) is True


def test_empty_settings_hotkey_is_disabled_and_harmless():
    """An empty Settings shortcut must simply never fire, not raise."""
    listener = HotkeyListener(hotkey_settings="")
    listener._is_running = True
    listener._on_press(keyboard.Key.ctrl_l)
    listener._on_press(keyboard.Key.alt_l)
    listener._on_press(keyboard.KeyCode.from_char("s"))
    assert listener._hk_settings is None


def test_windows_ctrl_letter_control_characters():
    """Ensure Windows ASCII control chars (e.g. Ctrl+S -> 0x13, Ctrl+H -> 0x08) match properly."""
    # Test ctrl+s
    hk_s = parse_hotkey_string("ctrl+s")
    assert hk_s is not None
    # KeyCode with char='\x13' and vk=83 (as emitted by Windows WH_KEYBOARD_LL under Ctrl)
    key_ctrl_s = keyboard.KeyCode(char="\x13", vk=83)
    assert hk_s.matches({keyboard.Key.ctrl}, key_ctrl_s) is True

    # Test ctrl+h
    hk_h = parse_hotkey_string("ctrl+h")
    assert hk_h is not None
    key_ctrl_h = keyboard.KeyCode(char="\x08", vk=72)
    assert hk_h.matches({keyboard.Key.ctrl}, key_ctrl_h) is True

    # Test key with no char but valid vk (e.g. F8 or numpad)
    key_vk_only = keyboard.KeyCode(char=None, vk=83)  # 's' by vk
    assert hk_s.matches({keyboard.Key.ctrl}, key_vk_only) is True


def test_spanish_aliases_parsed():
    """Ensure Spanish aliases like 'espacio' parse to 'space'."""
    hk = parse_hotkey_string("win+espacio")
    assert hk is not None
    assert hk.key_name == "space"
    assert hk.win is True


def test_live_listener_triggers_with_windows_ctrl_s():
    """Verify live HotkeyListener triggers dictation when Windows sends Ctrl+S with ASCII 0x13."""
    fired = threading.Event()
    listener = HotkeyListener(
        hotkey_dictation="ctrl+s",
        on_dictate_toggle=fired.set,
    )
    listener._is_running = True

    listener._on_press(keyboard.Key.ctrl_l)
    assert not fired.is_set()

    # Windows emits char='\x13' (Device Control 3) for Ctrl+S
    listener._on_press(keyboard.KeyCode(char="\x13", vk=83))
    assert fired.wait(timeout=2.0) is True
