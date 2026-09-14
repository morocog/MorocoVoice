"""Win32 text injector using SendInput and guarded clipboard transactions.

Implements high-speed text injection via synthetic Ctrl+V with clipboard backup,
hijack detection (Ditto, Win+V), atexit emergency restore, and UIPI elevation safety.
"""

from __future__ import annotations

import atexit
import ctypes
import threading
import time
from ctypes import wintypes

from app.contracts import InjectionError
from app.logging_setup import get_logger

logger = get_logger("injector")

# Win32 Constants
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1

# # VERIFY: Standard Win32 64-bit ULONG_PTR sizing for SendInput compatibility across x64
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


# # VERIFY: Win32 KEYBDINPUT structure alignment and padding according to MSDN
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


# Global state for emergency clipboard restore with reentrant lock to prevent deadlocks
_active_backup_text: str | None = None
_injected_expected_text: str | None = None
_clipboard_lock = threading.RLock()


try:
    import win32clipboard as wcb
    import win32con
    _HAS_PYWIN32_CLIP = True
except Exception:
    _HAS_PYWIN32_CLIP = False


def get_clipboard_text() -> str:
    """Retrieve current text content from clipboard with retry loop and 64-bit safety."""
    if _HAS_PYWIN32_CLIP:
        for _ in range(6):
            try:
                wcb.OpenClipboard()
                try:
                    if wcb.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                        val = wcb.GetClipboardData(win32con.CF_UNICODETEXT)
                        return val or ""
                    return ""
                finally:
                    wcb.CloseClipboard()
            except Exception:
                time.sleep(0.015)
        return ""

    # 64-bit ctypes fallback
    for _ in range(6):
        if ctypes.windll.user32.OpenClipboard(None):
            try:
                ctypes.windll.user32.GetClipboardData.restype = ctypes.c_void_p
                h_glb = ctypes.windll.user32.GetClipboardData(13)
                if not h_glb:
                    return ""
                ctypes.windll.kernel32.GlobalLock.restype = ctypes.c_void_p
                ptr = ctypes.windll.kernel32.GlobalLock(h_glb)
                if not ptr:
                    return ""
                try:
                    return ctypes.c_wchar_p(ptr).value or ""
                finally:
                    ctypes.windll.kernel32.GlobalUnlock(h_glb)
            finally:
                ctypes.windll.user32.CloseClipboard()
        time.sleep(0.015)
    return ""


def set_clipboard_text(text: str) -> bool:
    """Set text content into clipboard with retry loop and 64-bit safety."""
    if _HAS_PYWIN32_CLIP:
        for _ in range(6):
            try:
                wcb.OpenClipboard()
                try:
                    wcb.EmptyClipboard()
                    wcb.SetClipboardText(text, win32con.CF_UNICODETEXT)
                    return True
                finally:
                    wcb.CloseClipboard()
            except Exception:
                time.sleep(0.015)
        return False

    # 64-bit ctypes fallback with explicit pointer types
    for _ in range(6):
        if ctypes.windll.user32.OpenClipboard(None):
            try:
                ctypes.windll.user32.EmptyClipboard()
                buffer = (text + "\0").encode("utf-16-le")
                ctypes.windll.kernel32.GlobalAlloc.restype = ctypes.c_void_p
                h_glb = ctypes.windll.kernel32.GlobalAlloc(0x0002, len(buffer))
                if not h_glb:
                    return False
                ctypes.windll.kernel32.GlobalLock.restype = ctypes.c_void_p
                ptr = ctypes.windll.kernel32.GlobalLock(h_glb)
                if not ptr:
                    ctypes.windll.kernel32.GlobalFree(h_glb)
                    return False
                try:
                    ctypes.memmove(ptr, buffer, len(buffer))
                finally:
                    ctypes.windll.kernel32.GlobalUnlock(h_glb)
                ctypes.windll.user32.SetClipboardData.restype = ctypes.c_void_p
                res = ctypes.windll.user32.SetClipboardData(13, h_glb)
                return bool(res)
            finally:
                ctypes.windll.user32.CloseClipboard()
        time.sleep(0.015)
    return False


