"""Unit tests for procedural WAV synthesis and RIFF header verification."""

import struct

from app.platform.sounds import generate_wav_bytes, play_sound_blip, play_sound_pop


def test_generate_wav_bytes_riff_header():
    """Verify RIFF and WAVE magic numbers and structural sizes in synthesized audio."""
    sample_rate = 44100
    duration_s = 0.05
    wav_bytes = generate_wav_bytes(
        freq_start=440.0,
        freq_end=880.0,
        duration_s=duration_s,
        sample_rate=sample_rate,
        volume=0.3,
    )

    # Minimum header length is 44 bytes
    assert len(wav_bytes) > 44
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"
    assert wav_bytes[12:16] == b"fmt "
    assert wav_bytes[36:40] == b"data"

    # Unpack format parameters
    fmt_size, audio_format, num_channels, s_rate, byte_rate, block_align, bits = struct.unpack(
        "<IHHIIHH", wav_bytes[16:36]
    )
    assert fmt_size == 16
    assert audio_format == 1  # PCM
    assert num_channels == 1  # Mono
    assert s_rate == sample_rate
    assert bits == 16
    assert block_align == 2
    assert byte_rate == sample_rate * 2

    # Unpack data chunk size
    (data_size,) = struct.unpack("<I", wav_bytes[40:44])
    expected_samples = int(sample_rate * duration_s)
    expected_data_size = expected_samples * 2
    assert data_size == expected_data_size
    assert len(wav_bytes) == 44 + data_size


def test_playback_functions_do_not_crash():
    """Verify blip and pop routines execute safely without throwing unhandled exceptions."""
    try:
        play_sound_blip()
        play_sound_pop()
    except Exception as exc:
        assert False, f"Sound playback raised unexpected exception: {exc}"
