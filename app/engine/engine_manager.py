"""Unified Speech-to-Text Dispatcher with dynamic fallback and vocabulary truncation.

CRITICAL RULE:
custom_vocabulary.json is strictly truncated to a maximum of 30 terms to protect
Whisper Word Error Rate (WER) and prevent prompt bloat.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.contracts import (
    AppConfig,
    AudioEngineType,
    TranscriptionResult,
)
from app.engine.stt_cloud import CloudGroqWhisperEngine
from app.engine.stt_local import LocalWhisperEngine, is_hallucination
from app.logging_setup import get_logger

logger = get_logger("engine_manager")

MAX_VOCABULARY_TERMS = 30


def load_and_truncate_vocabulary(vocab_path: str | Path) -> str:
    """Load vocabulary JSON and truncate strictly to at most 30 terms."""
    path = Path(vocab_path)
    if not path.exists():
        logger.warning("Custom vocabulary file not found at %s. Proceeding with empty prompt.", path)
        return ""

    try:
        with open(path, encoding="utf-8") as f:
            raw_terms = json.load(f)

        if not isinstance(raw_terms, list):
            logger.warning("Vocabulary file did not contain a JSON array. Ignoring.")
            return ""

        # Filter non-empty strings and truncate strictly to 30
        valid_terms = [str(t).strip() for t in raw_terms if str(t).strip()]
        truncated_terms = valid_terms[:MAX_VOCABULARY_TERMS]

        if len(valid_terms) > MAX_VOCABULARY_TERMS:
            logger.info(
                "Custom vocabulary truncated from %d to %d terms for Whisper WER protection.",
                len(valid_terms),
                MAX_VOCABULARY_TERMS,
            )

        prompt_str = ", ".join(truncated_terms)
        logger.info("Vocabulary prompt constructed with %d terms.", len(truncated_terms))
        return prompt_str
    except Exception as e:
        logger.error("Failed to load custom vocabulary: %s", e)
        return ""


class EngineManager:
    """Orchestrates cloud vs. local transcription with automatic failover."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.active_engine = config.engine
        self.initial_prompt = load_and_truncate_vocabulary(config.custom_vocabulary_path)

        # Initialize engines
        self.cloud_engine: CloudGroqWhisperEngine | None = None
        if config.groq_api_key:
            self.cloud_engine = CloudGroqWhisperEngine(
                api_key=config.groq_api_key, model=config.groq_stt_model
            )

        self.local_engine = LocalWhisperEngine(
            model_size=config.local_whisper_model,
            device="cpu",
            compute_type=config.local_compute_type,
        )

    def warm_up(self) -> None:
        """Level 1 Warm-up: Load local Whisper weights if in local mode."""
        if self.active_engine == AudioEngineType.LOCAL or not self.config.groq_api_key:
            logger.info("Initiating Level 1 warm-up for local Whisper model...")
            self.local_engine.initialize()

    def transcribe(self, audio_data: np.ndarray) -> TranscriptionResult:
        """Transcribe audio with cloud-first policy and automatic local fallback."""
        if len(audio_data) == 0:
            return TranscriptionResult(
                text="", language="es", duration_ms=0.0, confidence=1.0, engine=self.active_engine
            )

        # Path 1: Cloud STT (Groq)
        if self.active_engine == AudioEngineType.CLOUD and self.cloud_engine is not None:
            try:
                result = self.cloud_engine.transcribe(audio_data, initial_prompt=self.initial_prompt)
                if not is_hallucination(result.text):
                    return result
                logger.info("Cloud transcription suppressed by hallucination filter.")
                return TranscriptionResult(
                    text="", language=result.language, duration_ms=result.duration_ms, confidence=0.0, engine=AudioEngineType.CLOUD
                )
            except Exception as e:
                logger.warning("Cloud transcription failed: %s. Falling back to local Whisper.", e)

        # Path 2: Local STT Fallback
        logger.info("Executing local faster-whisper transcription fallback...")
        return self.local_engine.transcribe(audio_data, initial_prompt=self.initial_prompt)
