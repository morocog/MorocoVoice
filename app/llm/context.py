"""Active foreground context extraction and UIPI elevation detection.

Inspects the active foreground window, extracts the target process binary name,
checks TokenElevation to prevent UIPI injection failures, and captures selected text.
"""

from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes
from pathlib import Path

from app.logging_setup import get_logger
from app.platform.injector import get_clipboard_text, send_ctrl_c, set_clipboard_text

logger = get_logger("context")

# Win32 Constants
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TokenElevation = 20
VK_CONTROL = 0x11
VK_C = 0x43
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


# # VERIFY: TOKEN_ELEVATION Win32 structure mapping
class TOKEN_ELEVATION(ctypes.Structure):
    _fields_ = [("TokenIsElevated", wintypes.DWORD)]


def is_process_elevated(pid: int) -> bool:
    """# VERIFY: Check if target PID runs with Administrator elevation via OpenProcessToken & TokenElevation."""
    h_process = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h_process:
        # If we cannot even open the process with limited info, it is likely elevated higher than our standard token
        return True

    h_token = wintypes.HANDLE()
    try:
        if not ctypes.windll.advapi32.OpenProcessToken(h_process, TOKEN_QUERY, ctypes.byref(h_token)):
            return False

        elevation = TOKEN_ELEVATION()
        return_length = wintypes.DWORD()
        # # VERIFY: TokenElevation = 20, size must match TOKEN_ELEVATION struct
        if ctypes.windll.advapi32.GetTokenInformation(
            h_token,
            TokenElevation,
            ctypes.byref(elevation),
            ctypes.sizeof(TOKEN_ELEVATION),
            ctypes.byref(return_length),
        ):
            return bool(elevation.TokenIsElevated)
        return False
    finally:
        if h_token:
            ctypes.windll.kernel32.CloseHandle(h_token)
        ctypes.windll.kernel32.CloseHandle(h_process)


def is_current_process_elevated() -> bool:
    """Check if VoiceFlow-Win itself is running with Administrator elevation."""
    return is_process_elevated(os.getpid())


def get_foreground_app_info() -> tuple[str, int, bool]:
    """Return (process_name, pid, is_elevated) for the current foreground window."""
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return ("unknown.exe", 0, False)

    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    target_pid = pid.value

    # Get Process Image Name
    h_process = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, target_pid)
    process_name = "unknown.exe"

    if h_process:
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if ctypes.windll.kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
                process_name = Path(buf.value).name.lower()
        finally:
            ctypes.windll.kernel32.CloseHandle(h_process)

    elevated = is_process_elevated(target_pid)
    logger.info("Foreground window inspected: %s (PID: %d, Elevated: %s)", process_name, target_pid, elevated)
    return (process_name, target_pid, elevated)


def get_selected_text() -> str:
    """Capture selected text in foreground application using simulated staged Ctrl+C."""
    # Backup original clipboard
    orig_clipboard = get_clipboard_text()

    # Clear clipboard to detect if copy succeeds
    set_clipboard_text("")

    # Simulate clean Ctrl+C via staged SendInput with explicit modifier release
    send_ctrl_c()

    time.sleep(0.12)  # Wait for application to fill clipboard
    selected = get_clipboard_text()

    # Restore original clipboard
    if orig_clipboard:
        set_clipboard_text(orig_clipboard)

    return selected.strip()
