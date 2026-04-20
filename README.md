# CodeElephantAI Tutor

Local AI coding tutor with:
- agent-style tool orchestration
- local RAG (Chroma + Ollama embeddings)
- local long-term memory (SQLite)
- terminal and desktop (AIM-style) interfaces

No cloud API keys are required for the default setup.

## Features

- Local tutoring model via Ollama (`llama3.1:8b` by default)
- Local embedding model via Ollama (`nomic-embed-text` by default)
- Tooling:
  - `search_docs`
  - `execute_code` (local Python executor)
  - `generate_quiz`
  - `get_user_progress`
  - `update_memory`
- Topic tracking (`/topics`) and progress profile (`/progress`)
- Code block rendering in terminal and desktop UI
- Optional desktop sounds and custom app icon

## App Modes

- `chat`: plain CLI chat
- `aim`: rich terminal AIM-style chat
- `tui`: alias for `aim`
- `desktop`: Tkinter desktop AIM-style app

## Architecture

```text
User (terminal/desktop)
  -> Orchestrator
     -> Plans tool call(s) or direct response
     -> Calls tools (RAG, code exec, quiz, memory)
     -> Produces final tutor reply
```

RAG flow:

```text
docs -> chunk -> embed -> Chroma
query -> embed -> top-k retrieval -> planner context
```

## Project Structure

```text
tutor_agent/
  bootstrap.py
  config.py
  main.py
  terminal_ui.py
  desktop_app.py
  desktop_entry.py
  topics.py
  ui_common.py
  core/orchestrator.py
  rag/
  memory/store.py
  tools/
  prompts/system_prompt.py

data/
  docs/                  # RAG source docs
  chroma/                # local vector DB (runtime)
  memory.db              # local learner memory (runtime)

assets/
  sounds/
  branding/

scripts and launchers:
  run_desktop.cmd
  build_desktop_exe.cmd
  build_desktop_exe.ps1
  install_desktop.cmd
  install_desktop_ui.ps1
  build_installer_exe.cmd
  build_installer_exe.ps1
  run_local.ps1
  run_docker.ps1
```

## Requirements

- Windows 10/11 (desktop app and installer scripts)
- Python 3.10+
- Ollama

Optional:
- Docker Desktop (container workflow)
- NVIDIA GPU + Docker GPU support (for `run_docker.ps1 -UseGpu`)

## Quick Start (Local)

1) Create venv

```powershell
python -m venv .venv_local
.\.venv_local\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
.\.venv_local\Scripts\python -m pip install -e .
```

3) Create `.env`

```powershell
@"
OLLAMA_HOST=http://127.0.0.1:11434
TUTOR_MODEL=llama3.1:8b
EMBEDDING_MODEL=nomic-embed-text
CHROMA_DIR=./data/chroma
MEMORY_DB=./data/memory.db
DOCS_DIR=./data/docs
TOP_K=3
MAX_AGENT_STEPS=4
"@ | Set-Content .env
```

4) Pull models

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

5) Ingest docs

```powershell
.\.venv_local\Scripts\python -m tutor_agent.main ingest
```

6) Run app

Terminal AIM mode:

```powershell
.\.venv_local\Scripts\python -m tutor_agent.main aim --user-id learner
```

Desktop mode:

```powershell
.\.venv_local\Scripts\python -m tutor_agent.main desktop --user-id learner
```

Desktop launcher:

```cmd
run_desktop.cmd learner
```

## AIM/TUI Commands

- `/ask <message>`
- `/paste [lang]`
- `/run [lang]`
- `/search <query>`
- `/quiz <topic> [easy|medium|hard]`
- `/topics`
- `/progress`
- `/help`
- `/quit`

Paste mode ends when you enter a line containing only `EOF`.

## Desktop Customization

Sounds (optional):
- `assets/sounds/aim-send.mp3`
- `assets/sounds/aim-instant-message.mp3`

App icon source (optional):
- `assets/branding/app-icon.png`
- `assets/branding/app-icon.jpg`
- `assets/branding/app-icon.jpeg`
- `assets/branding/app-icon.ico`

## Build Desktop EXE

```cmd
build_desktop_exe.cmd
```

Output (onedir default):
- `release\CodeElephantTutor\CodeElephantTutor.exe`

One-file build:

```cmd
build_desktop_exe.cmd -OneFile
```

Output (onefile):
- `release\CodeElephantTutor.exe`

## Installer UI and Installer EXE

Run installer UI script:

```cmd
install_desktop.cmd
```

No-UI detection mode:

```cmd
install_desktop.cmd -NoUi
```

Build installer EXE:

```cmd
build_installer_exe.cmd
```

Run installer EXE:
- `release\CodeElephantInstaller.exe`

Optional installer icon:
- `assets/branding/installer-icon.ico`

## Docker Workflow

Bring up stack and ingest:

```powershell
.\run_docker.ps1 -Action up
```

Chat in container:

```powershell
.\run_docker.ps1 -Action chat -UserId learner
```

GPU mode:

```powershell
.\run_docker.ps1 -Action up -UseGpu
```

## Persistence

- Source docs: `data/docs/`
- Vector store: `data/chroma/`
- Learner memory: `data/memory.db`
- Saved desktop chats: `data/saved_chats/`

Packaged desktop builds (PyInstaller EXE) use a user-local runtime path by default:
- Windows: `%LOCALAPPDATA%\CodeElephantTutor\data\`
- Other OSes: `~/.codeelephanttutor/data/`

This keeps release folders clean and avoids shipping personal chats/progress.

Runtime DB files are intentionally excluded from git tracking.

## Security Notes

- Keep `.env` local and out of source control
- Do not store secrets in `data/docs/`
- Local code executor is guard-railed, but not a full sandbox

## Known Limits

- Local code execution currently supports Python snippets only
- Single-machine/local-user defaults
- Full chat transcripts are not persisted by default
