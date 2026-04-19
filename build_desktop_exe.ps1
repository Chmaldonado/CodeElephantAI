param(
    [string]$AppName = "CodeElephantTutor",
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Test-IsValidIco {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path $Path)) {
        return $false
    }
    try {
        $header = Get-Content -Encoding Byte -Path $Path -TotalCount 4
        if ($header.Length -lt 4) {
            return $false
        }
        return ($header[0] -eq 0 -and $header[1] -eq 0 -and $header[2] -eq 1 -and $header[3] -eq 0)
    }
    catch {
        return $false
    }
}

function New-MultiSizeIcoFromImage {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$TargetPath
    )
    Add-Type -AssemblyName System.Drawing
    $source = $null
    $sourceIcon = $null
    $iconFrames = @()
    $writer = $null
    $targetStream = $null
    try {
        $ext = [IO.Path]::GetExtension($SourcePath).ToLowerInvariant()
        if ($ext -eq ".ico") {
            $sourceIcon = New-Object System.Drawing.Icon($SourcePath)
            $source = $sourceIcon.ToBitmap()
        }
        else {
            $source = New-Object System.Drawing.Bitmap($SourcePath)
        }

        $sizes = @(16, 24, 32, 48, 64, 128, 256)
        foreach ($size in $sizes) {
            $frame = New-Object System.Drawing.Bitmap($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $graphics = [System.Drawing.Graphics]::FromImage($frame)
            try {
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $graphics.DrawImage($source, 0, 0, $size, $size)
            }
            finally {
                $graphics.Dispose()
            }

            $memory = New-Object System.IO.MemoryStream
            $frame.Save($memory, [System.Drawing.Imaging.ImageFormat]::Png)
            $iconFrames += [PSCustomObject]@{
                Size = $size
                Data = $memory.ToArray()
            }
            $memory.Dispose()
            $frame.Dispose()
        }

        $targetStream = [System.IO.File]::Open($TargetPath, [System.IO.FileMode]::Create)
        $writer = New-Object System.IO.BinaryWriter($targetStream)
        $writer.Write([UInt16]0)
        $writer.Write([UInt16]1)
        $writer.Write([UInt16]$iconFrames.Count)

        $dataOffset = 6 + (16 * $iconFrames.Count)
        foreach ($entry in $iconFrames) {
            $sizeByte = if ($entry.Size -ge 256) { 0 } else { [byte]$entry.Size }
            $writer.Write([byte]$sizeByte)
            $writer.Write([byte]$sizeByte)
            $writer.Write([byte]0)
            $writer.Write([byte]0)
            $writer.Write([UInt16]1)
            $writer.Write([UInt16]32)
            $writer.Write([UInt32]$entry.Data.Length)
            $writer.Write([UInt32]$dataOffset)
            $dataOffset += $entry.Data.Length
        }

        foreach ($entry in $iconFrames) {
            $writer.Write($entry.Data)
        }
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($writer) { $writer.Dispose() }
        if ($targetStream) { $targetStream.Dispose() }
        if ($sourceIcon) { $sourceIcon.Dispose() }
        if ($source) { $source.Dispose() }
    }
}

function Stop-RunningAppProcess {
    param([Parameter(Mandatory = $true)][string]$ProcessName)
    $running = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
    if (-not $running) {
        return
    }
    Write-Host "Stopping running process: $ProcessName.exe" -ForegroundColor Yellow
    $running | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 700
}

function Remove-PathWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$Attempts = 5,
        [int]$DelayMs = 700
    )
    if (-not (Test-Path $Path)) {
        return $true
    }
    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
            return $true
        }
        catch {
            if ($i -ge $Attempts) {
                return $false
            }
            Start-Sleep -Milliseconds $DelayMs
        }
    }
    return $false
}

function Resolve-IconCandidates {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRootPath,
        [Parameter(Mandatory = $true)][string]$ReleaseDirPath
    )
    return @(
        (Join-Path $ProjectRootPath "assets\branding\app-icon.png"),
        (Join-Path $ProjectRootPath "assets\branding\app-icon.jpg"),
        (Join-Path $ProjectRootPath "assets\branding\app-icon.jpeg"),
        (Join-Path $ProjectRootPath "assets\branding\app-icon.ico"),
        (Join-Path $ProjectRootPath "assets\app-icon.png"),
        (Join-Path $ProjectRootPath "assets\app-icon.jpg"),
        (Join-Path $ProjectRootPath "assets\app-icon.jpeg"),
        (Join-Path $ProjectRootPath "assets\app-icon.ico"),
        (Join-Path $ReleaseDirPath "assets\branding\app-icon.png"),
        (Join-Path $ReleaseDirPath "assets\branding\app-icon.jpg"),
        (Join-Path $ReleaseDirPath "assets\branding\app-icon.jpeg"),
        (Join-Path $ReleaseDirPath "assets\branding\app-icon.ico")
    )
}

function Save-IconToPersistentBranding {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$BrandingDir
    )
    $ext = [IO.Path]::GetExtension($SourcePath).ToLowerInvariant()
    if (-not $ext) {
        $ext = ".png"
    }
    $dest = Join-Path $BrandingDir ("app-icon" + $ext)
    Copy-Item -LiteralPath $SourcePath -Destination $dest -Force
    return $dest
}

$Python = Join-Path $ProjectRoot ".venv_local\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Missing .venv_local. Create it first:" -ForegroundColor Red
    Write-Host "  python -m venv .venv_local"
    Write-Host "  .\.venv_local\Scripts\python -m pip install -e ."
    exit 1
}

Write-Host "Checking PyInstaller..." -ForegroundColor Cyan
& $Python -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller not found; installing..." -ForegroundColor Yellow
    & $Python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install PyInstaller."
    }
}

