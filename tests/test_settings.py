"""Tests for MorocoVoice settings persistence and rebranding."""

from __future__ import annotations

from app.main import MUTEX_NAME, MorocoVoiceApplication, VoiceFlowApplication
from app.ui.settings_window import _persist_groq_api_key_to_env


def test_mutex_name_and_aliases() -> None:
    """Ensure mutex name matches MorocoVoice standard and alias is preserved."""
    assert MUTEX_NAME == "Global\\MorocoVoice_SingleInstance_Mutex"
    assert VoiceFlowApplication is MorocoVoiceApplication


def test_persist_groq_api_key_creates_and_updates(tmp_path) -> None:
    """Ensure _persist_groq_api_key_to_env updates existing key and preserves comments."""
    env_file = tmp_path / ".env"

    # Test 1: Write to non-existent file
    _persist_groq_api_key_to_env(env_file, "gsk_initial123")
    assert env_file.exists()
    content = env_file.read_text(encoding="utf-8")
    assert "GROQ_API_KEY=gsk_initial123" in content

    # Test 2: Update existing key with other variables preserved
    env_file.write_text(
        "# Header comment\nOLLAMA_URL=http://localhost:11434\nGROQ_API_KEY=gsk_initial123\n# Footer comment\n",
        encoding="utf-8",
    )
    _persist_groq_api_key_to_env(env_file, "gsk_updated999")
    updated_content = env_file.read_text(encoding="utf-8")
    assert "GROQ_API_KEY=gsk_updated999" in updated_content
    assert "gsk_initial123" not in updated_content
    assert "# Header comment" in updated_content
    assert "OLLAMA_URL=http://localhost:11434" in updated_content
