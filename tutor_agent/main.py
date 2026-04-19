from __future__ import annotations

import typer

from tutor_agent.bootstrap import build_services
from tutor_agent.config import get_settings
from tutor_agent.desktop_app import run_desktop_session
from tutor_agent.terminal_ui import run_chat_session, run_tui_session
from tutor_agent.topics import format_discussed_topics

app = typer.Typer(add_completion=False, help="AI coding tutor with RAG + memory + tool orchestration.")


@app.command("chat")
def chat(
    user_id: str = typer.Option("learner", help="Stable learner id for long-term memory."),
    color: bool = typer.Option(True, "--color/--no-color", help="Enable colored role labels in terminal."),
) -> None:
    """Start an interactive tutor session."""
    services = build_services()
    run_chat_session(user_id=user_id, color=color, services=services)


@app.command("tui")
@app.command("aim")
def aim(
    user_id: str = typer.Option("learner", help="Stable learner id for long-term memory."),
) -> None:
    """Start the classic AIM-style terminal tutor session (`tui` and `aim` are aliases)."""
    services = build_services()
    run_tui_session(user_id=user_id, services=services)


@app.command("desktop")
def desktop(
    user_id: str = typer.Option("learner", help="Stable learner id for long-term memory."),
) -> None:
    """Start the classic AIM-style desktop tutor app."""
    services = build_services()
    run_desktop_session(user_id=user_id, services=services)


@app.command("ingest")
def ingest(
    docs_dir: str = typer.Option("", help="Directory of docs to ingest. Defaults to DOCS_DIR."),
) -> None:
    """Ingest docs into Chroma vector store."""
    settings = get_settings()
    services = build_services(settings=settings)
    target = docs_dir.strip() or settings.docs_dir
    count = services.ingestor.ingest_directory(target)
    typer.echo(f"Ingested {count} chunks from {target}")


@app.command("topics")
def topics(
    user_id: str = typer.Option("learner", help="Stable learner id for long-term memory."),
    limit: int = typer.Option(20, min=1, max=200, help="Maximum number of topics to display."),
) -> None:
    """Show tracked discussion topics for a user."""
    services = build_services()
    entries = services.memory.get_discussed_topics(user_id=user_id, limit=limit)
    typer.echo(format_discussed_topics(entries, heading=f"Tracked topics for {user_id}:"))


if __name__ == "__main__":
    app()
