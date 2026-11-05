"""Unit tests for foreground window detection, TokenElevation structures, and selection capture."""

import os
from unittest.mock import patch

from app.llm.context import (
    get_foreground_app_info,
    get_selected_text,
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


def test_get_selected_text_empty_when_no_clipboard_change():
    """Verify get_selected_text returns empty string when sequence number never changes."""
    with patch("ctypes.windll.user32.GetClipboardSequenceNumber", return_value=100), \
         patch("app.llm.context.send_ctrl_c"):
        result = get_selected_text()
        assert result == ""


def test_get_selected_text_returns_content_on_sequence_change():
    """Verify get_selected_text returns text when sequence number increments."""
    # First call returns 100, subsequent calls return 101
    seq_calls = [100, 101, 101]

    def mock_seq():
        return seq_calls.pop(0) if seq_calls else 101

    with patch("ctypes.windll.user32.GetClipboardSequenceNumber", side_effect=mock_seq), \
         patch("app.llm.context.send_ctrl_c"), \
         patch("app.llm.context.get_clipboard_text", return_value="Selected text payload"):
        result = get_selected_text()
        assert result == "Selected text payload"
