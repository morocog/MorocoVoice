"""Continuous WASAPI audio capture subsystem using sounddevice.

Captures mono float32 audio at 16 kHz with automatic timeout cutoff
at max_recording_seconds (60 s) and non-blocking background queue streaming.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

import numpy as np
import sounddevice as sd

from app.audio.vad import VoiceActivityDetector
from app.contracts import AudioCaptureError
from app.logging_setup import get_logger

logger = get_logger("recorder")

SAMPLE_RATE = 16000
BLOCK_SIZE = 512  # 32 ms chunk at 16 kHz


class AudioRecorder:
    """Thread-safe microphone recorder with automatic duration limits."""

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        block_size: int = BLOCK_SIZE,
        max_duration_seconds: float = 60.0,
        vad: VoiceActivityDetector | None = None,
        on_max_duration_reached: Callable[[], None] | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_duration_seconds = max_duration_seconds
        self.vad = vad
        self.on_max_duration_reached = on_max_duration_reached

        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._is_recording = False
        self._start_time = 0.0

    def start(self) -> None:
        """Start non-blocking audio capture stream."""
        with self._lock:
            if self._is_recording:
                logger.warning("Recorder is already capturing audio.")
                return

            self._frames.clear()
            self._is_recording = True
            self._start_time = time.perf_counter()

            if self.vad:
                self.vad.reset()

            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    channels=1,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self._stream.start()
                logger.info("Audio recording stream started at %d Hz.", self.sample_rate)
            except Exception as e:
                self._is_recording = False
                logger.error("Failed to start sounddevice InputStream: %s", e)
                raise AudioCaptureError(f"Microphone stream failure: {e}") from e

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time_info: object, status: sd.CallbackFlags
    ) -> None:
        """Low-latency callback executed in audio driver thread."""
        if status:
            logger.warning("Audio callback status warning: %s", status)

        if not self._is_recording:
            return

        chunk = indata[:, 0].copy()
        with self._lock:
            self._frames.append(chunk)

            # Auto cutoff protection (max 60 seconds)
            elapsed = time.perf_counter() - self._start_time
            if elapsed >= self.max_duration_seconds:
                logger.warning("Maximum recording duration reached (%s s). Triggering cutoff.", self.max_duration_seconds)
                self._is_recording = False
                if self.on_max_duration_reached:
                    threading.Thread(target=self.on_max_duration_reached, daemon=True).start()

    def stop(self) -> np.ndarray:
        """Stop capture stream and return the full recorded float32 audio buffer."""
        with self._lock:
            self._is_recording = False
            stream = self._stream
            self._stream = None

        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as e:
                logger.warning("Error closing audio stream: %s", e)

        with self._lock:
            if not self._frames:
                return np.array([], dtype=np.float32)
            concatenated = np.concatenate(self._frames)
            self._frames.clear()
            duration_s = len(concatenated) / self.sample_rate
            logger.info("Audio capture stopped. Buffer length: %d samples (%.2f s).", len(concatenated), duration_s)
            return concatenated

    @property
    def is_recording(self) -> bool:
        """Query if audio capture is actively running."""
        with self._lock:
            return self._is_recording

    def get_duration(self) -> float:
        """Return elapsed duration of current recording in seconds."""
        with self._lock:
            if not self._is_recording:
                return 0.0
            return time.perf_counter() - self._start_time
