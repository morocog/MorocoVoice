"""Unified Speech-to-Text Dispatcher with dynamic fallback and vocabulary truncation.

CRITICAL RULE:
custom_vocabulary.json is strictly truncated to a maximum of 30 terms to protect
Whisper Word Error Rate (WER) and prevent prompt bloat.
"""

from __future__ import annotations

import dataclasses
import difflib
import json
import re
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

KNOWN_PHONETIC_CORRECTIONS: dict[str, str] = {
    "gitcop": "GitHub",
    "git cop": "GitHub",
    "git-cop": "GitHub",
    "git cup": "GitHub",
    "git cub": "GitHub",
    "git cap": "GitHub",
    "githop": "GitHub",
    "githup": "GitHub",
}


def load_raw_vocabulary_terms(vocab_path: str | Path) -> list[str]:
    """Load and filter non-empty vocabulary terms from JSON."""
    path = Path(vocab_path)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            raw_terms = json.load(f)
        if isinstance(raw_terms, list):
            valid = [str(t).strip() for t in raw_terms if str(t).strip()]
            return valid[:MAX_VOCABULARY_TERMS]
    except Exception as e:
        logger.error("Failed to load vocabulary list from %s: %s", path, e)
    return []


def load_and_truncate_vocabulary(vocab_path: str | Path) -> str:
    """Load vocabulary JSON and truncate strictly to at most 30 terms."""
    valid_terms = load_raw_vocabulary_terms(vocab_path)
    if not valid_terms:
        logger.warning("Custom vocabulary empty or missing at %s. Proceeding with empty prompt.", vocab_path)
        return ""

    prompt_str = ", ".join(valid_terms)
    logger.info("Vocabulary prompt constructed with %d terms.", len(valid_terms))
    return prompt_str


def apply_vocabulary_post_processing(
    text: str,
    vocabulary_terms: list[str],
    similarity_threshold: float = 0.85,
) -> str:
    """Post-process transcription to correct phonetic or spelling near-misses against vocabulary."""
    if not text or not text.strip():
        return text

    result = text

    # Step 1: Known hard phonetic homophones
    for error_pattern, target_word in KNOWN_PHONETIC_CORRECTIONS.items():
        pattern = re.compile(rf"\b{re.escape(error_pattern)}\b", re.IGNORECASE)
        result = pattern.sub(target_word, result)

    if not vocabulary_terms:
        return result

    # Step 2: Multi-word terms matching
    multi_word = sorted([t for t in vocabulary_terms if " " in t], key=len, reverse=True)
    for term in multi_word:
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        result = pattern.sub(term, result)

    # Step 3: Single-word fuzzy matching with difflib
    COMMON_STOPWORDS = {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "a", "al",
        "en", "por", "para", "con", "sin", "sobre", "entre", "tras", "este", "esta",
        "estos", "estas", "ese", "esa", "esos", "esas", "que", "cual", "quien", "como",
        "pero", "mas", "sino", "porque", "pues", "muy", "tan", "ya", "no", "si", "bien",
        "mal", "todo", "nada", "algo", "otro", "otra", "otros", "otras", "mismo", "misma",
    }

    single_terms = [t for t in vocabulary_terms if " " not in t and len(t) >= 4]
    tokens = re.findall(r"\w+|[^\w\s]|\s+", result)
    new_tokens = []

    for token in tokens:
        if token.isalnum() and len(token) >= 4 and token.lower() not in COMMON_STOPWORDS:
            matched_term = None
            token_lower = token.lower()

            for term in single_terms:
                if token_lower == term.lower():
                    matched_term = term
                    break

            if not matched_term:
                for term in single_terms:
                    if abs(len(token) - len(term)) <= 2:
                        ratio = difflib.SequenceMatcher(None, token_lower, term.lower()).ratio()
                        if ratio >= similarity_threshold:
                            matched_term = term
                            break

            new_tokens.append(matched_term if matched_term else token)
        else:
            new_tokens.append(token)

    return "".join(new_tokens)


class EngineManager:
    """Orchestrates cloud vs. local transcription with automatic failover."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.active_engine = config.engine
        self.vocabulary_terms = load_raw_vocabulary_terms(config.custom_vocabulary_path)
        self.initial_prompt = ", ".join(self.vocabulary_terms) if self.vocabulary_terms else ""

        # Initialize engines
        self.cloud_engine: CloudGroqWhisperEngine | None = None
        if config.groq_api_key:
            self.cloud_engine = CloudGroqWhisperEngine(
                api_key=config.groq_api_key,
                model=config.groq_stt_model,
                language=config.stt_language,
                sample_rate=config.sample_rate,
            )

        self.local_engine = LocalWhisperEngine(
            model_size=config.local_whisper_model,
            device="cpu",
            compute_type=config.local_compute_type,
            language=config.stt_language,
        )

    def warm_up(self) -> None:
        """Level 1 Warm-up: Load local Whisper weights if in local mode."""
        if self.active_engine == AudioEngineType.LOCAL or not self.config.groq_api_key:
            logger.info("Initiating Level 1 warm-up for local Whisper model...")
            self.local_engine.initialize()

    def transcribe(self, audio_data: np.ndarray) -> TranscriptionResult:
        """Transcribe audio with cloud-first policy, automatic local fallback, and deterministic vocabulary post-processing."""
        if len(audio_data) == 0:
            return TranscriptionResult(
                text="", language=self.config.stt_language, duration_ms=0.0, confidence=1.0, engine=self.active_engine
            )

        raw_result: TranscriptionResult | None = None

        # Path 1: Cloud STT (Groq)
        if self.active_engine == AudioEngineType.CLOUD and self.cloud_engine is not None:
            try:
                candidate = self.cloud_engine.transcribe(audio_data, initial_prompt=self.initial_prompt)
                if not is_hallucination(candidate.text):
                    raw_result = candidate
                else:
                    logger.info("Cloud transcription suppressed by hallucination filter.")
                    return TranscriptionResult(
                        text="", language=candidate.language, duration_ms=candidate.duration_ms, confidence=0.0, engine=AudioEngineType.CLOUD
                    )
            except Exception as e:
                logger.warning("Cloud transcription failed: %s. Falling back to local Whisper.", e)

        # Path 2: Local STT Fallback
        if raw_result is None:
            logger.info("Executing local faster-whisper transcription fallback...")
            raw_result = self.local_engine.transcribe(audio_data, initial_prompt=self.initial_prompt)

        # Path 3: Apply deterministic vocabulary correction
        corrected_text = apply_vocabulary_post_processing(raw_result.text, self.vocabulary_terms)
        if corrected_text != raw_result.text:
            delta = len(corrected_text) - len(raw_result.text)
            logger.info("Vocabulary post-processing applied (%+d char delta).", delta)

        return dataclasses.replace(raw_result, text=corrected_text)

