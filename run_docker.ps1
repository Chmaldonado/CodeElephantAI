param(
    [ValidateSet("up", "down", "ingest", "chat", "chat-plain", "logs")]
    [string]$Action = "up",
    [string]$UserId = "learner",
    [switch]$ForcePullModels
)

$ErrorActionPreference = "Stop"

function Ensure-Model {
    param(
        [string]$ModelName
    )

    if ($ForcePullModels) {
        Write-Host "Force-pulling model: $ModelName" -ForegroundColor Yellow
        docker exec tutor-ollama ollama pull $ModelName
        return
    }

    docker exec tutor-ollama ollama show $ModelName *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Model already present: $ModelName" -ForegroundColor DarkGreen
        return
    }

    Write-Host "Pulling missing model: $ModelName" -ForegroundColor Yellow
    docker exec tutor-ollama ollama pull $ModelName
}

function Ensure-RequiredModels {
    Ensure-Model -ModelName "nomic-embed-text"
    Ensure-Model -ModelName "llama3.1:8b"
}

switch ($Action) {
    "up" {
        docker compose up -d --remove-orphans ollama
        Ensure-RequiredModels
        docker compose run --rm tutor python -m tutor_agent.main ingest
        Write-Host "Docker stack is ready. Start chat with:" -ForegroundColor Green
        Write-Host "  .\run_docker.ps1 -Action chat -UserId $UserId"
    }
    "chat" {
        docker compose run --rm --build tutor python -m tutor_agent.main tui --user-id $UserId
    }
    "chat-plain" {
        docker compose run --rm --build tutor python -m tutor_agent.main chat --user-id $UserId
    }
    "ingest" {
        docker compose run --rm --build tutor python -m tutor_agent.main ingest
    }
    "logs" {
        docker compose logs -f ollama
    }
    "down" {
        docker compose down --remove-orphans
    }
}
