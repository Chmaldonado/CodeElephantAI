from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    ollama_host: str
    tutor_model: str
    embedding_model: str
    chroma_dir: str
    memory_db: str
    docs_dir: str
    top_k: int
    max_agent_steps: int


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _default_runtime_data_root() -> Path:
    if getattr(sys, "frozen", False):
        if os.name == "nt":
            local_app_data = os.getenv("LOCALAPPDATA", "").strip()
            if local_app_data:
                return Path(local_app_data) / "CodeElephantTutor" / "data"
        return Path.home() / ".codeelephanttutor" / "data"
    return Path("data")


def _default_docs_dir(data_root: Path) -> Path:
    if not getattr(sys, "frozen", False):
        return Path("data") / "docs"

    # In packaged builds, prefer docs shipped next to the executable.
    bundled = Path(sys.executable).resolve().parent / "data" / "docs"
    if bundled.exists():
        return bundled
    return data_root / "docs"


def _get_path_env(name: str, default_path: Path) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    return str(default_path)


def get_settings() -> Settings:
    data_root = _default_runtime_data_root()
    return Settings(
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        tutor_model=os.getenv("TUTOR_MODEL", "llama3.1:8b"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        chroma_dir=_get_path_env("CHROMA_DIR", data_root / "chroma"),
        memory_db=_get_path_env("MEMORY_DB", data_root / "memory.db"),
        docs_dir=_get_path_env("DOCS_DIR", _default_docs_dir(data_root)),
        top_k=max(1, _get_int_env("TOP_K", 3)),
        max_agent_steps=max(1, _get_int_env("MAX_AGENT_STEPS", 4)),
    )
