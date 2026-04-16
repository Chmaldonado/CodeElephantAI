from __future__ import annotations

from typing import Iterable

import chromadb
from chromadb.api.models.Collection import Collection

from tutor_agent.models import DocChunk
from tutor_agent.rag.chunking import chunk_file, iter_text_files
from tutor_agent.rag.embeddings import LocalEmbedder


class RAGIngestor:
    def __init__(self, chroma_dir: str, embedding_model: str, ollama_host: str, collection_name: str = "docs"):
        self.client = chromadb.PersistentClient(path=chroma_dir)
        self.collection: Collection = self.client.get_or_create_collection(name=collection_name)
        self.embedder = LocalEmbedder(model=embedding_model, host=ollama_host)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed_texts(texts)

    def upsert_chunks(self, chunks: Iterable[DocChunk]) -> int:
        chunk_list = list(chunks)
        if not chunk_list:
            return 0
        texts = [c.text for c in chunk_list]
        embeddings = self._embed(texts)
        self.collection.upsert(
            ids=[c.id for c in chunk_list],
            documents=texts,
            embeddings=embeddings,
            metadatas=[{"source": c.source} for c in chunk_list],
        )
        return len(chunk_list)

    def ingest_directory(self, docs_dir: str, chunk_size: int = 800, overlap: int = 120) -> int:
        all_chunks: list[DocChunk] = []
        for path in iter_text_files(docs_dir):
            all_chunks.extend(chunk_file(path, chunk_size=chunk_size, overlap=overlap))
        return self.upsert_chunks(all_chunks)
