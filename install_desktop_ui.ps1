param(
    [string]$AppName = "CodeElephantTutor",
    [string]$TutorModel = "llama3.1:8b",
    [string]$EmbeddingModel = "nomic-embed-text",
    [switch]$NoUi
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

function Initialize-Winget {
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wingetCmd) {
        return $false
    }
    try {
        & winget --version *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Test-OllamaInstalled {
    return [bool](Get-Command ollama -ErrorAction SilentlyContinue)
}

function Ensure-OllamaInstalled {
    param(
        [bool]$HasWinget
    )
    if (Test-OllamaInstalled) {
        return
    }
    if (-not $HasWinget) {
        throw "Ollama is missing and winget is unavailable. Install Ollama manually."
    }
    & winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Ollama via winget (exit code $LASTEXITCODE)."
    }
    $env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
    if (-not (Test-OllamaInstalled)) {
        throw "Ollama installed but not in PATH yet. Reopen terminal and rerun installer."
    }
}

function Ensure-OllamaReady {
    for ($i = 0; $i -lt 8; $i++) {
        & ollama list *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        if ($i -eq 0) {
            Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
        }
        Start-Sleep -Seconds 2
    }
    throw "Could not connect to Ollama service."
}

function Get-InstalledModels {
    $output = & ollama list 2>$null
    if ($LASTEXITCODE -ne 0) {
        return @{}
    }
    $models = @{}
    foreach ($line in $output) {
        $trimmed = $line.Trim()
        if (-not $trimmed) {
            continue
        }
        if ($trimmed -match '^NAME\s+') {
            continue
        }
        $name = ($trimmed -split '\s+')[0]
        if ($name) {
            $models[$name] = $true
        }
    }
    return $models
}

function Ensure-Model {
    param([string]$ModelName)
    $models = Get-InstalledModels
    if ($models.ContainsKey($ModelName)) {
        return
    }
    & ollama pull $ModelName
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to pull model '$ModelName'."
    }
}

function Ensure-DesktopShortcut {
    param(
        [string]$ShortcutName,
        [string]$TargetPath,
        [string]$WorkingDirectory
    )
    $desktop = Get-DesktopFolderPath
    $shortcutPath = Join-Path $desktop "$ShortcutName.lnk"
    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.Save()
}

function Get-DesktopFolderPath {
    $desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        $desktop = [Environment]::GetFolderPath("Desktop")
    }
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        return $ProjectRoot
    }
    return $desktop
}

function Resolve-BaseDirectory {
    $scriptPath = $MyInvocation.MyCommand.Path
    if ([string]::IsNullOrWhiteSpace($scriptPath)) {
        $scriptPath = $PSCommandPath
    }
    if (-not [string]::IsNullOrWhiteSpace($scriptPath) -and (Test-Path $scriptPath)) {
        return (Split-Path -Parent $scriptPath)
    }
    return (Get-Location).Path
}

function Resolve-AppExePath {
    param(
        [string]$BaseDir,
        [string]$TargetApp
    )

    $parent = Split-Path -Parent $BaseDir
    $candidates = @(
        (Join-Path $BaseDir "release\$TargetApp\$TargetApp.exe"),
        (Join-Path $BaseDir "$TargetApp\$TargetApp.exe"),
        (Join-Path $parent "release\$TargetApp\$TargetApp.exe"),
        (Join-Path $parent "$TargetApp\$TargetApp.exe")
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }
    return $candidates[0]
}

function Get-InstallerState {
    param(
        [string]$ExePath,
        [string]$ShortcutPath,
        [string]$TutorModelName,
        [string]$EmbeddingModelName
    )

    $state = [ordered]@{
        ExeExists            = (Test-Path $ExePath)
        ShortcutExists       = (Test-Path $ShortcutPath)
        OllamaInstalled      = (Test-OllamaInstalled)
        OllamaReady          = $false
        TutorModelInstalled  = $false
        EmbedModelInstalled  = $false
    }

    if ($state.OllamaInstalled) {
        try {
            Ensure-OllamaReady
            $state.OllamaReady = $true
            $models = Get-InstalledModels
            $state.TutorModelInstalled = $models.ContainsKey($TutorModelName)
            $state.EmbedModelInstalled = $models.ContainsKey($EmbeddingModelName)
        }
        catch {
            $state.OllamaReady = $false
        }
    }

    $state["NoDownloadsNeeded"] = (
        $state.OllamaInstalled -and $state.TutorModelInstalled -and $state.EmbedModelInstalled
    )
    return $state
}

