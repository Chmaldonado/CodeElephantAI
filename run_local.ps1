param(
    [string]$UserId = "learner",
    [switch]$SkipIngest,
    [switch]$IngestOnly,
    [switch]$SkipModelChecks
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv_local\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Missing .venv_local. Create it first:" -ForegroundColor Red
    Write-Host "  python -m venv .venv_local"
    Write-Host "  .\.venv_local\Scripts\python -m pip install -e ."
    exit 1
}

if (-not $SkipModelChecks) {
    Write-Host "Checking required Ollama models..." -ForegroundColor Cyan
    & $Python -c "from ollama import Client; c=Client(host='http://127.0.0.1:11434'); c.show('nomic-embed-text'); c.show('llama3.1:8b'); print('Ollama model check passed')"
}

if (-not $SkipIngest) {
    Write-Host "Running RAG ingest..." -ForegroundColor Cyan
    & $Python -m tutor_agent.main ingest
}

if ($IngestOnly) {
    Write-Host "Done (ingest only)." -ForegroundColor Green
    exit 0
}

Write-Host "Starting tutor chat as user '$UserId'..." -ForegroundColor Green
& $Python -m tutor_agent.main chat --user-id $UserId
