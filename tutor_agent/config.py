from __future__ import annotations

import os
from dataclasses import dataclass

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


def get_settings() -> Settings:
    return Settings(
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        tutor_model=os.getenv("TUTOR_MODEL", "llama3.1:8b"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        chroma_dir=os.getenv("CHROMA_DIR", "./data/chroma"),
        memory_db=os.getenv("MEMORY_DB", "./data/memory.db"),
        docs_dir=os.getenv("DOCS_DIR", "./data/docs"),
        top_k=int(os.getenv("TOP_K", "4")),
        max_agent_steps=int(os.getenv("MAX_AGENT_STEPS", "6")),
    )