$ProjectRoot = Resolve-BaseDirectory
$ExePath = Resolve-AppExePath -BaseDir $ProjectRoot -TargetApp $AppName
$Desktop = Get-DesktopFolderPath
$ShortcutPath = Join-Path $Desktop "$AppName.lnk"
$HasWinget = Initialize-Winget

if ($NoUi) {
    $state = Get-InstallerState -ExePath $ExePath -ShortcutPath $ShortcutPath -TutorModelName $TutorModel -EmbeddingModelName $EmbeddingModel
    $state.GetEnumerator() | ForEach-Object { Write-Host "$($_.Key): $($_.Value)" }
    exit 0
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$form = New-Object System.Windows.Forms.Form
$form.Text = "CodeElephant Installer"
$form.StartPosition = "CenterScreen"
$form.Size = New-Object System.Drawing.Size(760, 560)
$form.MinimumSize = New-Object System.Drawing.Size(760, 560)

$title = New-Object System.Windows.Forms.Label
$title.Text = "CodeElephant Desktop Installer"
$title.Font = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
$title.AutoSize = $true
$title.Location = New-Object System.Drawing.Point(18, 14)
$form.Controls.Add($title)

$subtitle = New-Object System.Windows.Forms.Label
$subtitle.Text = "Select what to install. Existing components are auto-detected."
$subtitle.AutoSize = $true
$subtitle.Location = New-Object System.Drawing.Point(20, 42)
$form.Controls.Add($subtitle)

$group = New-Object System.Windows.Forms.GroupBox
$group.Text = "Components"
$group.Location = New-Object System.Drawing.Point(20, 68)
$group.Size = New-Object System.Drawing.Size(705, 220)
$form.Controls.Add($group)

$chkOllama = New-Object System.Windows.Forms.CheckBox
$chkOllama.Text = "Install Ollama"
$chkOllama.Location = New-Object System.Drawing.Point(18, 34)
$chkOllama.AutoSize = $true
$group.Controls.Add($chkOllama)

$lblOllama = New-Object System.Windows.Forms.Label
$lblOllama.Location = New-Object System.Drawing.Point(250, 35)
$lblOllama.Size = New-Object System.Drawing.Size(430, 24)
$group.Controls.Add($lblOllama)

$chkTutor = New-Object System.Windows.Forms.CheckBox
$chkTutor.Text = "Download tutor model ($TutorModel)"
$chkTutor.Location = New-Object System.Drawing.Point(18, 75)
$chkTutor.AutoSize = $true
$group.Controls.Add($chkTutor)

$lblTutor = New-Object System.Windows.Forms.Label
$lblTutor.Location = New-Object System.Drawing.Point(250, 76)
$lblTutor.Size = New-Object System.Drawing.Size(430, 24)
$group.Controls.Add($lblTutor)

$chkEmbed = New-Object System.Windows.Forms.CheckBox
$chkEmbed.Text = "Download embedding model ($EmbeddingModel)"
$chkEmbed.Location = New-Object System.Drawing.Point(18, 116)
$chkEmbed.AutoSize = $true
$group.Controls.Add($chkEmbed)

$lblEmbed = New-Object System.Windows.Forms.Label
$lblEmbed.Location = New-Object System.Drawing.Point(250, 117)
$lblEmbed.Size = New-Object System.Drawing.Size(430, 24)
$group.Controls.Add($lblEmbed)

$chkShortcut = New-Object System.Windows.Forms.CheckBox
$chkShortcut.Text = "Create desktop shortcut"
$chkShortcut.Location = New-Object System.Drawing.Point(18, 157)
$chkShortcut.AutoSize = $true
$group.Controls.Add($chkShortcut)

$lblShortcut = New-Object System.Windows.Forms.Label
$lblShortcut.Location = New-Object System.Drawing.Point(250, 158)
$lblShortcut.Size = New-Object System.Drawing.Size(430, 24)
$group.Controls.Add($lblShortcut)

$chkLaunch = New-Object System.Windows.Forms.CheckBox
$chkLaunch.Text = "Launch app after install"
$chkLaunch.Location = New-Object System.Drawing.Point(38, 302)
$chkLaunch.AutoSize = $true
$chkLaunch.Checked = $true
$form.Controls.Add($chkLaunch)

$lblNoDownloads = New-Object System.Windows.Forms.Label
$lblNoDownloads.Location = New-Object System.Drawing.Point(20, 332)
$lblNoDownloads.Size = New-Object System.Drawing.Size(705, 24)
$lblNoDownloads.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($lblNoDownloads)

$txtLog = New-Object System.Windows.Forms.TextBox
$txtLog.Location = New-Object System.Drawing.Point(20, 360)
$txtLog.Size = New-Object System.Drawing.Size(705, 132)
$txtLog.Multiline = $true
$txtLog.ScrollBars = "Vertical"
$txtLog.ReadOnly = $true
$form.Controls.Add($txtLog)

$btnRefresh = New-Object System.Windows.Forms.Button
$btnRefresh.Text = "Refresh"
$btnRefresh.Location = New-Object System.Drawing.Point(360, 503)
$btnRefresh.Size = New-Object System.Drawing.Size(110, 32)
$form.Controls.Add($btnRefresh)

$btnInstall = New-Object System.Windows.Forms.Button
$btnInstall.Text = "Install Selected"
$btnInstall.Location = New-Object System.Drawing.Point(480, 503)
$btnInstall.Size = New-Object System.Drawing.Size(120, 32)
$form.Controls.Add($btnInstall)

$btnClose = New-Object System.Windows.Forms.Button
$btnClose.Text = "Close"
$btnClose.Location = New-Object System.Drawing.Point(610, 503)
$btnClose.Size = New-Object System.Drawing.Size(115, 32)
$form.Controls.Add($btnClose)

function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format "HH:mm:ss"
    $txtLog.AppendText("[$stamp] $Message`r`n")
}

