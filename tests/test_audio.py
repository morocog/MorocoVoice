"""Unit tests for VAD detection, software RMS fallback, and recorder buffers."""

import numpy as np

from app.audio.vad import VoiceActivityDetector
from app.contracts import VADMode


def test_vad_rms_silence_detection():
    """Verify RMS fallback identifies pure silence as non-speech."""
    vad = VoiceActivityDetector(rms_threshold=0.015)
    silence = np.zeros(512, dtype=np.float32)
    assert not vad.is_speech_chunk(silence)


def test_vad_rms_tone_detection():
    """Verify RMS fallback identifies loud sinusoidal tone as speech."""
    vad = VoiceActivityDetector(rms_threshold=0.015)
    t = np.linspace(0, 512 / 16000, 512, endpoint=False)
    # Amplitude 0.5 is far above 0.015 threshold
    tone = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    assert vad._is_speech_rms(tone)


def test_vad_reset_and_modes():
    """Verify reset handles internal tensors and mode returns valid enum."""
    vad = VoiceActivityDetector()
    vad.reset()
    assert vad.get_mode() in (VADMode.SILERO, VADMode.RMS)


def test_empty_audio_chunk():
    """Verify empty numpy array does not crash VAD."""
    vad = VoiceActivityDetector()
    empty = np.array([], dtype=np.float32)
    assert not vad.is_speech_chunk(empty)


def test_audio_recorder_speech_detection_tracking():
    """Verify AudioRecorder speech chunk tracking and has_detected_speech method."""
    import time
    from unittest.mock import MagicMock

    from app.audio.recorder import AudioRecorder

    vad = MagicMock()
    rec = AudioRecorder(sample_rate=16000, block_size=512, vad=vad, silence_cutoff_seconds=0.5)
    rec._is_recording = True
    rec._start_time = time.perf_counter()

    # 1. Feed silence chunk (VAD returns False)
    vad.is_speech_chunk.return_value = False
    chunk1 = np.zeros((512, 1), dtype=np.float32)
    rec._audio_callback(chunk1, 512, None, None)
    assert not rec.has_detected_speech()

    # 2. Feed speech chunk (VAD returns True)
    vad.is_speech_chunk.return_value = True
    chunk2 = np.ones((512, 1), dtype=np.float32)
    rec._audio_callback(chunk2, 512, None, None)
    assert rec.has_detected_speech()


def test_pii_safe_filter_redacts_formatted_args():
    """Verify PIISafeFilter redacts messages even when sensitive terms are passed via record.args."""
    import logging

    from app.logging_setup import PIISafeFilter

    f = PIISafeFilter()

    # Case 1: Raw payload in message string
    record1 = logging.LogRecord("test", logging.INFO, "path", 10, "Payload: 'transcription': 'secret'", (), None)
    f.filter(record1)
    assert record1.msg == "[REDACTED_PII_PAYLOAD]"

    # Case 2: Sensitive payload in record.args
    record2 = logging.LogRecord("test", logging.INFO, "path", 10, "Result text: '%s' -> '%s'", ("text", "replaced"), None)
    f.filter(record2)
    assert record2.msg == "[REDACTED_PII_PAYLOAD]"
    assert record2.args == ()