$BuildMode = "--onedir"
if ($OneFile) {
    $BuildMode = "--onefile"
}

$ReleaseRoot = Join-Path $ProjectRoot "release"
$ReleaseDir = Join-Path $ReleaseRoot $AppName
$ReleaseExe = Join-Path $ReleaseRoot "$AppName.exe"
$PersistentBrandingDir = Join-Path $ProjectRoot "assets\branding"
New-Item -ItemType Directory -Force -Path $PersistentBrandingDir | Out-Null

$IconPath = $null
foreach ($candidate in (Resolve-IconCandidates -ProjectRootPath $ProjectRoot -ReleaseDirPath $ReleaseDir)) {
    if (Test-Path $candidate) {
        $IconPath = $candidate
        break
    }
}

if ($IconPath) {
    $iconFullPath = [IO.Path]::GetFullPath($IconPath)
    $releaseFullPath = [IO.Path]::GetFullPath($ReleaseRoot)
    $brandingFullPath = [IO.Path]::GetFullPath($PersistentBrandingDir)
    if (
        $iconFullPath.StartsWith($releaseFullPath, [System.StringComparison]::OrdinalIgnoreCase) -or
        -not $iconFullPath.StartsWith($brandingFullPath, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        $IconPath = Save-IconToPersistentBranding -SourcePath $IconPath -BrandingDir $PersistentBrandingDir
        Write-Host "Saved icon to persistent path: $IconPath" -ForegroundColor Yellow
    }
}

$ResolvedIconPath = $null
if ($IconPath) {
    $NormalizedIconPath = Join-Path $ProjectRoot "build\app-icon.normalized.ico"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $NormalizedIconPath) | Out-Null
    if ((New-MultiSizeIcoFromImage -SourcePath $IconPath -TargetPath $NormalizedIconPath) -and (Test-IsValidIco -Path $NormalizedIconPath)) {
        $ResolvedIconPath = $NormalizedIconPath
        Write-Host "Prepared multi-size app icon from: $IconPath" -ForegroundColor Green
    }
    else {
        if (([IO.Path]::GetExtension($IconPath)).ToLowerInvariant() -eq ".ico" -and (Test-IsValidIco -Path $IconPath)) {
            $ResolvedIconPath = $IconPath
            Write-Host "Using existing ICO as-is: $IconPath" -ForegroundColor Yellow
        }
        else {
            Write-Host "Icon exists but could not be converted to a valid multi-size ICO. Building with default icon." -ForegroundColor Yellow
        }
    }
}

Stop-RunningAppProcess -ProcessName $AppName
if ($OneFile) {
    if (-not (Remove-PathWithRetry -Path $ReleaseExe)) {
        throw "Could not remove locked output file: $ReleaseExe. Close the app and retry."
    }
}
else {
    if (-not (Remove-PathWithRetry -Path $ReleaseDir)) {
        throw "Could not remove locked output folder: $ReleaseDir. Close the app and retry."
    }
}

$PyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    $BuildMode,
    "--name", $AppName,
    "--distpath", (Join-Path $ProjectRoot "release"),
    "--workpath", (Join-Path $ProjectRoot "build"),
    "--specpath", (Join-Path $ProjectRoot "build"),
    "--collect-all", "pygments",
    "--collect-all", "chromadb",
    "--collect-all", "ollama",
    "tutor_agent\desktop_entry.py"
)

if ($ResolvedIconPath) {
    $PyInstallerArgs = @("-m", "PyInstaller", "--icon", $ResolvedIconPath) + $PyInstallerArgs[2..($PyInstallerArgs.Length - 1)]
    Write-Host "Using icon: $ResolvedIconPath" -ForegroundColor Green
}
else {
    Write-Host "No app icon found (looked in assets\\branding and assets\\). Building with default icon." -ForegroundColor Yellow
}

Write-Host "Building desktop executable..." -ForegroundColor Cyan
& $Python @PyInstallerArgs
if ($LASTEXITCODE -ne 0) {
    Stop-RunningAppProcess -ProcessName $AppName
    Start-Sleep -Milliseconds 900
    & $Python @PyInstallerArgs
}
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

if ($OneFile) {
    $ReleaseDir = Join-Path $ProjectRoot "release"
}

$TargetAssets = Join-Path $ReleaseDir "assets"
New-Item -ItemType Directory -Force -Path (Join-Path $TargetAssets "sounds") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $TargetAssets "branding") | Out-Null

$SourceSounds = Join-Path $ProjectRoot "assets\sounds"
$SourceBranding = Join-Path $ProjectRoot "assets\branding"
if (Test-Path $SourceSounds) {
    Copy-Item -Path (Join-Path $SourceSounds "*") -Destination (Join-Path $TargetAssets "sounds") -Recurse -Force
}
if (Test-Path $SourceBranding) {
    Copy-Item -Path (Join-Path $SourceBranding "*") -Destination (Join-Path $TargetAssets "branding") -Recurse -Force
}
if ($ResolvedIconPath) {
    Copy-Item -Path $ResolvedIconPath -Destination (Join-Path $TargetAssets "branding\app-icon.ico") -Force
}

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
if ($OneFile) {
    Write-Host "Executable: release\$AppName.exe"
}
else {
    Write-Host "Executable: release\$AppName\$AppName.exe"
}
Write-Host "Place custom icon at: assets\branding\app-icon.png (or .jpg/.jpeg/.ico)"
Write-Host "This source icon is preserved across builds."
Write-Host "Drop sound files here: assets\sounds\aim-send.mp3 and assets\sounds\aim-instant-message.mp3"
