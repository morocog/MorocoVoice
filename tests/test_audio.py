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
