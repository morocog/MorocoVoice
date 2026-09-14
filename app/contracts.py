"""Immutable interfaces, contracts, dataclasses, enums and custom exceptions for VoiceFlow-Win."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class AppState(StrEnum):
    """Operational states of the VoiceFlow-Win runtime."""
    IDLE = "IDLE"
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"
    INJECTING = "INJECTING"
    ERROR = "ERROR"


class AudioEngineType(StrEnum):
    """Supported Speech-To-Text engines."""
    LOCAL = "LOCAL"
    CLOUD = "CLOUD"


class RecordingMode(StrEnum):
    """Dictation vs contextual rewrite modes."""
    DICTATION = "DICTATION"
    REWRITE = "REWRITE"


class VADMode(StrEnum):
    """Voice Activity Detection engines."""
    SILERO = "SILERO"
    RMS = "RMS"


@dataclass(frozen=True)
class AudioChunk:
    """Raw audio chunk emitted by the recorder."""
    data: np.ndarray
    sample_rate: int = 16000
    duration_ms: float = 0.0
    is_speech: bool = False


@dataclass(frozen=True)
class TranscriptionResult:
    """Standard transcription payload."""
    text: str
    language: str
    duration_ms: float
    confidence: float
    engine: AudioEngineType


@dataclass(frozen=True)
class RewriteResult:
    """Contextual rewrite result."""
    original_text: str
    rewritten_text: str
    app_name: str
    duration_ms: float
    success: bool
    error_message: str | None = None


@dataclass(frozen=True)
class SystemMetrics:
    """System status and telemetry snapshot."""
    vram_mb: float
    ram_mb: float
    vad_type: VADMode
    engine: AudioEngineType
    is_elevated: bool


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration."""
    hotkey_dictation: str = "alt+space"
    hotkey_rewrite: str = "ctrl+shift+space"
    hotkey_shutdown: str = ""
    hotkey_diagnostics: str = ""
    engine: AudioEngineType = AudioEngineType.CLOUD
    groq_api_key: str = ""
    groq_stt_model: str = "whisper-large-v3"
    groq_llm_model: str = "llama-3.1-8b-instant"
    local_whisper_model: str = "base"
    local_compute_type: str = "int8"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b"
    max_recording_seconds: int = 60
    clipboard_restore_delay_ms: int = 80
    sample_rate: int = 16000
    hud_bottom_margin_px: int = 60
    custom_vocabulary_path: str = "custom_vocabulary.json"
    silence_threshold_seconds: float = 1.2
    energy_rms_threshold: float = 0.015


class VoiceFlowException(Exception):
    """Base exception for all VoiceFlow-Win errors."""


class AudioCaptureError(VoiceFlowException):
    """Raised when WASAPI audio stream fails or device is inaccessible."""


class InferenceError(VoiceFlowException):
    """Raised when STT or LLM inference fails."""


class InjectionError(VoiceFlowException):
    """Raised when Win32 SendInput or clipboard injection fails."""


class UIPIElevationError(VoiceFlowException):
    """Raised when target window is elevated as Admin and VoiceFlow cannot inject."""


class HardwareCompatibilityError(VoiceFlowException):
    """Raised when required hardware features are missing."""


class VADError(VoiceFlowException):
    """Raised when VAD fails to initialize or process audio."""
