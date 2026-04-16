from __future__ import annotations

from pathlib import Path
from typing import Iterable

from tutor_agent.models import DocChunk


TEXT_EXTENSIONS = {".md", ".txt", ".rst", ".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml"}


def iter_text_files(root: str) -> Iterable[Path]:
    base = Path(root)
    if not base.exists():
        return []
    return [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS]


def split_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    clean = text.strip()
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + chunk_size, len(clean))
        chunks.append(clean[start:end])
        if end == len(clean):
            break
        start = max(0, end - overlap)
    return chunks


def chunk_file(path: Path, chunk_size: int = 800, overlap: int = 120) -> list[DocChunk]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    out: list[DocChunk] = []
    for idx, piece in enumerate(split_text(text, chunk_size=chunk_size, overlap=overlap)):
        out.append(
            DocChunk(
                id=f"{path.as_posix()}::{idx}",
                source=path.as_posix(),
                text=piece,
            )
        )
    return out

