"""Local Speech-to-Text engine using faster-whisper with hallucination filtering.

Implements fuzzy blocklist matching (difflib > 0.85) and repetitive n-gram loop detection
to purge Whisper hallucinations (e.g. YouTube subtitles, subtitle credit loops).
"""

from __future__ import annotations

import difflib
import re
import time

import numpy as np
from faster_whisper import WhisperModel

from app.contracts import AudioEngineType, InferenceError, TranscriptionResult
from app.logging_setup import get_logger

logger = get_logger("stt_local")

# Hallucination blocklist phrases
HALLUCINATION_BLOCKLIST: list[str] = [
    "amara.org",
    "gracias por ver el video",
    "gracias por ver",
    "suscríbete al canal",
    "subtítulos por la comunidad de amara.org",
    "subtítulos realizados por",
    "subtítulos creados por",
    "thank you for watching",
    "thanks for watching",
    "please like and subscribe",
    "subscribe to my channel",
    "translated by",
    "subtitles by",
]


def detect_repetitive_loops(text: str, min_words: int = 4, min_repeats: int = 3) -> bool:
    """Detect if an n-gram of >= 4 words repeats >= 3 times sequentially."""
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < min_words * min_repeats:
        return False

    for n in range(min_words, len(words) // min_repeats + 1):
        for i in range(len(words) - n * min_repeats + 1):
            ngram = words[i : i + n]
            pattern_matched = True
            for r in range(1, min_repeats):
                next_slice = words[i + r * n : i + (r + 1) * n]
                if next_slice != ngram:
                    pattern_matched = False
                    break
            if pattern_matched:
                return True
    return False


def is_hallucination(text: str, similarity_threshold: float = 0.85) -> bool:
    """Check if candidate text matches the blocklist via difflib or exhibits repetitive loops."""
    cleaned = text.strip().lower()
    if not cleaned:
        return True

    # 1. Check repetitive loops
    if detect_repetitive_loops(cleaned):
        logger.info("Hallucination detected: repetitive n-gram loop.")
        return True

    # 2. Check fuzzy similarity against known credit blocklist
    for phrase in HALLUCINATION_BLOCKLIST:
        ratio = difflib.SequenceMatcher(None, cleaned, phrase).ratio()
        if ratio >= similarity_threshold:
            logger.info("Hallucination detected: blocklist fuzzy match (ratio=%.2f).", ratio)
            return True

    return False


class LocalWhisperEngine:
    """faster-whisper local engine with int8 CPU / CUDA execution."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: WhisperModel | None = None

    def initialize(self) -> None:
        """Load model weights into memory."""
        if self._model is not None:
            return

        logger.info(
            "Loading faster-whisper model '%s' (device=%s, compute_type=%s)...",
            self.model_size,
            self.device,
            self.compute_type,
        )
        t0 = time.perf_counter()
        try:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=4,
            )
            elapsed = time.perf_counter() - t0
            logger.info("Local Whisper model loaded in %.2f seconds.", elapsed)
        except Exception as e:
            logger.error("Failed to load local Whisper model: %s", e)
            raise InferenceError(f"Local Whisper load failure: {e}") from e

    def transcribe(
        self, audio_data: np.ndarray, initial_prompt: str | None = None
    ) -> TranscriptionResult:
        """Transcribe float32 16kHz audio array."""
        if self._model is None:
            self.initialize()

        if len(audio_data) == 0:
            return TranscriptionResult(
                text="", language="es", duration_ms=0.0, confidence=0.0, engine=AudioEngineType.LOCAL
            )

        t0 = time.perf_counter()
        try:
            assert self._model is not None
            segments, info = self._model.transcribe(
                audio_data,
                beam_size=5,
                language="es",
                initial_prompt=initial_prompt,
                vad_filter=False,  # VAD already handled upstream
            )

            text_segments = [seg.text.strip() for seg in segments]
            full_text = " ".join(text_segments).strip()

            # Apply hallucination filter
            if is_hallucination(full_text):
                logger.info("Transcribed text matched hallucination filter. Suppressing output.")
                full_text = ""

            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.info(
                "Local transcription completed. Duration: %.2f ms, Characters: %d",
                duration_ms,
                len(full_text),
            )

            return TranscriptionResult(
                text=full_text,
                language=info.language or "es",
                duration_ms=duration_ms,
                confidence=info.language_probability,
                engine=AudioEngineType.LOCAL,
            )
        except Exception as e:
            logger.error("Local Whisper transcription error: %s", e)
            raise InferenceError(f"Local STT error: {e}") from e
