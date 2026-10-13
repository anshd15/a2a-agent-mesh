"""Safety callbacks that run before every model call of the trip planner."""
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
    r"ignore (all |any )?(previous|prior|above) instructions|reveal (your )?system prompt", re.IGNORECASE
)
REFUSAL = "I can only help with planning trips."


def redact(text: str) -> str:
    for label, pattern in PII_PATTERNS.items():
        text = pattern.sub(f"[{label}]", text)
    return text


def block_prompt_injection(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Short-circuit the model call when the latest user turn tries to override instructions."""
    last = llm_request.contents[-1] if llm_request.contents else None
    if last is None or last.role != "user":
        return None
    text = " ".join(p.text or "" for p in last.parts or [])
    if INJECTION.search(text):
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=REFUSAL)]))
    return None


def redact_pii(callback_context: CallbackContext, llm_request: LlmRequest) -> LlmResponse | None:
    """Mask card numbers, emails and phone numbers before they reach the model."""
    for content in llm_request.contents:
        for part in content.parts or []:
            if part.text:
                part.text = redact(part.text)
    return None
