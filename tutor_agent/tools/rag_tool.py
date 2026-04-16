from __future__ import annotations

from tutor_agent.rag.retriever import RAGRetriever


class SearchDocsTool:
    name = "search_docs"
    description = "Semantic retrieval over ingested programming docs and snippets."

    def __init__(self, retriever: RAGRetriever, top_k: int):
        self.retriever = retriever
        self.top_k = top_k

    def __call__(self, query: str) -> dict:
        hits = self.retriever.search(query=query, top_k=self.top_k)
        return {"query": query, "top_k": self.top_k, "hits": hits}

