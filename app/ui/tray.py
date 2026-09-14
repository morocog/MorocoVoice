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
    """Procedurally create an attractive 64x64 RGBA system tray icon in memory."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer circle background
    draw.ellipse([4, 4, 60, 60], fill="#1e1e24", outline="#3284c6", width=3)

    # Microphone capsule shape
    draw.rounded_rectangle([26, 16, 38, 38], radius=6, fill="#3284c6")

    # Microphone stand
    draw.arc([20, 24, 44, 42], start=0, end=180, fill="#ffffff", width=3)
    draw.line([32, 42, 32, 50], fill="#ffffff", width=3)
    draw.line([24, 50, 40, 50], fill="#ffffff", width=3)

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
    ) -> None:
        self.root = root
        self.on_shutdown = on_shutdown
        self.on_open_settings = on_open_settings
        self.engine_type = engine_type
        self.vad_mode = vad_mode

        self.icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Launch the system tray icon loop inside a daemon thread."""
        image = create_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("VoiceFlow-Win v0.1.0", None, enabled=False),
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
            title="VoiceFlow-Win: Dictado Inteligente",
            menu=menu,
        )

        self._thread = threading.Thread(target=self.icon.run, daemon=True, name="TrayThread")
        self._thread.start()
        logger.info("System tray icon started in daemon thread.")

    def _get_engine_label(self, item: pystray.MenuItem) -> str:
        return f"Motor: {self.engine_type.value}"

    def _get_vad_label(self, item: pystray.MenuItem) -> str:
        if self.vad_mode == VADMode.SILERO:
            return "VAD: Silero (ONNX)"
        return "VAD: RMS (degradado)"

    def update_status(self, engine: AudioEngineType, vad: VADMode) -> None:
        """Update displayed menu status labels."""
        self.engine_type = engine
        self.vad_mode = vad
        if self.icon:
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
