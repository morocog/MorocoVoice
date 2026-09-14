"""Unit tests for prompt construction, guardrail templates, and LLM fast-path fallbacks."""

from app.contracts import AppConfig
from app.llm.prompt_templates import (
    DICTATION_SYSTEM_PROMPT,
    REWRITE_SYSTEM_PROMPT,
    build_dictation_prompt,
    build_rewrite_prompt,
)
from app.llm.rewriter import SemanticRewriter


def test_guardrail_present_in_prompts():
    """Verify strict anti-conversational guardrails are included in system prompts."""
    assert "CRITICAL OUTPUT RULES" in DICTATION_SYSTEM_PROMPT
    assert "DO NOT include any introductory or concluding chatter" in DICTATION_SYSTEM_PROMPT
    assert "CRITICAL OUTPUT RULES" in REWRITE_SYSTEM_PROMPT


def test_prompt_builder_includes_app_context():
    """Verify application-specific guidance is injected into user prompts."""
    dict_prompt = build_dictation_prompt("esto es una prueba", "outlook.exe")
    assert "outlook.exe" in dict_prompt
    assert "email" in dict_prompt.lower()

    rewrite_prompt = build_rewrite_prompt("def foo():", "code.exe")
    assert "code.exe" in rewrite_prompt
    assert "code" in rewrite_prompt.lower()


def test_fast_path_when_unconfigured():
    """Verify rewriter returns raw transcript unchanged when no LLM is configured (fast-path)."""
    cfg = AppConfig(groq_api_key="", ollama_url="http://127.0.0.1:99999")
    rewriter = SemanticRewriter(cfg)

    raw_text = "hola esto es una prueba de dictado directo"
    result = rewriter.refine_dictation(raw_text, "notepad.exe")
    assert result == raw_text
