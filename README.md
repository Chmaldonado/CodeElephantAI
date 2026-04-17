# CodeElephantAI Tutor

Terminal-first AI coding tutor with:
- agent orchestration
- local RAG over your docs
- local long-term learner memory
- tool-calling behavior (search docs, execute code, generate quiz, update memory)

Built for local use with Ollama + Chroma + SQLite.

## What This Project Is

This app is a local coding tutor agent that can:
- answer coding questions
- retrieve relevant local docs/snippets with semantic search
- run Python snippets in a constrained subprocess
- generate quizzes
- remember learner progress across sessions

The current product is terminal-only (no web UI).

## Architecture

High-level flow:

```text
User (Terminal)
  -> Orchestrator (plans each turn)
      -> Tools (as needed):
         - search_docs
         - execute_code
         - generate_quiz
         - get_user_progress
         - update_memory
      -> LLM response
  -> Terminal output
```

RAG flow:

```text
docs files -> chunking -> embeddings (nomic-embed-text via Ollama)
           -> Chroma persistent store
query -> embed -> top-k semantic retrieval -> injected into planning context
```

## Components

- `tutor_agent/core/orchestrator.py`
  - agent loop, tool routing, step limit, action parsing
- `tutor_agent/rag/ingest.py`
  - scans docs, chunks text, computes embeddings, upserts into Chroma
- `tutor_agent/rag/retriever.py`
  - semantic search over vector store
- `tutor_agent/tools/`
  - tool adapters used by orchestrator
- `tutor_agent/memory/store.py`
  - SQLite learner progress store
- `tutor_agent/llm.py`
  - Ollama chat + JSON response parsing
- `tutor_agent/main.py`
  - CLI commands: `chat`, `tui`, `ingest`, `topics`

## Tools Used (Current Stack)

- Language/runtime: Python 3.10+
- LLM serving: Ollama
- Tutor model default: `llama3.1:8b`
- Embedding model default: `nomic-embed-text`
- Vector DB: Chroma (local persistent directory)
- Long-term memory DB: SQLite
- CLI framework: Typer
- Terminal UI rendering: Rich
- Optional containerization: Docker Compose

## Project Structure

```text
tutor_agent/
  core/
  memory/
  prompts/
  rag/
  tools/
  config.py
  llm.py
  main.py
data/
  docs/        # source docs for RAG
  chroma/      # vector store (created/populated at runtime)
  memory.db    # SQLite learner memory
docker-compose.yml
run_docker.ps1
run_local.ps1
run_cli.cmd
run_tui.cmd
launch_all.cmd
```

## Prerequisites

### Required

- Python 3.10+
- Ollama installed and running

### Optional

- Docker Desktop (for containerized workflow)
- NVIDIA GPU + Docker GPU support (if using GPU mode)

## Quick Start (Local, No Docker)

1. Create and activate a venv.

```powershell
python -m venv .venv_local
.\.venv_local\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
.\.venv_local\Scripts\python -m pip install -e .
```

3. Create `.env` with your local settings.

```powershell
@"
OLLAMA_HOST=http://127.0.0.1:11434
TUTOR_MODEL=llama3.1:8b
EMBEDDING_MODEL=nomic-embed-text
CHROMA_DIR=./data/chroma
MEMORY_DB=./data/memory.db
DOCS_DIR=./data/docs
TOP_K=4
MAX_AGENT_STEPS=6
"@ | Set-Content .env
```

4. Pull required Ollama models.

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

5. Ingest docs into RAG.

```powershell
.\.venv_local\Scripts\python -m tutor_agent.main ingest
```

6. Start tutor.

```powershell
.\.venv_local\Scripts\python -m tutor_agent.main tui --user-id learner
```

Windows shortcuts:

```cmd
run_tui.cmd learner
run_cli.cmd learner
```

## Quick Start (Docker)

1. Start stack + model checks + ingest.

```powershell
.\run_docker.ps1 -Action up
```

