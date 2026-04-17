from __future__ import annotations

import re

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.text import Text

from tutor_agent.config import get_settings
from tutor_agent.core.orchestrator import TutorOrchestrator
from tutor_agent.llm import LocalLLM
from tutor_agent.memory.store import MemoryStore
from tutor_agent.rag.ingest import RAGIngestor
from tutor_agent.rag.retriever import RAGRetriever
from tutor_agent.tools.code_executor import ExecuteCodeTool
from tutor_agent.tools.memory_tools import GetUserProgressTool, UpdateMemoryTool
from tutor_agent.tools.quiz_tool import GenerateQuizTool
from tutor_agent.tools.rag_tool import SearchDocsTool

app = typer.Typer(add_completion=False, help="AI coding tutor with RAG + memory + tool orchestration.")


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


def _extract_topics(message: str, max_topics: int = 8) -> list[str]:
    text = (message or "").strip()
    if not text or text.startswith("/"):
        return []

    text = re.sub(r"```[\s\S]*?```", " ", text)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_+#.-]{1,}", text.lower())
    ordered_unique: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in TOPIC_STOPWORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        ordered_unique.append(token)
        if len(ordered_unique) >= max_topics:
            break
    return ordered_unique


def _collect_code_block(console: Console, lang_hint: str = "") -> str | None:
    language = (lang_hint or "").strip() or Prompt.ask(
        "[bold cyan]Language[/bold cyan] (python/javascript/...)",
        default="python",
    )
    console.print(
        Panel(
            "Paste/type your code. End input with a line containing only [bold]EOF[/bold].",
            title="Paste Mode",
            border_style="cyan",
        )
    )
    lines: list[str] = []
    while True:
        line = console.input("")
        if line.strip() == "EOF":
            break
        lines.append(line)
    if not lines:
        return None
    code = "\n".join(lines)
    return f"```{language}\n{code}\n```"


def build_orchestrator() -> tuple[TutorOrchestrator, RAGIngestor, MemoryStore]:
    settings = get_settings()
    llm = LocalLLM(model=settings.tutor_model, host=settings.ollama_host)

    retriever = RAGRetriever(
        chroma_dir=settings.chroma_dir,
        embedding_model=settings.embedding_model,
        ollama_host=settings.ollama_host,
    )
    ingestor = RAGIngestor(
        chroma_dir=settings.chroma_dir,
        embedding_model=settings.embedding_model,
        ollama_host=settings.ollama_host,
    )
    memory = MemoryStore(db_path=settings.memory_db)

    tools = {
        "search_docs": SearchDocsTool(retriever=retriever, top_k=settings.top_k),
        "execute_code": ExecuteCodeTool(timeout_seconds=5),
        "generate_quiz": GenerateQuizTool(llm=llm),
        "get_user_progress": GetUserProgressTool(store=memory),
        "update_memory": UpdateMemoryTool(store=memory),
    }

    orchestrator = TutorOrchestrator(
        llm=llm,
        max_steps=settings.max_agent_steps,
        tools=tools,
    )
    return orchestrator, ingestor, memory


@app.command("chat")
def chat(
    user_id: str = typer.Option("learner", help="Stable learner id for long-term memory."),
    color: bool = typer.Option(True, "--color/--no-color", help="Enable colored role labels in terminal."),
) -> None:
    """Start an interactive tutor session."""
    orchestrator, _, memory = build_orchestrator()
    typer.secho("Tutor ready. Type '/quit' to exit.", fg=typer.colors.GREEN if color else None)

    while True:
        prompt_text = typer.style("You", fg=typer.colors.BLUE, bold=True) if color else "You"
        msg = typer.prompt(prompt_text)
        lower = msg.strip().lower()
        if lower in {"/quit", "quit", "exit"}:
            typer.secho("Bye.", fg=typer.colors.GREEN if color else None)
            return
        if lower in {"/topics", "topics"}:
            entries = memory.get_discussed_topics(user_id=user_id, limit=20)
            if not entries:
                typer.echo("No topics tracked yet for this user.")
            else:
                typer.echo("Discussed topics:")
                for row in entries:
                    typer.echo(f"- {row['topic']} ({row['mentions']})")
            continue
        memory.record_discussed_topics(user_id=user_id, topics=_extract_topics(msg))
        reply = orchestrator.run_turn(user_id=user_id, user_message=msg)
        if color:
            typer.secho("Tutor:", fg=typer.colors.GREEN, bold=True, nl=False)
            typer.echo(f" {reply}")
        else:
            typer.echo(f"Tutor: {reply}")


