"""Safety callbacks that run before every model call of the trip planner."""
import os
import re

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

# Order matters: card numbers are matched before the shorter phone pattern.
PII_PATTERNS = {
    "CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "PHONE": re.compile(r"\+\d[\d ]{8,14}\d|\b\d{10}\b"),
}
INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|reveal (your )?system prompt",
    re.IGNORECASE,
)
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "4000"))
REFUSAL = "I can only help with planning trips."
TOO_LONG = "That message is too long - please summarise your trip request."


def redact(text: str) -> str:
    for label, pattern in PII_PATTERNS.items():
        text = pattern.sub(f"[{label}]", text)
    return text


def _latest_user_text(llm_request: LlmRequest) -> str | None:
    last = llm_request.contents[-1] if llm_request.contents else None
    if last is None or last.role != "user":
        return None
    return " ".join(p.text or "" for p in last.parts or [])


def _reply(text: str) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))


def limit_input_length(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Refuse oversized user turns before they burn tokens."""
    text = _latest_user_text(llm_request)
    if text is not None and len(text) > MAX_INPUT_CHARS:
        return _reply(TOO_LONG)
    return None


def block_prompt_injection(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Short-circuit the model call when the latest user turn tries to override instructions."""
    text = _latest_user_text(llm_request)
    if text and INJECTION.search(text):
        return _reply(REFUSAL)
    return None


def redact_pii(callback_context: CallbackContext, llm_request: LlmRequest) -> LlmResponse | None:
    """Mask card numbers, emails and phone numbers before they reach the model."""
    for content in llm_request.contents:
        for part in content.parts or []:
            if part.text:
                part.text = redact(part.text)
    return None
