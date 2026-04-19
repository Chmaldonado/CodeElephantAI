from __future__ import annotations

from dataclasses import dataclass

from tutor_agent.config import Settings, get_settings
from tutor_agent.core.orchestrator import TutorOrchestrator
from tutor_agent.llm import LocalLLM
from tutor_agent.memory.store import MemoryStore
from tutor_agent.rag.ingest import RAGIngestor
from tutor_agent.rag.retriever import RAGRetriever
from tutor_agent.tools.code_executor import ExecuteCodeTool
from tutor_agent.tools.memory_tools import GetUserProgressTool, UpdateMemoryTool
from tutor_agent.tools.quiz_tool import GenerateQuizTool
from tutor_agent.tools.rag_tool import SearchDocsTool


@dataclass(frozen=True)
class AppServices:
    orchestrator: TutorOrchestrator
    ingestor: RAGIngestor
    memory: MemoryStore


def build_services(settings: Settings | None = None) -> AppServices:
    """Assemble all core services used by CLI entrypoints."""
    active_settings = settings or get_settings()
    llm = LocalLLM(model=active_settings.tutor_model, host=active_settings.ollama_host)

    retriever = RAGRetriever(
        chroma_dir=active_settings.chroma_dir,
        embedding_model=active_settings.embedding_model,
        ollama_host=active_settings.ollama_host,
    )
    ingestor = RAGIngestor(
        chroma_dir=active_settings.chroma_dir,
        embedding_model=active_settings.embedding_model,
        ollama_host=active_settings.ollama_host,
    )
    memory = MemoryStore(db_path=active_settings.memory_db)

    tools = {
        "search_docs": SearchDocsTool(retriever=retriever, top_k=active_settings.top_k),
        "execute_code": ExecuteCodeTool(timeout_seconds=5),
        "generate_quiz": GenerateQuizTool(llm=llm),
        "get_user_progress": GetUserProgressTool(store=memory),
        "update_memory": UpdateMemoryTool(store=memory),
    }

    orchestrator = TutorOrchestrator(
        llm=llm,
        max_steps=active_settings.max_agent_steps,
        tools=tools,
    )
    return AppServices(orchestrator=orchestrator, ingestor=ingestor, memory=memory)
