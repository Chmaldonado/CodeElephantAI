from __future__ import annotations

import re
from typing import Any


FENCED_BLOCK_RE = re.compile(r"```([A-Za-z0-9_+#.-]*)\n([\s\S]*?)```")

LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "sh": "bash",
    "c++": "cpp",
    "c#": "csharp",
}


def parse_quiz_topic_and_difficulty(raw: str) -> tuple[str, str]:
    tokens = raw.split()
    if not tokens:
        return "", "medium"
    maybe_diff = tokens[-1].strip().lower()
    if maybe_diff in {"easy", "medium", "hard"} and len(tokens) > 1:
        return " ".join(tokens[:-1]).strip(), maybe_diff
    return raw.strip(), "medium"


def split_message_segments(message: str) -> list[tuple[str, str, str]]:
    segments: list[tuple[str, str, str]] = []
    pos = 0
    for match in FENCED_BLOCK_RE.finditer(message):
        start, end = match.span()
        if start > pos:
            segments.append(("text", "", message[pos:start]))
        segments.append(("code", match.group(1), match.group(2)))
        pos = end
    if pos < len(message):
        segments.append(("text", "", message[pos:]))
    return segments or [("text", "", message)]


def normalize_lexer_name(lang: str) -> str:
    key = (lang or "").strip().lower()
    return LANGUAGE_ALIASES.get(key, key or "text")


def format_search_result(payload: dict[str, Any], snippet_char_limit: int = 160) -> str:
    hits = payload.get("hits", []) or []
    query = str(payload.get("query", ""))
    if not hits:
        return f"No docs matched: {query}"

    lines = [f"Top {len(hits)} docs for: {query}"]
    for idx, hit in enumerate(hits, start=1):
        source = str(hit.get("source", "unknown"))
        distance = hit.get("distance")
        text = str(hit.get("text", "")).replace("\r", "").strip()
        text = " ".join(text.split())
        if len(text) > snippet_char_limit:
            text = text[:snippet_char_limit] + "..."
        lines.append(f"{idx}. {source} | distance={distance}")
        lines.append(f"   {text}")
    return "\n".join(lines)


def format_progress(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "No progress found."
    return (
        f"Skill level: {payload.get('skill_level', 'beginner')}\n"
        f"Known topics: {', '.join(payload.get('known_topics', [])) or '(none)'}\n"
        f"Struggled topics: {', '.join(payload.get('struggled_topics', [])) or '(none)'}\n"
        f"Last summary: {payload.get('last_summary', '') or '(none)'}"
    )