$stateCache = $null

function Refresh-UiState {
    $script:stateCache = Get-InstallerState -ExePath $ExePath -ShortcutPath $ShortcutPath -TutorModelName $TutorModel -EmbeddingModelName $EmbeddingModel

    if (-not $stateCache.ExeExists) {
        $lblNoDownloads.Text = "Build not found: $ExePath"
        $lblNoDownloads.ForeColor = [System.Drawing.Color]::Firebrick
    }
    elseif ($stateCache.NoDownloadsNeeded) {
        $lblNoDownloads.Text = "No downloads are needed. You already have Ollama and both models."
        $lblNoDownloads.ForeColor = [System.Drawing.Color]::DarkGreen
    }
    else {
        $lblNoDownloads.Text = "Downloads are needed for one or more components."
        $lblNoDownloads.ForeColor = [System.Drawing.Color]::DarkOrange
    }

    if ($stateCache.OllamaInstalled) {
        $chkOllama.Checked = $false
        $chkOllama.Enabled = $false
        $lblOllama.Text = "Already installed"
        $lblOllama.ForeColor = [System.Drawing.Color]::DarkGreen
    }
    else {
        $chkOllama.Checked = $true
        $chkOllama.Enabled = $true
        $lblOllama.Text = $(if ($HasWinget) { "Will be installed via winget" } else { "winget unavailable (manual install required)" })
        $lblOllama.ForeColor = $(if ($HasWinget) { [System.Drawing.Color]::DarkOrange } else { [System.Drawing.Color]::Firebrick })
    }

    if ($stateCache.TutorModelInstalled) {
        $chkTutor.Checked = $false
        $chkTutor.Enabled = $false
        $lblTutor.Text = "Already downloaded"
        $lblTutor.ForeColor = [System.Drawing.Color]::DarkGreen
    }
    else {
        $chkTutor.Checked = $true
        $chkTutor.Enabled = $true
        $lblTutor.Text = "Will download from Ollama"
        $lblTutor.ForeColor = [System.Drawing.Color]::DarkOrange
    }

    if ($stateCache.EmbedModelInstalled) {
        $chkEmbed.Checked = $false
        $chkEmbed.Enabled = $false
        $lblEmbed.Text = "Already downloaded"
        $lblEmbed.ForeColor = [System.Drawing.Color]::DarkGreen
    }
    else {
        $chkEmbed.Checked = $true
        $chkEmbed.Enabled = $true
        $lblEmbed.Text = "Will download from Ollama"
        $lblEmbed.ForeColor = [System.Drawing.Color]::DarkOrange
    }

    if ($stateCache.ShortcutExists) {
        $chkShortcut.Checked = $false
        $chkShortcut.Enabled = $true
        $lblShortcut.Text = "Shortcut already exists"
        $lblShortcut.ForeColor = [System.Drawing.Color]::DarkGreen
    }
    else {
        $chkShortcut.Checked = $true
        $chkShortcut.Enabled = $true
        $lblShortcut.Text = "Will create shortcut on Desktop"
        $lblShortcut.ForeColor = [System.Drawing.Color]::DarkOrange
    }

    if (-not $stateCache.ExeExists) {
        $btnInstall.Enabled = $false
    }
    else {
        $btnInstall.Enabled = $true
    }
}

