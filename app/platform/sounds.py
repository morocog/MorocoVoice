"""Procedural in-memory WAV sound synthesis and playback for VoiceFlow-Win.

Generates blip/pop auditory cues entirely in memory without relying on disk I/O,
and plays them asynchronously using winsound to prevent UI or audio capture blocking.
"""

from __future__ import annotations

import math
import struct
import winsound

from app.logging_setup import get_logger

logger = get_logger("sounds")


def generate_wav_bytes(
    freq_start: float,
    freq_end: float,
    duration_s: float,
    sample_rate: int = 44100,
    volume: float = 0.3,
) -> bytes:
    """Synthesize an in-memory 16-bit PCM mono RIFF WAV byte string with frequency chirp."""
    num_samples = int(sample_rate * duration_s)
    raw_samples = bytearray()

    # Linear frequency chirp
    for i in range(num_samples):
        t = i / sample_rate
        progress = i / max(1, num_samples - 1)
        freq = freq_start + (freq_end - freq_start) * progress

        # Envelope window: 10% attack, 20% sustain, 70% decay
        if progress < 0.1:
            env = progress / 0.1
        elif progress > 0.3:
            env = max(0.0, 1.0 - (progress - 0.3) / 0.7)
        else:
            env = 1.0

        sample_val = int(32767.0 * volume * env * math.sin(2.0 * math.pi * freq * t))
        sample_val = max(-32768, min(32767, sample_val))
        raw_samples.extend(struct.pack("<h", sample_val))

    # Construct RIFF WAVE header
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = len(raw_samples)
    riff_chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        riff_chunk_size,
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size for PCM
        1,   # AudioFormat (1 = PCM)
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + bytes(raw_samples)


# Pre-generate sound buffers in memory at module load time
try:
    _BLIP_BYTES: bytes | None = generate_wav_bytes(
        freq_start=880.0, freq_end=1320.0, duration_s=0.08, sample_rate=44100, volume=0.25
    )
    _POP_BYTES: bytes | None = generate_wav_bytes(
        freq_start=600.0, freq_end=300.0, duration_s=0.07, sample_rate=44100, volume=0.20
    )
except Exception as e:
    logger.error("Failed to pre-synthesize auditory cues: %s", e)
    _BLIP_BYTES = None
    _POP_BYTES = None


def play_sound_blip() -> None:
    """Play start-of-recording auditory cue asynchronously."""
    if _BLIP_BYTES is None:
        return
    try:
        winsound.PlaySound(_BLIP_BYTES, winsound.SND_MEMORY | winsound.SND_ASYNC)
    except Exception as e:
        logger.warning("winsound PlaySound blip error: %s", e)


def play_sound_pop() -> None:
    """Play end-of-recording auditory cue asynchronously."""
    if _POP_BYTES is None:
        return
    try:
        winsound.PlaySound(_POP_BYTES, winsound.SND_MEMORY | winsound.SND_ASYNC)
    except Exception as e:
        logger.warning("winsound PlaySound pop error: %s", e)
