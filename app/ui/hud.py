"""Translucent draggable non-activating pill HUD overlay for Windows 10/11.

Uses Win32 WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW and MonitorFromPoint to render
an unobtrusive floating capsule with mouse-drag repositioning and auto-dismiss watchdog.
Spotify-inspired dark aesthetic with dynamic DPI-aware sizing and hardware-accelerated rounded corners.
"""

from __future__ import annotations

import ctypes
import tkinter as tk
import tkinter.font as tkfont
from ctypes import wintypes

from app.contracts import AppState
from app.logging_setup import get_logger

logger = get_logger("hud")

# Win32 Constants
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
MONITOR_DEFAULTTONEAREST = 2
GA_ROOT = 2


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class FloatingHUD:
    """Draggable, non-activating, topmost translucent floating HUD with dynamic DPI-aware dimensions."""

    def __init__(self, root: tk.Tk, bottom_margin_px: int = 60) -> None:
        self.root = root
        self.bottom_margin_px = bottom_margin_px
        self.state = AppState.IDLE

        self.width = 280
        self.height = 46
        self._font_tuple = ("Segoe UI", 9, "bold")
        self._label_font: tkfont.Font | None = None

        # Dragging state
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self.custom_x: int | None = None
        self.custom_y: int | None = None
        self._auto_dismiss_timer: str | None = None

        self._build_window()
        self.hide()

    def _build_window(self) -> None:
        """Construct borderless, topmost Tkinter window and configure Win32 styles."""
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.94)
        self.root.configure(bg="#121212")

        # Frame container with Spotify pill / card look
        self.frame = tk.Frame(
            self.root,
            bg="#181818",
            highlightthickness=1,
            highlightbackground="#282828",
            cursor="fleur",
        )
        self.frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Status icon / dot
        self.icon_canvas = tk.Canvas(
            self.frame, width=18, height=18, bg="#181818", highlightthickness=0, cursor="fleur"
        )
        self.icon_canvas.pack(side=tk.LEFT, padx=(12, 6), pady=6)
        self.status_dot = self.icon_canvas.create_oval(2, 2, 16, 16, fill="#EF4444", outline="")

        # Status label
        self.label = tk.Label(
            self.frame,
            text="MorocoVoice",
            font=self._font_tuple,
            fg="#FFFFFF",
            bg="#181818",
            cursor="fleur",
            anchor="w",
        )
        self.label.pack(side=tk.LEFT, padx=(2, 8), pady=6, fill=tk.BOTH, expand=True)

        # Dismiss button "✕"
        self.close_btn = tk.Label(
            self.frame,
            text="✕",
            font=("Segoe UI", 9),
            fg="#727272",
            bg="#181818",
            cursor="hand2",
        )
        self.close_btn.pack(side=tk.RIGHT, padx=(0, 12), pady=6)
        self.close_btn.bind("<Button-1>", lambda e: self.hide())
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.configure(fg="#FFFFFF"))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.configure(fg="#727272"))

        # Enable mouse dragging across all widgets with screen coordinates
        for widget in (self.frame, self.label, self.icon_canvas):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._do_drag)
            widget.bind("<Button-3>", lambda e: self.hide())  # Right-click dismiss

        # Apply Win32 NOACTIVATE, TOOLWINDOW and DWM rounded corner styles
        self.root.update_idletasks()
        self._apply_win32_styles()

    def _start_drag(self, event) -> None:
        """Record initial mouse click offset using root screen coordinates."""
        self._drag_offset_x = event.x_root - self.root.winfo_x()
        self._drag_offset_y = event.y_root - self.root.winfo_y()

    def _do_drag(self, event) -> None:
        """Update window position during mouse drag smoothly."""
        x = event.x_root - self._drag_offset_x
        y = event.y_root - self._drag_offset_y
        self.custom_x = x
        self.custom_y = y
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _apply_win32_styles(self) -> None:
        """Apply WS_EX_NOACTIVATE to prevent stealing focus and request DWM rounded corners."""
        try:
            hwnd_id = self.root.winfo_id()
            hwnd = ctypes.windll.user32.GetAncestor(hwnd_id, GA_ROOT) or ctypes.windll.user32.GetParent(hwnd_id)
            if not hwnd:
                return
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_style = ex_style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)

            # Windows 11 rounded corners preference (DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2)
            round_val = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(round_val), ctypes.sizeof(round_val)
            )
        except Exception as e:
            logger.warning("Could not apply Win32 window styles to HUD: %s", e)

    def _reposition(self) -> None:
        """Position HUD either at user-custom coordinates or centered at bottom of active monitor."""
        if self.custom_x is not None and self.custom_y is not None:
            self.root.geometry(f"{self.width}x{self.height}+{self.custom_x}+{self.custom_y}")
            return

        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))

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
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = (screen_w - self.width) // 2
            y = screen_h - self.height - self.bottom_margin_px

        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def show(
        self,
        text: str = "Escuchando...",
        state: AppState = AppState.RECORDING,
        duration_ms: int | None = None,
    ) -> None:
        """Update display status and reveal HUD with dynamic DPI-aware sizing and single cancellable timer."""
        self.state = state

        # Dynamic width and height calculation to prevent clipping across all DPI scale factors
        if self._label_font is None:
            try:
                self._label_font = tkfont.Font(root=self.root, family="Segoe UI", size=9, weight="bold")
            except Exception:
                self._label_font = None

        if self._label_font is not None:
            try:
                text_width = self._label_font.measure(text)
                linespace = self._label_font.metrics("linespace")
                self.width = max(260, text_width + 88)
                self.height = max(44, linespace + 26)
            except Exception:
                self.width = max(260, len(text) * 9 + 88)
                self.height = 46
        else:
            self.width = max(260, len(text) * 9 + 88)
            self.height = 46

        self._reposition()

        if state == AppState.RECORDING:
            self.icon_canvas.itemconfig(self.status_dot, fill="#EF4444")
            self.label.configure(text=text, fg="#FFFFFF")
        elif state == AppState.PROCESSING:
            self.icon_canvas.itemconfig(self.status_dot, fill="#38BDF8")
            self.label.configure(text=text, fg="#E0F2FE")
        elif state == AppState.INJECTING:
            self.icon_canvas.itemconfig(self.status_dot, fill="#1DB954")
            self.label.configure(text=text, fg="#FFFFFF")
        elif state == AppState.ERROR:
            self.icon_canvas.itemconfig(self.status_dot, fill="#FECA66")
            self.label.configure(text=text, fg="#FEF3C7")
        else:
            self.icon_canvas.itemconfig(self.status_dot, fill="#B3B3B3")
            self.label.configure(text=text, fg="#B3B3B3")

        # Single cancellable auto-dismiss safety watchdog
        if self._auto_dismiss_timer is not None:
            try:
                self.root.after_cancel(self._auto_dismiss_timer)
            except Exception:
                pass
            self._auto_dismiss_timer = None

        if duration_ms is not None:
            timeout_ms = duration_ms
        elif state == AppState.RECORDING:
            timeout_ms = 65000
        elif state == AppState.PROCESSING:
            timeout_ms = 12000
        elif state == AppState.INJECTING:
            timeout_ms = 3500
        elif state == AppState.ERROR:
            timeout_ms = 3500
        else:
            timeout_ms = 4000

        self._auto_dismiss_timer = self.root.after(timeout_ms, self.hide)

        self.root.deiconify()
        self._apply_win32_styles()
        self.root.lift()

    def show_uipi_alert(self) -> None:
        """Display specific warning when target window is elevated as Administrator."""
        self.show(
            text="Ventana de administrador activa (ejecuta MorocoVoice como administrador)",
            state=AppState.ERROR,
            duration_ms=3500,
        )

    def hide(self) -> None:
        """Withdraw HUD window from view."""
        if self._auto_dismiss_timer is not None:
            try:
                self.root.after_cancel(self._auto_dismiss_timer)
            except Exception:
                pass
            self._auto_dismiss_timer = None
        self.root.withdraw()
