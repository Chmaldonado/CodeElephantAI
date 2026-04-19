from __future__ import annotations

import re
from typing import Any


TOPIC_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "code",
    "do",
    "for",
    "from",
    "hello",
    "help",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "please",
    "show",
    "so",
    "that",
    "the",
    "this",
    "to",
    "we",
    "what",
    "with",
    "you",
    "your",
}


def extract_topics(message: str, max_topics: int = 8) -> list[str]:
    """Extract a compact set of discussion topics from a learner message."""
    text = (message or "").strip()
    if not text or text.startswith("/"):
        return []

    # Remove fenced code blocks so identifiers inside snippets do not dominate topics.
    text = re.sub(r"```[\s\S]*?```", " ", text)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_+#.-]{1,}", text.lower())

    ordered_unique: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in TOPIC_STOPWORDS or token in seen:
            continue
        seen.add(token)
        ordered_unique.append(token)
        if len(ordered_unique) >= max_topics:
            break
    return ordered_unique


def format_discussed_topics(entries: list[dict[str, Any]], heading: str = "Tracked topics:") -> str:
    if not entries:
        return "No topics tracked yet for this user."
    lines = [heading]
    lines.extend([f"- {row['topic']} ({row['mentions']})" for row in entries])
    return "\n".join(lines)
