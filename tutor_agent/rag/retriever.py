from __future__ import annotations

import chromadb

from tutor_agent.rag.embeddings import LocalEmbedder


class RAGRetriever:
    def __init__(self, chroma_dir: str, embedding_model: str, ollama_host: str, collection_name: str = "docs"):
        self.client = chromadb.PersistentClient(path=chroma_dir)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self.embedder = LocalEmbedder(model=embedding_model, host=ollama_host)

    def _embed_query(self, query: str) -> list[float]:
        return self.embedder.embed_query(query)

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        if not query.strip():
            return []
        query_vector = self._embed_query(query)
        result = self.collection.query(query_embeddings=[query_vector], n_results=top_k)
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        out: list[dict] = []
        for i, doc in enumerate(docs):
            out.append(
                {
                    "source": (metas[i] or {}).get("source", "unknown"),
                    "text": doc,
                    "distance": distances[i] if i < len(distances) else None,
                }
            )
        return out
