"""System tray icon subsystem using pystray in a dedicated background thread.

Ensures non-blocking execution alongside Tkinter main loop with thread-safe callbacks.
"""

from __future__ import annotations

import ctypes
import threading
import tkinter as tk
from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw

from app import __version__
from app.contracts import AudioEngineType, VADMode
from app.logging_setup import get_logger, open_log_in_notepad

logger = get_logger("tray")


def create_tray_icon_image() -> Image.Image:
    """Procedurally create a high-contrast vibrant 64x64 RGBA system tray icon."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Vibrant Telat Blue solid badge background
    draw.ellipse([2, 2, 62, 62], fill="#3284C6", outline="#FECA66", width=2)

    # Crisp white microphone capsule shape
    draw.rounded_rectangle([25, 14, 39, 36], radius=7, fill="#FFFFFF")

    # Microphone arc / holder in pure white
    draw.arc([18, 22, 46, 42], start=0, end=180, fill="#FFFFFF", width=4)
    # Microphone stem & base in pure white
    draw.line([32, 42, 32, 52], fill="#FFFFFF", width=4)
    draw.line([22, 52, 42, 52], fill="#FFFFFF", width=4)

    return img


def _instrument_pystray() -> None:
    """Make both of pystray's silent Win32 failures visible, and non-fatal.

    1. ``ChangeWindowMessageFilterEx`` - pystray calls it while creating its
       hidden window, purely so an *elevated* process keeps receiving
       WM_TASKBARCREATED after an Explorer restart. On hardened /
       domain-managed machines it can fail with ``WinError 5 (Access Denied)``.
       pystray does not guard it, so the whole tray thread died and the app
       ended up with no tray icon and no way to reach its Settings menu. The
       opt-in is unnecessary for a non-elevated process, so the failure is
       downgraded to a warning instead of being fatal.

    2. ``Shell_NotifyIcon`` - pystray declares it WITHOUT an errcheck, so if
       Windows refuses to add the icon the call fails completely silently and
       ``icon.visible`` still reports True. We attach a reporting errcheck so a
       rejection is logged instead of leaving the user staring at an empty
       notification area.
    """
    try:
        from pystray._util import win32 as pystray_win32
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("pystray win32 backend unavailable, nothing to patch: %s", exc)
        return

    NIM_ADD = 0x00000000

    def _tolerant_errcheck(result, func, arguments):
        if not result:
            try:
                detail = str(ctypes.WinError())
            except Exception:
                detail = "WinError desconocido"
            logger.warning(
                "ChangeWindowMessageFilterEx was denied by Windows (%s). "
                "Continuing without the elevated-explorer-restart opt-in.",
                detail,
            )
        return result

    def _notify_errcheck(result, func, arguments):
        # Only NIM_ADD matters: NIM_DELETE legitimately fails for an icon that
        # was never added, and NIM_MODIFY is a best-effort cosmetic refresh.
        if not result and arguments and arguments[0] == NIM_ADD:
            try:
                detail = str(ctypes.WinError())
            except Exception:
                detail = "WinError desconocido"
            logger.error(
                "Shell_NotifyIcon(NIM_ADD) FAILED (%s). Windows rejected the tray "
                "icon, so it will NOT appear in the notification area. Dictation "
                "still works; use the Settings hotkey (default ctrl+alt+s) instead "
                "of the tray menu. If the notification area is simply hiding the "
                "icon, enable it in Configuracion > Personalizacion > Barra de "
                "tareas > Otros iconos. See docs/TROUBLESHOOTING.md.",
                detail,
            )
        return result

    try:
        pystray_win32.ChangeWindowMessageFilterEx.errcheck = _tolerant_errcheck
        logger.debug("pystray UIPI opt-in failure made non-fatal.")
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Could not relax pystray errcheck: %s", exc)

    try:
        pystray_win32.Shell_NotifyIcon.errcheck = _notify_errcheck
        logger.debug("pystray Shell_NotifyIcon failures will now be reported.")
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Could not instrument Shell_NotifyIcon: %s", exc)


class SystemTrayManager:
    """Manages pystray icon lifecycle in a dedicated thread."""

    def __init__(
        self,
        root: tk.Tk,
        on_shutdown: Callable[[], None],
        on_open_settings: Callable[[], None] | None = None,
        engine_type: AudioEngineType = AudioEngineType.CLOUD,
        vad_mode: VADMode = VADMode.SILERO,
        hotkey_dictation: str = "win+space",
        hotkey_settings: str = "ctrl+alt+s",
    ) -> None:
        self.root = root
        self.on_shutdown = on_shutdown
        self.on_open_settings = on_open_settings
        self.engine_type = engine_type
        self.vad_mode = vad_mode
        self.hotkey_dictation = hotkey_dictation
        self.hotkey_settings = hotkey_settings

        self.icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Launch the system tray icon loop inside a daemon thread."""
        _instrument_pystray()

        image = create_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem(f"MorocoVoice v{__version__}", None, enabled=False),
            pystray.MenuItem(self._get_engine_label, None, enabled=False),
            pystray.MenuItem(self._get_vad_label, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙️ Configuración...", self._on_settings_clicked),
            pystray.MenuItem("Abrir Logs", self._on_open_logs),
            pystray.MenuItem("Salir", self._on_exit_clicked),
        )

        self.icon = pystray.Icon(
            name="MorocoVoice",
            icon=image,
            title=f"MorocoVoice: Dictado ({self.hotkey_dictation})",
            menu=menu,
        )

        def _run_tray() -> None:
            def _on_ready(icon: pystray.Icon) -> None:
                # CRITICAL: pystray only performs its default setup (which sets
                # visible = True) when NO custom setup callback is given. Since we
                # pass one, we must publish the icon ourselves or it never shows.
                try:
                    icon.visible = True
                except Exception as exc:
                    logger.error("Could not publish the tray icon: %s", exc, exc_info=True)
                    return
                logger.info(
                    "System tray icon is now visible in the notification area (visible=%s).",
                    icon.visible,
                )

            try:
                self.icon.run(setup=_on_ready)
            except Exception as exc:
                logger.error(
                    "System tray icon FAILED and is now unavailable (no Settings/Exit "
                    "menu next to the clock). The application keeps working for dictation; "
                    "press %s to open Settings from the keyboard. Cause: %s",
                    self.hotkey_settings,
                    exc,
                    exc_info=True,
                )

        self._thread = threading.Thread(target=_run_tray, daemon=True, name="TrayThread")
        self._thread.start()
        logger.info("System tray icon started in daemon thread.")

        def _send_welcome_toast() -> None:
            import time
            time.sleep(1.0)
            if self.icon:
                try:
                    self.icon.notify(
                        title="MorocoVoice Activo 🎙️",
                        message=f"Presiona {self.hotkey_dictation} para dictar o clic derecho para Configuración.",
                    )
                except Exception:
                    pass

        threading.Thread(target=_send_welcome_toast, daemon=True, name="WelcomeToast").start()

    def _get_engine_label(self, item: pystray.MenuItem) -> str:
        return f"Motor: {self.engine_type.value}"

    def _get_vad_label(self, item: pystray.MenuItem) -> str:
        if self.vad_mode == VADMode.SILERO:
            return "VAD: Silero (ONNX)"
        return "VAD: RMS (degradado)"

    def update_status(self, engine: AudioEngineType, vad: VADMode, hotkey_dictation: str | None = None) -> None:
        """Update displayed menu status labels and shortcuts."""
        self.engine_type = engine
        self.vad_mode = vad
        if hotkey_dictation:
            self.hotkey_dictation = hotkey_dictation
        if self.icon:
            self.icon.title = f"MorocoVoice: Dictado ({self.hotkey_dictation})"
            self.icon.update_menu()

    def _on_settings_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if self.on_open_settings:
            self.root.after(0, self.on_open_settings)

    def _on_open_logs(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        open_log_in_notepad()

    def _on_exit_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        # Tkinter thread-safe dispatch
        self.root.after(0, self.on_shutdown)

    def stop(self) -> None:
        """Stop tray icon."""
        if self.icon:
            try:
                self.icon.stop()
                logger.info("System tray icon stopped.")
            except Exception as e:
                logger.warning("Error stopping tray icon: %s", e)
