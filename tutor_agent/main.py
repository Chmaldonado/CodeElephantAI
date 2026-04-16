from __future__ import annotations

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


def build_orchestrator() -> tuple[TutorOrchestrator, RAGIngestor]:
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
    return orchestrator, ingestor


@app.command("chat")
def chat(
    user_id: str = typer.Option("demo-user", help="Stable learner id for long-term memory."),
    color: bool = typer.Option(True, "--color/--no-color", help="Enable colored role labels in terminal."),
) -> None:
    """Start an interactive tutor session."""
    orchestrator, _ = build_orchestrator()
    typer.secho("Tutor ready. Type '/quit' to exit.", fg=typer.colors.GREEN if color else None)

    while True:
        prompt_text = typer.style("You", fg=typer.colors.BLUE, bold=True) if color else "You"
        msg = typer.prompt(prompt_text)
        if msg.strip().lower() in {"/quit", "quit", "exit"}:
            typer.secho("Bye.", fg=typer.colors.GREEN if color else None)
            return
        reply = orchestrator.run_turn(user_id=user_id, user_message=msg)
        if color:
            typer.secho("Tutor:", fg=typer.colors.GREEN, bold=True, nl=False)
            typer.echo(f" {reply}")
        else:
            typer.echo(f"Tutor: {reply}")


@app.command("tui")
def tui(
    user_id: str = typer.Option("demo-user", help="Stable learner id for long-term memory."),
) -> None:
    """Start a richer terminal UI chat session."""
    orchestrator, _ = build_orchestrator()
    console = Console()
    transcript: list[tuple[str, str]] = []

    def render_screen() -> None:
        console.clear()
        console.print(Rule("[bold cyan]AI Coding Tutor[/bold cyan]"))
        if not transcript:
            console.print(
                Panel(
                    "Type your message and press Enter.\nCommands: /paste [lang], /help, /quit",
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
                        "Commands:\n- /paste [lang] for multi-line code input (end with EOF)\n- /quit to exit",
                    )
                )
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
    _, ingestor = build_orchestrator()
    target = docs_dir.strip() or settings.docs_dir
    count = ingestor.ingest_directory(target)
    typer.echo(f"Ingested {count} chunks from {target}")


if __name__ == "__main__":
    app()
