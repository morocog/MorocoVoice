"""Prompt templates and strict anti-conversational guardrails for LLM refinement.

Prevents conversational chatter, preamble ("Here is your text:"), or explanation.
Directs the model to output ONLY the clean, formatted replacement text.
"""

from __future__ import annotations

# Application-specific tone and formatting hints
APP_HINTS: dict[str, str] = {
    "code.exe": "Technical and concise. Preserve code syntax, variable names, and programming terms.",
    "devenv.exe": "Technical, precise, software engineering context.",
    "windowsterminal.exe": "Terminal / CLI command context.",
    "powershell.exe": "PowerShell command context.",
    "outlook.exe": "Executive, polished, formal business email tone.",
    "teams.exe": "Professional, direct workplace communication.",
    "slack.exe": "Clear, modern, friendly workplace collaboration.",
    "winword.exe": "Formal document style with immaculate grammar and punctuation.",
    "excel.exe": "Concise tabular labels or formulas.",
    "notepad.exe": "Clean plain text with natural punctuation.",
}


ANTI_CONVERSATION_GUARDRAIL = """
CRITICAL OUTPUT RULES:
1. Output ONLY the resulting text.
2. Absolutely DO NOT include any introductory or concluding chatter (NO "Here is the text:", NO "Sure!", NO "Output:").
3. DO NOT wrap the output in quotes or markdown code blocks unless the original requested code formatting.
4. Maintain the language of the input (Spanish or English).
"""

DICTATION_SYSTEM_PROMPT = f"""You are MorocoVoice Semantic Formatter.
Your task is to transform spoken transcriptions into clean, natural, and properly punctuated written text.
Remove filler sounds and speech disfluencies (e.g., "eh", "este", "umm", "bueno", "o sea", "you know").
Apply capitalization and punctuation correctly.
{ANTI_CONVERSATION_GUARDRAIL}
"""

REWRITE_SYSTEM_PROMPT = f"""You are MorocoVoice Contextual Editor.
Your task is to rewrite and polish the user's selected text based on the active application context.
Fix grammar, spelling, typos, and syntax while preserving the author's original meaning and intent.
{ANTI_CONVERSATION_GUARDRAIL}
"""


def build_dictation_prompt(raw_transcript: str, app_name: str) -> str:
    """Construct prompt for dictation semantic formatting."""
    app_hint = APP_HINTS.get(app_name.lower(), "Standard clean desktop application text.")
    return (
        f"Active Application: {app_name}\n"
        f"Context Guideline: {app_hint}\n\n"
        f"Raw Spoken Transcription:\n{raw_transcript}\n\n"
        "Clean Formatted Text:"
    )


def build_rewrite_prompt(selected_text: str, app_name: str) -> str:
    """Construct prompt for contextual text rewrite."""
    app_hint = APP_HINTS.get(app_name.lower(), "Standard clean desktop application text.")
    return (
        f"Active Application: {app_name}\n"
        f"Context Guideline: {app_hint}\n\n"
        f"Selected Text to Polish:\n{selected_text}\n\n"
        "Polished Text:"
    )
