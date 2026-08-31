Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-LastExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$UvExe = Join-Path $ProjectRoot ".venv\Scripts\uv.exe"
$AceDir = Join-Path $ProjectRoot "ACE-Step-1.5"

if (-not (Test-Path $VvPython)) {
    throw "VV_knopka virtual environment is missing. Run scripts/setup-windows.ps1 first."
}

if (-not (Test-Path $UvExe)) {
    Write-Host "Installing uv into the VV_knopka helper environment..."
    & $VvPython -m pip install --upgrade uv
    Assert-LastExitCode "uv installation"
}

if (-not (Test-Path $AceDir)) {
    Write-Host "Cloning official ACE-Step 1.5..."
    & git clone https://github.com/ACE-Step/ACE-Step-1.5.git $AceDir
    Assert-LastExitCode "ACE-Step clone"
} else {
    Write-Host "ACE-Step checkout already exists; keeping the current local revision."
    Write-Host "No automatic git pull is performed because production dependencies should not change silently."
}

Push-Location $AceDir
try {
    Write-Host "Ensuring Python 3.11 for ACE-Step..."
    & $UvExe python install 3.11
    Assert-LastExitCode "ACE-Step Python installation"

    Write-Host "Installing ACE-Step dependencies with uv sync..."
    & $UvExe sync --python 3.11
    Assert-LastExitCode "ACE-Step dependency installation"
} finally {
    Pop-Location
}

$CandidateDir = Join-Path $ProjectRoot "runtime\assets\music\candidates"
New-Item -ItemType Directory -Force -Path $CandidateDir | Out-Null

Write-Host ""
Write-Host "ACE-Step setup complete."
Write-Host "Checkout   : $AceDir"
Write-Host "Candidates : $CandidateDir"
Write-Host "API default: http://127.0.0.1:8001"
Write-Host ""
Write-Host "Next command (models may download on first run):"
Write-Host "  .\.venv\Scripts\vv-music.exe generate-library --count 8 --duration 45"
Write-Host ""
Write-Host "The generated WAVs remain candidates only. Production music stays disabled until they are listened to and approved."
