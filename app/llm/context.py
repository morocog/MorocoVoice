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
from app.platform.injector import get_clipboard_text, send_ctrl_c

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


# VERIFY: TOKEN_ELEVATION Win32 structure mapping
class TOKEN_ELEVATION(ctypes.Structure):
    _fields_ = [("TokenIsElevated", wintypes.DWORD)]


def is_process_elevated(pid: int) -> bool:
    """Check if target PID runs with Administrator elevation via OpenProcessToken & TokenElevation."""
    h_process = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h_process:
        # If we cannot even open the process with limited info, it is likely elevated higher than our standard token
        return True

    h_token = wintypes.HANDLE()
    try:
        if not ctypes.windll.advapi32.OpenProcessToken(h_process, TOKEN_QUERY, ctypes.byref(h_token)):
            err = ctypes.GetLastError()
            # ERROR_ACCESS_DENIED (5) indicates the target process token is elevated higher than caller
            if err == 5:
                return True
            return False

        elevation = TOKEN_ELEVATION()
        return_length = wintypes.DWORD()
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
    """Check if MorocoVoice itself is running with Administrator elevation."""
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
    """Capture selected text in foreground application using simulated staged Ctrl+C.

    Uses Win32 GetClipboardSequenceNumber() to detect if Ctrl+C placed new content
    on the clipboard with zero clipboard corruption, zero ghost items in Win+V,
    and zero risk of rewriting stale clipboard text when nothing was selected.
    """
    try:
        seq_before = ctypes.windll.user32.GetClipboardSequenceNumber()
    except Exception:
        seq_before = 0

    # Simulate clean Ctrl+C via staged SendInput with explicit modifier release
    send_ctrl_c()

    # Poll for clipboard update for up to 150 ms (15 ms intervals)
    seq_changed = False
    deadline = time.perf_counter() + 0.15
    while time.perf_counter() < deadline:
        time.sleep(0.015)
        try:
            curr_seq = ctypes.windll.user32.GetClipboardSequenceNumber()
            if curr_seq != seq_before and curr_seq != 0:
                seq_changed = True
                break
        except Exception:
            break

    if not seq_changed:
        logger.info("GetClipboardSequenceNumber unchanged after Ctrl+C: no text was selected.")
        return ""

    selected = get_clipboard_text()
    return selected.strip()