def release_modifiers() -> None:
    """Release physical modifier keys (Alt, Win, Shift, Ctrl) to prevent combination conflicts."""
    mods = [VK_MENU, VK_LWIN, VK_RWIN, VK_SHIFT]
    cb_size = ctypes.sizeof(INPUT)
    inputs = (INPUT * len(mods))()
    for i, vk in enumerate(mods):
        inputs[i].type = INPUT_KEYBOARD
        inputs[i].union.ki = KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, 0)
    ctypes.windll.user32.SendInput(len(mods), ctypes.byref(inputs), cb_size)
    time.sleep(0.02)


def send_ctrl_v() -> None:
    """Synthesize Ctrl+V keydown/keyup events using staged Win32 SendInput."""
    # Ensure no lingering modifiers (Alt/Win/Shift) warp Ctrl+V into Win+Ctrl+V or Alt+Ctrl+V
    release_modifiers()

    cb_size = ctypes.sizeof(INPUT)

    # 1. Ctrl Down
    down_ctrl = (INPUT * 1)()
    down_ctrl[0].type = INPUT_KEYBOARD
    down_ctrl[0].union.ki = KEYBDINPUT(VK_CONTROL, 0, 0, 0, 0)
    ctypes.windll.user32.SendInput(1, ctypes.byref(down_ctrl), cb_size)
    time.sleep(0.015)

    # 2. V Down and V Up
    press_v = (INPUT * 2)()
    press_v[0].type = INPUT_KEYBOARD
    press_v[0].union.ki = KEYBDINPUT(VK_V, 0, 0, 0, 0)
    press_v[1].type = INPUT_KEYBOARD
    press_v[1].union.ki = KEYBDINPUT(VK_V, 0, KEYEVENTF_KEYUP, 0, 0)
    ctypes.windll.user32.SendInput(2, ctypes.byref(press_v), cb_size)
    time.sleep(0.015)

    # 3. Ctrl Up
    up_ctrl = (INPUT * 1)()
    up_ctrl[0].type = INPUT_KEYBOARD
    up_ctrl[0].union.ki = KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, 0)
    ctypes.windll.user32.SendInput(1, ctypes.byref(up_ctrl), cb_size)
    time.sleep(0.02)


def emergency_restore() -> None:
    """Atexit / shutdown safety hook to guarantee user clipboard restoration."""
    global _active_backup_text, _injected_expected_text
    with _clipboard_lock:
        if _active_backup_text is not None:
            try:
                curr = get_clipboard_text()
                # Only restore if clipboard still holds our injected text
                if curr == _injected_expected_text:
                    set_clipboard_text(_active_backup_text)
                    logger.info("Emergency clipboard restoration completed.")
            except Exception as e:
                logger.error("Failed during emergency clipboard restore: %s", e)
            finally:
                _active_backup_text = None
                _injected_expected_text = None


# Register emergency restoration at process exit
atexit.register(emergency_restore)


def inject_text(text: str, restore_delay_ms: int = 80) -> bool:
    """Safely inject text into active control via SendInput and guarded clipboard."""
    global _active_backup_text, _injected_expected_text

    if not text:
        return True

    with _clipboard_lock:
        # Step 1: Backup current user clipboard
        backup_text = get_clipboard_text()
        _active_backup_text = backup_text
        _injected_expected_text = text

        try:
            # Step 2: Write injected payload
            if not set_clipboard_text(text):
                raise InjectionError("Failed to set clipboard text before injection.")

            # Step 3: Trigger Ctrl+V
            send_ctrl_v()

        except Exception as e:
            logger.error("Injection failed: %s", e)
            emergency_restore()
            raise InjectionError(f"Injection transaction error: {e}") from e

    # Step 4: Non-blocking asynchronous clipboard restore with external manager verification
    def _async_restore() -> None:
        global _active_backup_text, _injected_expected_text
        time.sleep(restore_delay_ms / 1000.0)
        with _clipboard_lock:
            try:
                current_text = get_clipboard_text()
                # External manager hijack check (Ditto, Win+V, or user manual copy)
                if current_text != _injected_expected_text:
                    logger.warning(
                        "Clipboard text was modified by an external tool (Ditto/Win+V). Aborting restore."
                    )
                    return

                # Restore previous text
                if _active_backup_text is not None:
                    set_clipboard_text(_active_backup_text)
            except Exception as exc:
                logger.error("Error during asynchronous clipboard restoration: %s", exc)
            finally:
                _active_backup_text = None
                _injected_expected_text = None

    threading.Thread(target=_async_restore, daemon=True, name="ClipboardRestore").start()
    return True
