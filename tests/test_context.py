"""Unit tests for foreground window detection and TokenElevation structures."""

import os

from app.llm.context import (
    get_foreground_app_info,
    is_current_process_elevated,
    is_process_elevated,
)


def test_current_process_elevation():
    """Verify is_current_process_elevated returns a boolean value without error."""
    elevated = is_current_process_elevated()
    assert isinstance(elevated, bool)


def test_pid_elevation_check():
    """Verify elevation check on current process PID matches current elevation."""
    current_pid = os.getpid()
    assert is_process_elevated(current_pid) == is_current_process_elevated()


def test_foreground_app_detection():
    """Verify get_foreground_app_info returns a 3-tuple (str, int, bool)."""
    app_name, pid, is_elev = get_foreground_app_info()
    assert isinstance(app_name, str)
    assert isinstance(pid, int)
    assert isinstance(is_elev, bool)
