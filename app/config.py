"""Configuration loader and validator for MorocoVoice.

Loads JSON configuration and environment variables into an immutable AppConfig.
Tolerates unknown configuration keys by emitting a warning to maintain forward compatibility.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Any

from app.contracts import AppConfig, AudioEngineType
from app.logging_setup import get_logger

logger = get_logger("config")


def load_env_file(env_path: Path) -> None:
    """Lightweight .env parser without external dependencies."""
    if not env_path.exists():
        return
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("\"'")
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception as e:
        logger.warning("Failed to parse .env file at %s: %s", env_path, e)


def is_valid_groq_api_key(key: str | None) -> bool:
    """Validate that key is not an empty string or standard documentation placeholder."""
    cleaned = (key or "").strip()
    if not cleaned:
        return False
    if cleaned.startswith("gsk_tu_clave") or "placeholder" in cleaned.lower():
        return False
    return cleaned.startswith("gsk_") and len(cleaned) >= 20


def load_config(config_path: str | Path = "config.json") -> AppConfig:
    """Load configuration from JSON and environment into an immutable AppConfig."""
    cfg_file = Path(config_path)
    env_file = cfg_file.parent / ".env" if cfg_file.is_file() else Path(".env")
    load_env_file(env_file)

    base_config = AppConfig()
    config_dict: dict[str, Any] = {}

    if cfg_file.exists():
        try:
            with open(cfg_file, encoding="utf-8") as f:
                loaded_raw = json.load(f)
                if isinstance(loaded_raw, dict):
                    config_dict = loaded_raw
        except Exception as e:
            logger.error("Error reading configuration file %s: %s. Using default configuration.", cfg_file, e)

    # Filter recognized vs unknown keys
    valid_fields = {f.name for f in dataclasses.fields(AppConfig)}
    recognized_updates: dict[str, Any] = {}

    for key, val in config_dict.items():
        if key in valid_fields:
            if key == "engine" and isinstance(val, str):
                try:
                    recognized_updates[key] = AudioEngineType(val.upper())
                except ValueError:
                    logger.warning("Invalid engine type '%s' in config; using default.", val)
            else:
                recognized_updates[key] = val
        else:
            logger.warning("Ignoring unknown configuration key '%s' for forward compatibility.", key)

    # Environment variable overrides
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_api_key:
        if is_valid_groq_api_key(groq_api_key):
            recognized_updates["groq_api_key"] = groq_api_key
        else:
            logger.warning("GROQ_API_KEY contains placeholder or invalid format. Ignoring.")
            recognized_updates["groq_api_key"] = ""

    ollama_url = os.getenv("OLLAMA_BASE_URL", "").strip()
    if ollama_url:
        recognized_updates["ollama_url"] = ollama_url

    # Auto-select engine if API key is present or absent
    has_real_key = bool(recognized_updates.get("groq_api_key"))
    if "engine" not in recognized_updates:
        recognized_updates["engine"] = AudioEngineType.CLOUD if has_real_key else AudioEngineType.LOCAL
    elif recognized_updates.get("engine") == AudioEngineType.CLOUD and not has_real_key:
        logger.warning("CLOUD engine selected but no valid GROQ_API_KEY available. Setting LOCAL engine fallback.")
        recognized_updates["engine"] = AudioEngineType.LOCAL

    try:
        final_config = dataclasses.replace(base_config, **recognized_updates)
    except Exception as e:
        logger.error("Failed to construct AppConfig: %s. Reverting to base defaults.", e)
        final_config = base_config

    logger.info("Configuration loaded successfully. Engine: %s", final_config.engine.value)
    return final_config
