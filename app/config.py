"""Configuration loader, validator, and persistence helpers for MorocoVoice.

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


def load_env_file(env_path: Path, override: bool = False) -> None:
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
                    if key and (override or key not in os.environ):
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


def persist_groq_api_key_to_env(env_path: Path, api_key: str) -> None:
    """Safely persist or update GROQ_API_KEY in .env file without destroying other variables."""
    lines: list[str] = []
    key_found = False
    if env_path.exists():
        try:
            with open(env_path, encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logger.warning("Could not read existing .env: %s", e)

    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("GROQ_API_KEY=") or stripped.startswith("GROQ_API_KEY ="):
            new_lines.append(f"GROQ_API_KEY={api_key}\n")
            key_found = True
        else:
            new_lines.append(line)

    if not key_found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"GROQ_API_KEY={api_key}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        logger.info("GROQ_API_KEY persisted securely to .env")
    except Exception as e:
        logger.error("Failed to write GROQ_API_KEY to %s: %s", env_path, e)


def verify_groq_api_key_online(api_key: str, timeout: float = 2.5) -> tuple[bool, str]:
    """Verify Groq API key by attempting to fetch model list with short timeout and no retries."""
    try:
        from groq import Groq

        client = Groq(api_key=api_key, timeout=timeout, max_retries=0)
        client.models.list()
        return True, "Clave válida y autorizada."
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "invalid_api_key" in err_msg.lower() or "unauthorized" in err_msg.lower():
            return False, "La clave de Groq es inválida o fue revocada (código 401)."
        if (
            "connection" in err_msg.lower()
            or "timeout" in err_msg.lower()
            or "429" in err_msg
            or "500" in err_msg
            or "503" in err_msg
        ):
            return (
                True,
                "No se pudo verificar la conexión en este momento (sin internet o servicio ocupado), pero la clave se guardó.",
            )
        return False, "No se pudo validar la clave con el servidor de Groq."


def load_config(config_path: str | Path = "config.json") -> AppConfig:
    """Load configuration from JSON and environment into an immutable AppConfig."""
    cfg_file = Path(config_path)
    env_file = cfg_file.parent / ".env" if cfg_file.is_file() else Path(".env")
    load_env_file(env_file, override=env_file.is_file())

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