$btnRefresh.Add_Click({
    try {
        Write-Log "Refreshing install state..."
        Refresh-UiState
        Write-Log "State refreshed."
    }
    catch {
        Write-Log "Refresh error: $($_.Exception.Message)"
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, "Refresh Error", "OK", "Error") | Out-Null
    }
})

$btnInstall.Add_Click({
    try {
        $btnInstall.Enabled = $false
        $btnRefresh.Enabled = $false
        $form.UseWaitCursor = $true
        [System.Windows.Forms.Application]::DoEvents()

        $didAnyWork = $false

        if ($chkOllama.Checked) {
            Write-Log "Installing Ollama..."
            Ensure-OllamaInstalled -HasWinget:$HasWinget
            Write-Log "Ollama installed."
            $didAnyWork = $true
        }

        if ($chkTutor.Checked -or $chkEmbed.Checked) {
            Write-Log "Ensuring Ollama service is running..."
            Ensure-OllamaReady
            if ($chkTutor.Checked) {
                Write-Log "Downloading model: $TutorModel"
                Ensure-Model -ModelName $TutorModel
                Write-Log "Model ready: $TutorModel"
                $didAnyWork = $true
            }
            if ($chkEmbed.Checked) {
                Write-Log "Downloading model: $EmbeddingModel"
                Ensure-Model -ModelName $EmbeddingModel
                Write-Log "Model ready: $EmbeddingModel"
                $didAnyWork = $true
            }
        }

        if ($chkShortcut.Checked) {
            Write-Log "Creating desktop shortcut..."
            Ensure-DesktopShortcut -ShortcutName $AppName -TargetPath $ExePath -WorkingDirectory (Split-Path $ExePath -Parent)
            Write-Log "Desktop shortcut created."
            $didAnyWork = $true
        }

        if (-not $didAnyWork) {
            Write-Log "No install actions were needed/selected."
        }

        if ($chkLaunch.Checked -and (Test-Path $ExePath)) {
            Write-Log "Launching desktop app..."
            Start-Process $ExePath -ArgumentList "--user-id learner"
        }

        Refresh-UiState
        Write-Log "Installer complete."
        [System.Windows.Forms.MessageBox]::Show("Installer complete.", "Success", "OK", "Information") | Out-Null
    }
    catch {
        Write-Log "Install error: $($_.Exception.Message)"
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, "Install Error", "OK", "Error") | Out-Null
    }
    finally {
        $form.UseWaitCursor = $false
        $btnInstall.Enabled = $true
        $btnRefresh.Enabled = $true
    }
})

$btnClose.Add_Click({ $form.Close() })

Refresh-UiState
[void]$form.ShowDialog()
