param(
    [string]$InstallerName = "CodeElephantInstaller",
    [string]$SourceScript = "install_desktop_ui.ps1"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$SourcePath = Join-Path $ProjectRoot $SourceScript
if (-not (Test-Path $SourcePath)) {
    throw "Missing installer source script: $SourcePath"
}

function Ensure-PS2EXE {
    if (Get-Command Invoke-ps2exe -ErrorAction SilentlyContinue) {
        return
    }

    $available = Get-Module -ListAvailable -Name ps2exe | Select-Object -First 1
    if ($available) {
        Import-Module $available.Path -Force
    }

    if (Get-Command Invoke-ps2exe -ErrorAction SilentlyContinue) {
        return
    }

    try {
        Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Scope CurrentUser -Force | Out-Null
    }
    catch {
        # Continue; provider may already exist.
    }

    try {
        Set-PSRepository -Name PSGallery -InstallationPolicy Trusted -ErrorAction SilentlyContinue
    }
    catch {
        # Ignore non-fatal repository policy errors.
    }

    Install-Module -Name ps2exe -Scope CurrentUser -Force -AllowClobber
    Import-Module ps2exe -Force
}

Ensure-PS2EXE

$ReleaseDir = Join-Path $ProjectRoot "release"
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
$OutputExe = Join-Path $ReleaseDir "$InstallerName.exe"

$IconCandidates = @(
    (Join-Path $ProjectRoot "assets\branding\installer-icon.ico")
)
$IconPath = $null
foreach ($candidate in $IconCandidates) {
    if (Test-Path $candidate) {
        $IconPath = $candidate
        break
    }
}

$baseParams = @{
    inputFile  = $SourcePath
    outputFile = $OutputExe
    noConsole  = $true
}

if ($IconPath) {
    $baseParams["iconFile"] = $IconPath
    Write-Host "Using installer icon: $IconPath" -ForegroundColor Green
}
else {
    Write-Host "No installer icon found (optional): assets\\branding\\installer-icon.ico" -ForegroundColor Yellow
}

Write-Host "Building installer executable..." -ForegroundColor Cyan
try {
    Invoke-ps2exe @baseParams -ErrorAction Stop
}
catch {
    if ($baseParams.ContainsKey("iconFile")) {
        Write-Host "Icon build failed, retrying without icon..." -ForegroundColor Yellow
        $baseParams.Remove("iconFile") | Out-Null
        Invoke-ps2exe @baseParams -ErrorAction Stop
    }
    else {
        throw
    }
}

if (-not (Test-Path $OutputExe)) {
    throw "Installer build failed: $OutputExe was not created."
}

Write-Host ""
Write-Host "Installer EXE created:" -ForegroundColor Green
Write-Host "  $OutputExe"
