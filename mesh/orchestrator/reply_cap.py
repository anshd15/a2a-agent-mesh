"""Cap oversized specialist replies before they reach the planner's model.

One chatty - or hostile - specialist returning megabytes of text would blow the context
window and the token bill for every later turn. Replies over MAX_TOOL_REPLY_CHARS are cut,
with a note saying how much was dropped, so the model knows the answer is partial.
"""
from collections.abc import Callable
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from mesh.config import MAX_TOOL_REPLY_CHARS
from mesh.orchestrator.tool_guard import response_text

TRUNCATION_NOTE = "\n[... {dropped} characters truncated by the planner ...]"


def reply_cap(specialists: set[str],
              max_chars: int = MAX_TOOL_REPLY_CHARS) -> Callable[..., dict | None]:
    """after_tool_callback that truncates specialist replies longer than max_chars."""

    def cap(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext,
            tool_response: Any) -> dict | None:
        if tool.name not in specialists or max_chars <= 0:
            return None
        text = response_text(tool_response)
        if len(text) <= max_chars:
            return None
        note = TRUNCATION_NOTE.format(dropped=len(text) - max_chars)
        return {"result": text[:max_chars] + note, "truncated": True}

    return cap
