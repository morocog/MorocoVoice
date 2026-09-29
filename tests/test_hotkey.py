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
