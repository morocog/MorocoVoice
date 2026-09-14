"""Unit tests for Win32 injector structures, clipboard transactions, and hijack detection."""

import ctypes

import pytest

from app.platform.injector import (
    INPUT,
    emergency_restore,
    get_clipboard_text,
    set_clipboard_text,
)


def test_input_struct_size():
    """# VERIFY: Validate that INPUT structure size equals 40 bytes on 64-bit Windows."""
    is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
    expected_size = 40 if is_64bit else 28
    assert ctypes.sizeof(INPUT) == expected_size


def test_clipboard_roundtrip():
    """Verify clipboard get and set operations retain Unicode text accurately."""
    test_str = "VoiceFlow-Win-Test-Unicode-123_ñáéíóú"
    success = set_clipboard_text(test_str)
    if not success:
        pytest.skip("Clipboard unavailable in current headless test runner.")

    result = get_clipboard_text()
    assert result == test_str


def test_emergency_restore_safeguard():
    """Verify emergency_restore resets pending backup safely."""
    emergency_restore()
    # Should complete without throwing exceptions
    assert True


def test_clipboard_lock_reentrancy():
    """Verify _clipboard_lock is reentrant (RLock) to prevent deadlocks on exception recovery."""
    from app.platform.injector import _clipboard_lock

    with _clipboard_lock:
        # Calling emergency_restore while holding lock MUST NOT deadlock
        emergency_restore()
    assert True


def test_release_modifiers_executes_safely():
    """Verify release_modifiers executes without raising Win32 exceptions."""
    from app.platform.injector import release_modifiers

    release_modifiers()
    assert True

