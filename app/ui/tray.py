"""System tray icon subsystem using pystray in a dedicated background thread.

Ensures non-blocking execution alongside Tkinter main loop with thread-safe callbacks.
"""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw

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
    ) -> None:
        self.root = root
        self.on_shutdown = on_shutdown
        self.on_open_settings = on_open_settings
        self.engine_type = engine_type
        self.vad_mode = vad_mode
        self.hotkey_dictation = hotkey_dictation

        self.icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Launch the system tray icon loop inside a daemon thread."""
        image = create_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("VoiceFlow-Win v3.4.1", None, enabled=False),
            pystray.MenuItem(self._get_engine_label, None, enabled=False),
            pystray.MenuItem(self._get_vad_label, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙️ Configuración...", self._on_settings_clicked),
            pystray.MenuItem("Abrir Logs (Ctrl+Shift+D)", self._on_open_logs),
            pystray.MenuItem("Salir (Ctrl+Shift+Q)", self._on_exit_clicked),
        )

        self.icon = pystray.Icon(
            name="VoiceFlow-Win",
            icon=image,
            title=f"VoiceFlow-Win: Dictado ({self.hotkey_dictation})",
            menu=menu,
        )

        self._thread = threading.Thread(target=self.icon.run, daemon=True, name="TrayThread")
        self._thread.start()
        logger.info("System tray icon started in daemon thread.")

        def _send_welcome_toast() -> None:
            import time
            time.sleep(1.0)
            if self.icon:
                try:
                    self.icon.notify(
                        title="VoiceFlow-Win Activo 🎙️",
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
            self.icon.title = f"VoiceFlow-Win: Dictado ({self.hotkey_dictation})"
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
