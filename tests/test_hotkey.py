"""Unit tests for hotkey parsing and combination matching."""

from pynput import keyboard

from app.platform.hotkey import parse_hotkey_string


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
