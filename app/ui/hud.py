"""Translucent non-activating pill HUD overlay for Windows 10/11.

Uses Win32 WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW and MonitorFromPoint to render
an unobtrusive floating capsule 60px above the bottom of the active monitor.
"""

from __future__ import annotations

import ctypes
import tkinter as tk
from ctypes import wintypes

from app.contracts import AppState
from app.logging_setup import get_logger

logger = get_logger("hud")

# Win32 Constants
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
MONITOR_DEFAULTTONEAREST = 2

# Global DPI awareness initialization flag
_DPI_AWARE_INITIALIZED = False


def init_dpi_awareness() -> None:
    """Set process DPI awareness to Per-Monitor V2 before Tkinter window creation."""
    global _DPI_AWARE_INITIALIZED
    if _DPI_AWARE_INITIALIZED:
        return
    try:
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE_V2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        _DPI_AWARE_INITIALIZED = True
        logger.info("Per-Monitor DPI awareness (v2) successfully set.")
    except Exception as e:
        logger.warning("Could not set DPI awareness: %s", e)


# # VERIFY: RECT structure according to Win32 SDK
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


# # VERIFY: MONITORINFO structure with cbSize initialization
class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class FloatingHUD:
    """Non-activating, topmost translucent floating HUD."""

    def __init__(self, root: tk.Tk, bottom_margin_px: int = 60) -> None:
        self.root = root
        self.bottom_margin_px = bottom_margin_px
        self.state = AppState.IDLE

        self.width = 240
        self.height = 48

        self._build_window()
        self.hide()

    def _build_window(self) -> None:
        """Construct borderless, topmost Tkinter window and configure Win32 styles."""
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#18181b")

        # Frame container with modern capsule look
        self.frame = tk.Frame(
            self.root,
            bg="#27272a",
            highlightthickness=1,
            highlightbackground="#3f3f46",
        )
        self.frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Status icon / dot
        self.icon_canvas = tk.Canvas(
            self.frame, width=20, height=20, bg="#27272a", highlightthickness=0
        )
        self.icon_canvas.pack(side=tk.LEFT, padx=(14, 8), pady=8)
        self.status_dot = self.icon_canvas.create_oval(3, 3, 17, 17, fill="#ef4444", outline="")

        # Status label
        self.label = tk.Label(
            self.frame,
            text="VoiceFlow",
            font=("Segoe UI", 10, "bold"),
            fg="#f4f4f5",
            bg="#27272a",
        )
        self.label.pack(side=tk.LEFT, padx=(0, 14), pady=8)

        # Apply Win32 NOACTIVATE and TOOLWINDOW styles
        self.root.update_idletasks()
        self._apply_win32_styles()

    def _apply_win32_styles(self) -> None:
        """Apply WS_EX_NOACTIVATE to prevent stealing focus from the active foreground app."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            # # VERIFY: GetWindowLongW and SetWindowLongW with GWL_EXSTYLE (-20)
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_style = ex_style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
            logger.info("Win32 WS_EX_NOACTIVATE and WS_EX_TOOLWINDOW applied to HUD hwnd %s.", hex(hwnd))
        except Exception as e:
            logger.warning("Could not apply Win32 window styles to HUD: %s", e)

    def _reposition_to_cursor_monitor(self) -> None:
        """Position HUD horizontally centered 60px above bottom edge of cursor's monitor."""
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))

        # # VERIFY: MonitorFromPoint with MONITOR_DEFAULTTONEAREST (2)
        h_monitor = ctypes.windll.user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)

        if ctypes.windll.user32.GetMonitorInfoW(h_monitor, ctypes.byref(mi)):
            work_rect = mi.rcWork
            mon_left = work_rect.left
            mon_right = work_rect.right
            mon_bottom = work_rect.bottom

            mon_width = mon_right - mon_left
            x = mon_left + (mon_width - self.width) // 2
            y = mon_bottom - self.height - self.bottom_margin_px
        else:
            # Fallback to primary screen info
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = (screen_w - self.width) // 2
            y = screen_h - self.height - self.bottom_margin_px

        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def show(self, text: str = "Escuchando...", state: AppState = AppState.RECORDING) -> None:
        """Update display status and reveal HUD."""
        self.state = state
        self._reposition_to_cursor_monitor()

        if state == AppState.RECORDING:
            self.icon_canvas.itemconfig(self.status_dot, fill="#ef4444")  # Red pulse
            self.label.configure(text=text, fg="#f4f4f5")
        elif state == AppState.PROCESSING:
            self.icon_canvas.itemconfig(self.status_dot, fill="#3b82f6")  # Blue process
            self.label.configure(text=text, fg="#93c5fd")
        elif state == AppState.INJECTING:
            self.icon_canvas.itemconfig(self.status_dot, fill="#10b981")  # Green inject
            self.label.configure(text=text, fg="#a7f3d0")
        elif state == AppState.ERROR:
            self.icon_canvas.itemconfig(self.status_dot, fill="#f59e0b")  # Amber warning
            self.label.configure(text=text, fg="#fde68a")

        self.root.deiconify()
        self.root.lift()

    def show_uipi_alert(self) -> None:
        """Display specific warning when target window is elevated as Administrator."""
        self.show(text="Admin Activo (Ejecuta como Admin)", state=AppState.ERROR)
        self.root.after(3000, self.hide)

    def hide(self) -> None:
        """Withdraw HUD window from view."""
        self.root.withdraw()
