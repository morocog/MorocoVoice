"""Semantic rewriter and formatter supporting Groq Cloud LLM and local Ollama with fast-path fallback.

Operates in fast-path (direct raw text) if LLM is offline or during Level 2 background warm-up.
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request

from groq import Groq

from app.contracts import AppConfig, RewriteResult
from app.llm.prompt_templates import (
    DICTATION_SYSTEM_PROMPT,
    REWRITE_SYSTEM_PROMPT,
    build_dictation_prompt,
    build_rewrite_prompt,
)
from app.logging_setup import get_logger

logger = get_logger("rewriter")


def _clean_llm_response(text: str) -> str:
    """Remove reasoning/thought tags (<think>...</think>) if produced by reasoning models."""
    if "<think>" in text:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


class SemanticRewriter:
    """Dispatches semantic text refinement to Groq or local Ollama with fast-path safety."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.groq_api_key = config.groq_api_key
        self.groq_model = config.groq_llm_model
        self.ollama_url = config.ollama_url.rstrip("/")
        self.ollama_model = config.ollama_model

        self._groq_client: Groq | None = None
        self._ollama_online = False
        self._llm_ready = False
        self._health_check_thread: threading.Thread | None = None

    def start_warmup(self) -> None:
        """Level 2 Warm-up: Probe LLM availability in background thread."""
        def _warmup_worker() -> None:
            logger.info("Level 2 warm-up started in background...")
            if self.groq_api_key:
                try:
                    self._groq_client = Groq(api_key=self.groq_api_key)
                    self._llm_ready = True
                    logger.info("Cloud LLM (Groq %s) ready.", self.groq_model)
                    return
                except Exception as e:
                    logger.warning("Groq LLM initialization warning: %s", e)

            # Probe local Ollama with 500 ms health check
            self._check_ollama_health()
            if self._ollama_online:
                self._llm_ready = True
                logger.info("Local LLM (Ollama %s) ready.", self.ollama_model)
            else:
                logger.info("LLM operating in fast-path (raw direct text) mode.")

        threading.Thread(target=_warmup_worker, daemon=True, name="LLMWarmup").start()

    def _check_ollama_health(self) -> bool:
        """Probe Ollama with 500ms timeout on GET /api/tags."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                if resp.status == 200:
                    self._ollama_online = True
                    return True
        except Exception:
            pass
        self._ollama_online = False
        return False

    def is_llm_available(self) -> bool:
        """Query if an LLM is active and ready."""
        return bool(self.groq_api_key) or self._ollama_online

    def refine_dictation(self, raw_transcript: str, app_name: str) -> str:
        """Format transcribed speech or return raw text if LLM is offline (fast-path)."""
        if not raw_transcript.strip():
            return ""

        # Fast-path check
        if not self.is_llm_available():
            logger.info("LLM offline/unconfigured. Fast-path direct text returned.")
            return raw_transcript

        prompt = build_dictation_prompt(raw_transcript, app_name)
        result = self._call_llm(DICTATION_SYSTEM_PROMPT, prompt)
        return result or raw_transcript

    def rewrite_selection(self, selected_text: str, app_name: str) -> RewriteResult:
        """Contextually polish selected text."""
        t0 = time.perf_counter()
        if not selected_text.strip():
            return RewriteResult(
                original_text="",
                rewritten_text="",
                app_name=app_name,
                duration_ms=0.0,
                success=False,
                error_message="No text selected for rewrite.",
            )

        if not self.is_llm_available():
            return RewriteResult(
                original_text=selected_text,
                rewritten_text=selected_text,
                app_name=app_name,
                duration_ms=0.0,
                success=False,
                error_message="LLM service is offline or not configured.",
            )

        prompt = build_rewrite_prompt(selected_text, app_name)
        rewritten = self._call_llm(REWRITE_SYSTEM_PROMPT, prompt)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        if rewritten:
            return RewriteResult(
                original_text=selected_text,
                rewritten_text=rewritten,
                app_name=app_name,
                duration_ms=duration_ms,
                success=True,
            )
        else:
            return RewriteResult(
                original_text=selected_text,
                rewritten_text=selected_text,
                app_name=app_name,
                duration_ms=duration_ms,
                success=False,
                error_message="LLM inference produced empty result.",
            )

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str | None:
        """Execute inference against Groq or Ollama with automatic model fallback."""
        # 1. Groq Cloud
        if self.groq_api_key:
            try:
                if self._groq_client is None:
                    self._groq_client = Groq(api_key=self.groq_api_key, timeout=15.0)

                prompt_words = len(user_prompt.split())
                dynamic_max_tokens = min(2048, max(500, int(prompt_words * 2.5)))

                # Candidate fallback models if configured model is decommissioned or returns 404/400
                models_to_try = [self.groq_model]
                for fallback_m in ["qwen/qwen3.8-27b", "groq/compound-mini", "qwen/qwen3.6-27b"]:
                    if fallback_m not in models_to_try:
                        models_to_try.append(fallback_m)

                for attempt_model in models_to_try:
                    try:
                        resp = self._groq_client.chat.completions.create(
                            model=attempt_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0.2,
                            max_tokens=dynamic_max_tokens,
                        )
                        raw_choice = resp.choices[0].message.content or ""
                        cleaned_choice = _clean_llm_response(raw_choice)
                        if cleaned_choice:
                            if attempt_model != self.groq_model:
                                logger.info("Groq fallback model '%s' succeeded.", attempt_model)
                            return cleaned_choice
                    except Exception as model_err:
                        err_str = str(model_err)
                        if "404" in err_str or "model_not_found" in err_str or "decommissioned" in err_str:
                            logger.warning(
                                "Groq model '%s' unavailable (%s). Trying fallback model...",
                                attempt_model,
                                err_str,
                            )
                            continue
                        logger.warning("Groq LLM call failed for '%s': %s", attempt_model, model_err)
                        break
            except Exception as e:
                logger.warning("Groq LLM client error: %s", e)

        # 2. Local Ollama
        if self._ollama_online:
            try:
                payload = {
                    "model": self.ollama_model,
                    "system": system_prompt,
                    "prompt": user_prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.ollama_url}/api/generate",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        parsed = json.loads(resp.read().decode("utf-8"))
                        response_text = parsed.get("response", "").strip()
                        return response_text or None
            except Exception as e:
                logger.warning("Ollama LLM call failed: %s", e)

        return None
