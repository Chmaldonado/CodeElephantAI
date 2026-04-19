param(
    [ValidateSet("up", "down", "ingest", "chat", "chat-plain", "topics", "logs")]
    [string]$Action = "up",
    [string]$UserId = "learner",
    [switch]$ForcePullModels,
    [switch]$UseGpu
)

$ErrorActionPreference = "Stop"
$ComposeArgs = @("-f", "docker-compose.yml")
if ($UseGpu) {
    $ComposeArgs += @("-f", "docker-compose.gpu.yml")
}

function Ensure-Model {
    param(
        [string]$ModelName
    )

    if ($ForcePullModels) {
        Write-Host "Force-pulling model: $ModelName" -ForegroundColor Yellow
        docker exec tutor-ollama ollama pull $ModelName
        return
    }

    $models = docker exec tutor-ollama ollama list 2>$null
    if ($LASTEXITCODE -eq 0 -and (($models -join "`n") -match [regex]::Escape($ModelName))) {
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
        docker compose @ComposeArgs up -d --remove-orphans ollama
        Ensure-RequiredModels
        docker compose @ComposeArgs run --rm --build tutor python -m tutor_agent.main ingest
        Write-Host "Docker stack is ready. Start chat with:" -ForegroundColor Green
        if ($UseGpu) {
            Write-Host "  .\run_docker.ps1 -Action chat -UserId $UserId -UseGpu"
        }
        else {
            Write-Host "  .\run_docker.ps1 -Action chat -UserId $UserId"
        }
    }
    "chat" {
        docker compose @ComposeArgs run --rm --build tutor python -m tutor_agent.main aim --user-id $UserId
    }
    "chat-plain" {
        docker compose @ComposeArgs run --rm --build tutor python -m tutor_agent.main chat --user-id $UserId
    }
    "ingest" {
        docker compose @ComposeArgs run --rm --build tutor python -m tutor_agent.main ingest
    }
    "logs" {
        docker compose @ComposeArgs logs -f ollama
    }
    "topics" {
        docker compose @ComposeArgs run --rm --build tutor python -m tutor_agent.main topics --user-id $UserId
    }
    "down" {
        docker compose @ComposeArgs down --remove-orphans
    }
}
