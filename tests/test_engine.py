"""Unit tests for EngineManager, hallucination filters, and vocabulary limits."""

import json
from pathlib import Path

from app.engine.engine_manager import MAX_VOCABULARY_TERMS, load_and_truncate_vocabulary
from app.engine.stt_local import detect_repetitive_loops, is_hallucination


def test_vocabulary_truncation(tmp_path: Path):
    """Verify vocabulary loader strictly enforces the 30-term maximum limit."""
    vocab_file = tmp_path / "vocab_test.json"
    # Create 45 dummy terms
    terms = [f"Term_{i}" for i in range(45)]
    vocab_file.write_text(json.dumps(terms), encoding="utf-8")

    prompt = load_and_truncate_vocabulary(vocab_file)
    extracted = [t.strip() for t in prompt.split(",") if t.strip()]

    assert len(extracted) == MAX_VOCABULARY_TERMS
    assert extracted[0] == "Term_0"
    assert extracted[-1] == "Term_29"


def test_hallucination_fuzzy_blocklist():
    """Verify blocklist matches known subtitle credits."""
    assert is_hallucination("Gracias por ver el video!")
    assert is_hallucination("Subtítulos por la comunidad de amara.org")
    assert is_hallucination("Thank you for watching")
    assert not is_hallucination("Por favor agenda la reunión de operaciones a las 4 pm")


def test_repetitive_loop_detection():
    """Verify repetitive n-gram detection flags looping text."""
    # 4 words repeated 3 times
    loop_text = "esto es una prueba esto es una prueba esto es una prueba"
    assert detect_repetitive_loops(loop_text, min_words=4, min_repeats=3)

    normal_text = "El reporte de operaciones y Workforce Management fue completado exitosamente."
    assert not detect_repetitive_loops(normal_text, min_words=4, min_repeats=3)
