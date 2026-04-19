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
    $models = & ollama list 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Could not query Ollama models. Is Ollama running?" -ForegroundColor Red
        exit 1
    }
    $joined = ($models -join "`n")
    if ($joined -notmatch "llama3\.1:8b") {
        Write-Host "Missing model: llama3.1:8b" -ForegroundColor Red
        Write-Host "Run: ollama pull llama3.1:8b" -ForegroundColor Yellow
        exit 1
    }
    if ($joined -notmatch "nomic-embed-text") {
        Write-Host "Missing model: nomic-embed-text" -ForegroundColor Red
        Write-Host "Run: ollama pull nomic-embed-text" -ForegroundColor Yellow
        exit 1
    }
}

if (-not $SkipIngest) {
    Write-Host "Running RAG ingest..." -ForegroundColor Cyan
    & $Python -m tutor_agent.main ingest
}

if ($IngestOnly) {
    Write-Host "Done (ingest only)." -ForegroundColor Green
    exit 0
}

Write-Host "Starting tutor AIM mode as user '$UserId'..." -ForegroundColor Green
& $Python -m tutor_agent.main aim --user-id $UserId
