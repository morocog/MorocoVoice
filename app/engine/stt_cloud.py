"""In-memory Cloud Speech-to-Text connector using Groq whisper-large-v3.

Delivers Wispr Flow parity with sub-500ms transcription latency via in-memory WAV buffers.
"""

from __future__ import annotations

import struct
import time

import numpy as np
from groq import Groq

from app.contracts import AudioEngineType, InferenceError, TranscriptionResult
from app.logging_setup import get_logger

logger = get_logger("stt_cloud")


def numpy_to_wav_bytes(audio_data: np.ndarray, sample_rate: int = 16000) -> bytes:
    """Encode 1D float32 numpy audio array into an in-memory 16-bit PCM WAV byte buffer."""
    if audio_data.ndim > 1:
        audio_data = audio_data.squeeze()

    # Clip and scale float32 (-1.0 to 1.0) to int16 (-32768 to 32767)
    clipped = np.clip(audio_data, -1.0, 1.0)
    pcm_16 = (clipped * 32767.0).astype(np.int16)
    raw_data = pcm_16.tobytes()

    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = len(raw_data)
    riff_chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        riff_chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + raw_data


class CloudGroqWhisperEngine:
    """Cloud STT engine backed by Groq whisper-large-v3."""

    def __init__(self, api_key: str, model: str = "whisper-large-v3", language: str = "es") -> None:
        self.api_key = api_key
        self.model = model
        self.language = language
        self._client: Groq | None = None

    def _get_client(self) -> Groq:
        """Lazy initialization of the Groq API client with 15s timeout."""
        if self._client is None:
            if not self.api_key:
                raise InferenceError("GROQ_API_KEY is not configured for Cloud STT.")
            self._client = Groq(api_key=self.api_key, timeout=15.0)
        return self._client

    def transcribe(
        self, audio_data: np.ndarray, initial_prompt: str | None = None
    ) -> TranscriptionResult:
        """Transcribe audio via Groq Whisper API entirely in memory."""
        if len(audio_data) == 0:
            return TranscriptionResult(
                text="", language=self.language, duration_ms=0.0, confidence=1.0, engine=AudioEngineType.CLOUD
            )

        t0 = time.perf_counter()
        try:
            client = self._get_client()
            wav_bytes = numpy_to_wav_bytes(audio_data, sample_rate=16000)
            audio_file = ("audio.wav", wav_bytes)

            kwargs = {
                "file": audio_file,
                "model": self.model,
                "language": self.language,
                "response_format": "verbose_json",
            }
            if initial_prompt:
                kwargs["prompt"] = initial_prompt

            transcription = client.audio.transcriptions.create(**kwargs)

            text = getattr(transcription, "text", "") or ""
            language = getattr(transcription, "language", "es") or "es"
            duration_ms = (time.perf_counter() - t0) * 1000.0

            logger.info(
                "Cloud Groq transcription completed. Duration: %.2f ms, Characters: %d",
                duration_ms,
                len(text),
            )

            return TranscriptionResult(
                text=text.strip(),
                language=language,
                duration_ms=duration_ms,
                confidence=1.0,
                engine=AudioEngineType.CLOUD,
            )
        except Exception as e:
            logger.error("Cloud Groq transcription error: %s", e)
            raise InferenceError(f"Cloud STT failure: {e}") from e