GPU mode (optional):

```powershell
.\run_docker.ps1 -Action up -UseGpu
```

2. Start panel-style terminal chat.

```powershell
.\run_docker.ps1 -Action chat -UserId learner
```

Other Docker actions:

```powershell
.\run_docker.ps1 -Action chat-plain -UserId learner
.\run_docker.ps1 -Action ingest
.\run_docker.ps1 -Action topics -UserId learner
.\run_docker.ps1 -Action logs
.\run_docker.ps1 -Action down
.\run_docker.ps1 -Action up -ForcePullModels
```

To run any Docker action in GPU mode, append `-UseGpu`.

One-click launcher:

```cmd
launch_all.cmd learner
```

## CLI Commands

From the installed package entrypoint:

```bash
tutor ingest
tutor chat --user-id learner
tutor tui --user-id learner
tutor topics --user-id learner
```

Direct module form:

```bash
python -m tutor_agent.main ingest
python -m tutor_agent.main chat --user-id learner
python -m tutor_agent.main tui --user-id learner
python -m tutor_agent.main topics --user-id learner
```

## Terminal UI Notes

In `tui` mode:
- `/help` shows commands
- `/quit` exits
- `/paste [lang]` enters multi-line paste mode
- `/topics` shows tracked discussed topics
- finish paste mode with a line containing only `EOF`

`/paste` wraps input in fenced markdown blocks before sending to the tutor.

## Data and Persistence

- RAG docs source: `data/docs/`
- Vector DB files: `data/chroma/`
- Learner memory DB: `data/memory.db`

What persists:
- Chroma index persists across restarts (if data directory/volume remains)
- SQLite learner profile persists across restarts

What does not persist by default:
- full chat transcript history in orchestrator process memory

## Configuration

Environment variables (`.env`):

- `OLLAMA_HOST` (default `http://127.0.0.1:11434`)
- `TUTOR_MODEL` (default `llama3.1:8b`)
- `EMBEDDING_MODEL` (default `nomic-embed-text`)
- `CHROMA_DIR` (default `./data/chroma`)
- `MEMORY_DB` (default `./data/memory.db`)
- `DOCS_DIR` (default `./data/docs`)
- `TOP_K` (default `4`)
- `MAX_AGENT_STEPS` (default `6`)

## Current Built-In Tooling

- `search_docs(query)`
  - semantic retrieval from Chroma
- `execute_code(snippet, lang)`
  - local Python execution only (currently)
- `generate_quiz(topic, difficulty)`
  - quiz generation via LLM
- `get_user_progress(user_id)`
  - fetch learner profile from SQLite
- `update_memory(user_id, patch)`
  - update learner profile

## Known Limitations

- Code execution tool currently supports only Python.
- Code execution uses basic safety guards, not full container sandboxing.
- Planner relies on JSON parsing from model output, which can occasionally fail.
- No auth/multi-tenant isolation yet (single local environment assumptions).
- No web interface in this branch (terminal-first only).

## Troubleshooting

- `No such command 'tui'`:
  - run latest code path: `python -m tutor_agent.main --help`
  - if Docker, rebuild: `.\run_docker.ps1 -Action chat` already uses `--build`
- Ollama model not found:
  - run `ollama pull llama3.1:8b` and `ollama pull nomic-embed-text`
- Empty/weak retrieval:
  - add docs to `data/docs` and rerun ingest
- Docker GPU not used:
  - verify NVIDIA driver + Docker Desktop GPU support + WSL2 backend
  - run Docker commands with `-UseGpu`

## Suggested Next Upgrades

- Replace local code execution with sandbox services (E2B/Judge0)
- Add reranking for RAG
- Persist full chat transcripts
- Add eval set + regression tests for tool routing
- Add user auth and per-user namespaces

## Contributing

PRs are welcome. If you add features, please include:
- updated docs/commands in this README
- reproducible steps to run/test locally
- notes on data model or tool-contract changes
