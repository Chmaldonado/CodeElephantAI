from __future__ import annotations

import json
from datetime import datetime

import typer
from rich.console import Console
from rich.markup import escape
from rich.padding import Padding
from rich.prompt import Prompt
from rich.syntax import Syntax

from tutor_agent.bootstrap import AppServices
from tutor_agent.topics import extract_topics, format_discussed_topics
from tutor_agent.ui_common import (
    format_progress,
    format_search_result,
    normalize_lexer_name,
    parse_quiz_topic_and_difficulty,
    split_message_segments,
)


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M")


def _print_chat(console: Console, speaker: str, style: str, message: str) -> None:
    text = message or ""
    segments = split_message_segments(text)
    header_printed = False
    first_text_line = True

    for kind, lang, payload in segments:
        if kind == "text":
            lines = payload.splitlines()
            if not lines:
                continue
            for line in lines:
                if first_text_line:
                    console.print(
                        f"[dim][{_timestamp()}][/dim] [bold {style}]{speaker}[/bold {style}]: {escape(line)}"
                    )
                    header_printed = True
                    first_text_line = False
                else:
                    console.print(f"       {escape(line)}")
            continue

        if not header_printed:
            console.print(f"[dim][{_timestamp()}][/dim] [bold {style}]{speaker}[/bold {style}]:")
            header_printed = True
            first_text_line = False

        lexer = normalize_lexer_name(lang)
        code = payload.rstrip("\n")
        try:
            syntax = Syntax(code or "", lexer=lexer, theme="monokai", line_numbers=False, word_wrap=True)
        except Exception:
            syntax = Syntax(code or "", lexer="text", theme="monokai", line_numbers=False, word_wrap=True)
        console.print(Padding(syntax, (0, 7, 0, 7)))

    if not header_printed:
        console.print(f"[dim][{_timestamp()}][/dim] [bold {style}]{speaker}[/bold {style}]:")
    console.print("")


def collect_code_block(console: Console, lang_hint: str = "") -> tuple[str, str] | None:
    language = (lang_hint or "").strip() or Prompt.ask(
        "[bold cyan]Language[/bold cyan] (python/javascript/...)",
        default="python",
    )
    console.print("[bold cyan]Paste mode[/bold cyan]: end input with a line containing only EOF")
    lines: list[str] = []
    while True:
        line = console.input("")
        if line.strip() == "EOF":
            break
        lines.append(line)
    if not lines:
        return None
    code = "\n".join(lines)
    return language, code


def run_chat_session(user_id: str, color: bool, services: AppServices) -> None:
    orchestrator = services.orchestrator
    memory = services.memory
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
            typer.echo(format_discussed_topics(entries, heading="Discussed topics:"))
            continue
        memory.record_discussed_topics(user_id=user_id, topics=extract_topics(msg))
        reply = orchestrator.run_turn(user_id=user_id, user_message=msg)
        if color:
            typer.secho("Tutor:", fg=typer.colors.GREEN, bold=True, nl=False)
            typer.echo(f" {reply}")
        else:
            typer.echo(f"Tutor: {reply}")


def run_tui_session(user_id: str, services: AppServices) -> None:
    orchestrator = services.orchestrator
    memory = services.memory
    console = Console()
    tools = orchestrator.tools

    help_text = (
        "Commands:\n"
        "/ask <message>        ask the tutor (default if no command)\n"
        "/paste [lang]         paste multiline code and ask for help\n"
        "/run [lang]           paste multiline code and execute it locally\n"
        "/search <query>       run RAG document search directly\n"
        "/quiz <topic> [level] generate a quiz (easy|medium|hard)\n"
        "/topics               show tracked topics\n"
        "/progress             show learner profile memory\n"
        "/help                 show this menu\n"
        "/quit                 exit"
    )

    console.print("[bold cyan]CodeElephant Tutor (AIM Mode)[/bold cyan]")
    console.print("[dim]Type /help for commands. Use /quit to exit.[/dim]")

    while True:
        raw = console.input("[bold blue]you>[/bold blue] ")
        clean = raw.strip()
        if not clean:
            continue

        lower = clean.lower()
        if lower in {"/quit", "quit", "exit"}:
            _print_chat(console, "Tutor", "green", "Bye.")
            return
        if lower in {"/help", "help"}:
            _print_chat(console, "Tutor", "green", help_text)
            continue
        if lower in {"/topics", "topics"}:
            entries = memory.get_discussed_topics(user_id=user_id, limit=20)
            _print_chat(console, "Tutor", "green", format_discussed_topics(entries, heading="Tracked topics:"))
            continue
        if lower in {"/progress", "progress"}:
            progress = memory.get_user_progress(user_id=user_id)
            _print_chat(console, "Tutor", "green", format_progress(progress))
            continue
        if lower.startswith("/search "):
            query = clean.split(" ", 1)[1].strip()
            if not query:
                _print_chat(console, "Tutor", "green", "Usage: /search <query>")
                continue
            result = tools["search_docs"](query=query)
            _print_chat(console, "Tutor", "green", format_search_result(result))
            continue
        if lower.startswith("/quiz "):
            payload = clean.split(" ", 1)[1].strip()
            topic, difficulty = parse_quiz_topic_and_difficulty(payload)
            if not topic:
                _print_chat(console, "Tutor", "green", "Usage: /quiz <topic> [easy|medium|hard]")
                continue
            result = tools["generate_quiz"](topic=topic, difficulty=difficulty)
            _print_chat(console, "Tutor", "green", json.dumps(result, ensure_ascii=True, indent=2))
            continue
        if lower.startswith("/run"):
            parts = clean.split(maxsplit=1)
            lang_hint = parts[1] if len(parts) > 1 else "python"
            block = collect_code_block(console, lang_hint=lang_hint)
            if not block:
                _print_chat(console, "Tutor", "green", "No code received.")
                continue
            lang, snippet = block
            _print_chat(console, "You", "blue", f"(run {lang})\n{snippet}")
            result = tools["execute_code"](snippet=snippet, lang=lang)
            _print_chat(console, "Tutor", "green", json.dumps(result, ensure_ascii=True, indent=2))
            continue

        msg = clean
        if lower.startswith("/paste"):
            parts = clean.split(maxsplit=1)
            lang_hint = parts[1] if len(parts) > 1 else ""
            block = collect_code_block(console, lang_hint=lang_hint)
            if not block:
                _print_chat(console, "Tutor", "green", "No code received.")
                continue
            lang, snippet = block
            note = Prompt.ask("[bold cyan]Optional note[/bold cyan] (Enter to skip)", default="")
            fenced = f"```{lang}\n{snippet}\n```"
            msg = f"{note}\n\n{fenced}".strip() if note else fenced
        elif lower.startswith("/ask "):
            msg = clean.split(" ", 1)[1].strip()
            if not msg:
                _print_chat(console, "Tutor", "green", "Usage: /ask <message>")
                continue
        elif clean.startswith("/"):
            _print_chat(console, "Tutor", "green", "Unknown command. Type /help.")
            continue

        memory.record_discussed_topics(user_id=user_id, topics=extract_topics(msg))
        _print_chat(console, "You", "blue", msg)
        reply = orchestrator.run_turn(user_id=user_id, user_message=msg)
        _print_chat(console, "Tutor", "green", reply)
