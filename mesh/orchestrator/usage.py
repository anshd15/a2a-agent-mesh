"""Track token usage and estimated cost per session, so spend is measured, not guessed."""
import os

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse

# Defaults are Gemini 2.5 Flash list prices in USD per 1M tokens; override for other models.
PRICE_IN_PER_M = float(os.getenv("PRICE_IN_PER_M", "0.30"))
PRICE_OUT_PER_M = float(os.getenv("PRICE_OUT_PER_M", "2.50"))


def track_usage(callback_context: CallbackContext, llm_response: LlmResponse) -> LlmResponse | None:
    """Accumulate model calls, tokens and cost into session state under "usage"."""
    meta = llm_response.usage_metadata
    if meta is None:
        return None
    usage = dict(callback_context.state.get("usage") or {})
    usage["calls"] = usage.get("calls", 0) + 1
    usage["input_tokens"] = usage.get("input_tokens", 0) + (meta.prompt_token_count or 0)
    usage["output_tokens"] = usage.get("output_tokens", 0) + (meta.candidates_token_count or 0)
    usage["cost_usd"] = round(
        usage["input_tokens"] * PRICE_IN_PER_M / 1e6
        + usage["output_tokens"] * PRICE_OUT_PER_M / 1e6,
        6,
    )
    callback_context.state["usage"] = usage
    return None
