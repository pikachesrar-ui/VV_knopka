param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AceDir = Join-Path $ProjectRoot "ACE-Step-1.5"
$UvExe = Join-Path $ProjectRoot ".venv\Scripts\uv.exe"
$AceApiExe = Join-Path $AceDir ".venv\Scripts\acestep-api.exe"

if ($DryRun) {
    Write-Host "DRY RUN: ACE-Step API launcher"
    Write-Host "Checkout: $AceDir"
    Write-Host "URL     : http://127.0.0.1:8001"
    Write-Host "No process was started."
    exit 0
}

if (-not (Test-Path $AceDir)) {
    throw "ACE-Step checkout is missing. Run scripts/setup-acestep-windows.ps1 first."
}

Write-Host "Starting ACE-Step API at http://127.0.0.1:8001"
Write-Host "This manual launcher is for testing/debugging; vv-music can start the API automatically."
Write-Host "The first launch may download model files and can take a while."
Write-Host ""

Push-Location $AceDir
try {
    if (Test-Path $AceApiExe) {
        & $AceApiExe
    } elseif (Test-Path $UvExe) {
        & $UvExe run acestep-api
    } else {
        throw "Neither acestep-api.exe nor VV_knopka's uv.exe was found. Re-run setup-acestep-windows.ps1."
    }
    if ($LASTEXITCODE -ne 0) {
        throw "ACE-Step API exited with code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
