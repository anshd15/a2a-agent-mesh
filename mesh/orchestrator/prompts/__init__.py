"""Versioned prompts, kept as files so changes are reviewed, diffed and tied to eval runs.

Each prompt is Markdown with a small front-matter header (`version: N`). Placeholders use
[[NAME]] because ADK already owns {curly} braces for session-state templating.
"""
from dataclasses import dataclass
from functools import cache
from pathlib import Path

HERE = Path(__file__).parent


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    text: str

    @property
    def tag(self) -> str:
        return f"{self.name}@{self.version}"

    def render(self, **values: str) -> str:
        text = self.text
        for key, value in values.items():
            text = text.replace(f"[[{key.upper()}]]", value)
        if "[[" in text:
            raise ValueError(f"prompt {self.tag} has an unfilled placeholder")
        return text


@cache
def load_prompt(name: str) -> Prompt:
    raw = (HERE / f"{name}.md").read_text(encoding="utf-8")
    if not raw.startswith("---\n") or "\n---\n" not in raw[4:]:
        raise ValueError(f"prompt {name} is missing its front-matter header")
    header, body = raw[4:].split("\n---\n", 1)
    meta = dict(line.split(":", 1) for line in header.splitlines() if ":" in line)
    return Prompt(name=name, version=meta["version"].strip(), text=body.strip())