@app.command("tui")
def tui(
    user_id: str = typer.Option("learner", help="Stable learner id for long-term memory."),
) -> None:
    """Start a richer terminal UI chat session."""
    orchestrator, _, memory = build_orchestrator()
    console = Console()
    transcript: list[tuple[str, str]] = []

    def render_screen() -> None:
        console.clear()
        console.print(Rule("[bold cyan]AI Coding Tutor[/bold cyan]"))
        if not transcript:
            console.print(
                Panel(
                    "Type your message and press Enter.\nCommands: /paste [lang], /topics, /help, /quit",
                    title="Welcome",
                    border_style="green",
                )
            )
            return
        for role, content in transcript[-16:]:
            label = "You" if role == "user" else "Tutor"
            color = "blue" if role == "user" else "green"
            renderable = Markdown(content) if "```" in content else Text(content)
            console.print(
                Panel(
                    renderable,
                    title=f"[bold {color}]{label}[/bold {color}]",
                    border_style=color,
                )
            )

    with console.screen():
        render_screen()
        while True:
            msg = console.input("[bold blue]>[/bold blue] ")
            clean = msg.strip()
            lower = clean.lower()
            if lower in {"/quit", "quit", "exit"}:
                return
            if lower in {"/help", "help"}:
                transcript.append(
                    (
                        "assistant",
                        "Commands:\n- /paste [lang] for multi-line code input (end with EOF)\n- /topics to view tracked topics\n- /quit to exit",
                    )
                )
                render_screen()
                continue
            if lower in {"/topics", "topics"}:
                entries = memory.get_discussed_topics(user_id=user_id, limit=20)
                if not entries:
                    transcript.append(("assistant", "No topics tracked yet for this user."))
                else:
                    lines = ["Tracked topics:"]
                    lines.extend([f"- {row['topic']} ({row['mentions']})" for row in entries])
                    transcript.append(("assistant", "\n".join(lines)))
                render_screen()
                continue
            if lower.startswith("/paste"):
                parts = clean.split(maxsplit=1)
                lang_hint = parts[1] if len(parts) > 1 else ""
                block = _collect_code_block(console, lang_hint=lang_hint)
                if not block:
                    transcript.append(("assistant", "No code received. Paste mode cancelled."))
                    render_screen()
                    continue
                note = Prompt.ask("[bold cyan]Optional note[/bold cyan] (Enter to skip)", default="")
                msg = f"{note}\n\n{block}".strip() if note else block
            memory.record_discussed_topics(user_id=user_id, topics=_extract_topics(msg))
            transcript.append(("user", msg))
            render_screen()
            reply = orchestrator.run_turn(user_id=user_id, user_message=msg)
            transcript.append(("assistant", reply))
            render_screen()


@app.command("ingest")
def ingest(
    docs_dir: str = typer.Option("", help="Directory of docs to ingest. Defaults to DOCS_DIR."),
) -> None:
    """Ingest docs into Chroma vector store."""
    settings = get_settings()
    _, ingestor, _ = build_orchestrator()
    target = docs_dir.strip() or settings.docs_dir
    count = ingestor.ingest_directory(target)
    typer.echo(f"Ingested {count} chunks from {target}")


@app.command("topics")
def topics(
    user_id: str = typer.Option("learner", help="Stable learner id for long-term memory."),
    limit: int = typer.Option(20, min=1, max=200, help="Maximum number of topics to display."),
) -> None:
    """Show tracked discussion topics for a user."""
    _, _, memory = build_orchestrator()
    entries = memory.get_discussed_topics(user_id=user_id, limit=limit)
    if not entries:
        typer.echo("No topics tracked yet for this user.")
        return
    typer.echo(f"Tracked topics for {user_id}:")
    for row in entries:
        typer.echo(f"- {row['topic']} ({row['mentions']})")


if __name__ == "__main__":
    app()
