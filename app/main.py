"""Main runtime orchestrator for VoiceFlow-Win.

Initializes Per-Monitor DPI Awareness v2 before importing Tkinter,
enforces single-instance Win32 Mutex, orchestrates staggered warm-up,
and executes graceful shutdown_ordered with safety watchdogs.
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
import tkinter as tk
from ctypes import wintypes

# CRITICAL DPI AWARENESS: Must execute before any Tkinter / UI imports
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

from app.audio.recorder import AudioRecorder
from app.audio.vad import VoiceActivityDetector
from app.config import load_config
from app.contracts import AppConfig, AppState
from app.engine.engine_manager import EngineManager
from app.llm.context import (
    get_foreground_app_info,
    get_selected_text,
    is_current_process_elevated,
)
from app.llm.rewriter import SemanticRewriter
from app.logging_setup import open_log_in_notepad, setup_logging
from app.platform.hotkey import HotkeyListener
from app.platform.injector import emergency_restore, inject_text
from app.platform.sounds import play_sound_blip, play_sound_pop
from app.ui.hud import FloatingHUD
from app.ui.settings_window import SettingsModal
from app.ui.tray import SystemTrayManager

logger = setup_logging()

# Win32 Mutex Constants
ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "Global\\VoiceFlowWin_SingleInstance_Mutex"


class VoiceFlowApplication:
    """Central controller coordinating audio capture, VAD, STT, LLM, HUD and injection."""

    def __init__(self, root: tk.Tk, config: AppConfig) -> None:
        self.root = root
        self.config = config
        self._mutex_handle: wintypes.HANDLE | None = None
        self._is_shutting_down = False
        self._worker_lock = threading.Lock()
        self._active_job_id = 0

        # Subsystems
        self.hud = FloatingHUD(root, bottom_margin_px=config.hud_bottom_margin_px)
        self.vad = VoiceActivityDetector(
            speech_threshold=0.5, rms_threshold=config.energy_rms_threshold
        )
        self.recorder = AudioRecorder(
            sample_rate=config.sample_rate,
            vad=self.vad,
            max_duration_seconds=config.max_recording_seconds,
            on_max_duration_reached=self._on_max_recording_reached,
        )
        self.engine_mgr = EngineManager(config)
        self.rewriter = SemanticRewriter(config)
        self.settings_modal = SettingsModal(
            parent=self.root,
            current_config=self.config,
            config_file_path="config.json",
            on_saved=self.reload_config,
        )
        self.tray = SystemTrayManager(
            root=self.root,
            on_shutdown=self.shutdown_ordered,
            on_open_settings=self.open_settings,
            engine_type=config.engine,
            vad_mode=self.vad.get_mode(),
        )
        self.hotkeys = HotkeyListener(
            hotkey_dictation=config.hotkey_dictation,
            hotkey_rewrite=config.hotkey_rewrite,
            hotkey_shutdown=config.hotkey_shutdown,
            hotkey_diagnostics=config.hotkey_diagnostics,
            on_dictate_toggle=self.toggle_dictation,
            on_rewrite_trigger=self.trigger_rewrite,
            on_shutdown_trigger=self.shutdown_ordered,
            on_diagnostics_trigger=self.trigger_diagnostics,
        )

    def open_settings(self) -> None:
        """Display the visual settings modal."""
        self.settings_modal.show()

    def reload_config(self, new_config: AppConfig) -> None:
        """Live hot reload of runtime configuration without restarting."""
        self.config = new_config
        self.hotkeys.update_shortcuts(
            dictation=new_config.hotkey_dictation,
            rewrite=new_config.hotkey_rewrite,
            shutdown=new_config.hotkey_shutdown,
            diagnostics=new_config.hotkey_diagnostics,
        )
        self.engine_mgr = EngineManager(new_config)
        self.rewriter = SemanticRewriter(new_config)
        self.tray.update_status(new_config.engine, self.vad.get_mode())
        logger.info("Configuration hot-reloaded successfully in live runtime.")

    def enforce_single_instance(self) -> bool:
        """Enforce single instance execution via Win32 Named Mutex."""
        # # VERIFY: CreateMutexW to prevent duplicate overlapping instances
        handle = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
        last_err = ctypes.windll.kernel32.GetLastError()
        if last_err == ERROR_ALREADY_EXISTS:
            logger.warning("Another instance of VoiceFlow-Win is already running. Exiting.")
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
            return False
        self._mutex_handle = handle
        return True

    def start(self) -> None:
        """Perform staggered warm-up and start listener threads."""
        logger.info("Starting VoiceFlow-Win runtime...")

        # Level 1 Warm-up (blocking 2-5s if local)
        self.engine_mgr.warm_up()

        # Level 2 Warm-up (background LLM probe)
        self.rewriter.start_warmup()

        # Start tray and hotkey listeners
        self.tray.start()
        self.hotkeys.start()
        logger.info("VoiceFlow-Win is live and ready.")

    def toggle_dictation(self) -> None:
        """Toggle recording state on Alt+Space press."""
        if self._is_shutting_down:
            return

        if self.recorder.is_recording:
            # Stop recording and process
            play_sound_pop()
            self._dispatch_hud(AppState.PROCESSING, "Procesando audio...")
            audio_buffer = self.recorder.stop()
            self._enqueue_processing(audio_buffer)
        else:
            # Check UIPI elevation of target window before starting
            app_name, pid, is_target_elev = get_foreground_app_info()
            if is_target_elev and not is_current_process_elevated():
                logger.warning("Target app %s is elevated. UIPI prevents injection.", app_name)
                self._dispatch_uipi_alert()
                return

            play_sound_blip()
            self._dispatch_hud(AppState.RECORDING, "Escuchando...")
            try:
                self.recorder.start()
            except Exception as e:
                logger.error("Failed to start audio recording: %s", e)
                self._dispatch_hud(AppState.ERROR, "Error de Micrófono")
                self.root.after(2000, self.hud.hide)

    def _on_max_recording_reached(self) -> None:
        """Callback when recording hits 60s hard limit."""
        logger.info("Auto-cutoff reached. Stopping recording.")
        play_sound_pop()
        self._dispatch_hud(AppState.PROCESSING, "Procesando (60s límite)...")
        audio_buffer = self.recorder.stop()
        self._enqueue_processing(audio_buffer)

    def _enqueue_processing(self, audio_buffer) -> None:
        """Queue worker thread for STT and text injection with LIFO replacement policy."""
        with self._worker_lock:
            self._active_job_id += 1
            current_job = self._active_job_id

        def _worker() -> None:
            if len(audio_buffer) == 0:
                self.root.after(0, self.hud.hide)
                return

            # Step 1: STT
            try:
                transcription = self.engine_mgr.transcribe(audio_buffer)
            except Exception as e:
                logger.error("Transcription error in worker: %s", e)
                self._dispatch_hud(AppState.ERROR, "Error en Transcripción")
                self.root.after(2000, self.hud.hide)
                return

            # Check if canceled by newer job
            with self._worker_lock:
                if current_job != self._active_job_id:
                    logger.info("Discarding stale job %d in favor of newer request.", current_job)
                    return

            raw_text = transcription.text.strip()
            if not raw_text:
                logger.info("No speech detected or output suppressed by hallucination filter.")
                self.root.after(0, self.hud.hide)
                return

            # Step 2: Contextual Semantic Refinement
            app_name, _, _ = get_foreground_app_info()
            refined_text = self.rewriter.refine_dictation(raw_text, app_name)

            # Step 3: Injection
            self._dispatch_hud(AppState.INJECTING, "Escribiendo...")
            try:
                inject_text(refined_text, restore_delay_ms=self.config.clipboard_restore_delay_ms)
            except Exception as e:
                logger.error("Injection error: %s", e)
                self._dispatch_hud(AppState.ERROR, "Error al Inyectar")
                self.root.after(2000, self.hud.hide)
                return

            # Complete and hide HUD
            time.sleep(0.4)
            self.root.after(0, self.hud.hide)

        threading.Thread(target=_worker, daemon=True, name="AudioWorker").start()

    def trigger_rewrite(self) -> None:
        """Process contextual rewrite on Ctrl+Shift+Space."""
        if self._is_shutting_down:
            return

        app_name, pid, is_target_elev = get_foreground_app_info()
        if is_target_elev and not is_current_process_elevated():
            logger.warning("Target app %s is elevated. UIPI prevents rewrite.", app_name)
            self._dispatch_uipi_alert()
            return

        selected_text = get_selected_text()
        if not selected_text:
            logger.info("No text was selected for contextual rewrite.")
            return

        play_sound_blip()
        self._dispatch_hud(AppState.PROCESSING, "Reescribiendo...")

        def _rewrite_worker() -> None:
            res = self.rewriter.rewrite_selection(selected_text, app_name)
            if res.success and res.rewritten_text:
                self._dispatch_hud(AppState.INJECTING, "Reemplazando...")
                play_sound_pop()
                inject_text(res.rewritten_text, restore_delay_ms=self.config.clipboard_restore_delay_ms)
                time.sleep(0.4)
                self.root.after(0, self.hud.hide)
            else:
                self._dispatch_hud(AppState.ERROR, "Error al Reescribir")
                self.root.after(2000, self.hud.hide)

        threading.Thread(target=_rewrite_worker, daemon=True, name="RewriteWorker").start()

    def trigger_diagnostics(self) -> None:
        """Open log file in Notepad (Ctrl+Shift+D)."""
        open_log_in_notepad()

    def _dispatch_hud(self, state: AppState, text: str) -> None:
        """Thread-safe HUD update routed to Tkinter main thread."""
        self.root.after(0, lambda: self.hud.show(text=text, state=state))

    def _dispatch_uipi_alert(self) -> None:
        """Thread-safe UIPI alert display."""
        self.root.after(0, self.hud.show_uipi_alert)

    def shutdown_ordered(self) -> None:
        """Execute ordered graceful shutdown protocol with 2.0s watchdog."""
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        logger.info("Shutdown protocol initiated.")

        # Watchdog thread: force exit if process hangs after 2.0 seconds
        def _watchdog() -> None:
            time.sleep(2.0)
            logger.warning("Watchdog timer expired (2.0s). Forcing clean process exit.")
            os._exit(0)

        threading.Thread(target=_watchdog, daemon=True, name="ShutdownWatchdog").start()

        # Step 1: Emergency clipboard restoration
        emergency_restore()

        # Step 2: Stop global hotkey listener
        self.hotkeys.stop()

        # Step 3: Stop audio recording
        if self.recorder.is_recording:
            self.recorder.stop()

        # Step 4: Stop tray icon
        self.tray.stop()

        # Step 5: Release Win32 Mutex
        if self._mutex_handle:
            ctypes.windll.kernel32.ReleaseMutex(self._mutex_handle)
            ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
            self._mutex_handle = None

        # Step 6: Quit Tkinter loop
        try:
            self.root.after(0, self.root.quit)
        except Exception:
            pass


def main() -> None:
    """Bootstrap VoiceFlow-Win application."""
    config = load_config()

    root = tk.Tk()
    app = VoiceFlowApplication(root, config)

    if not app.enforce_single_instance():
        sys.exit(0)

    app.start()
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.shutdown_ordered()


if __name__ == "__main__":
    main()
