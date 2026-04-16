from __future__ import annotations

from ollama import Client


class LocalEmbedder:
    def __init__(self, model: str, host: str):
        self.model = model
        self.client = Client(host=host)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embed(model=self.model, input=texts)
        return response.get("embeddings", [])

    def embed_query(self, query: str) -> list[float]:
        response = self.client.embed(model=self.model, input=query)
        embeddings = response.get("embeddings", [])
        if not embeddings:
            return []
        return embeddings[0]

