$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$mptDir = Join-Path $repoRoot "MoneyPrinterTurbo"
$mptPython = Join-Path $mptDir ".venv\Scripts\python.exe"

if (-not (Test-Path $mptPython)) {
    throw "MoneyPrinterTurbo environment is missing. Run setup-mpt-windows.ps1 first."
}

Write-Host "Starting MoneyPrinterTurbo API on http://127.0.0.1:8080"
Write-Host "Keep this PowerShell window open while rendering."
Write-Host "API docs: http://127.0.0.1:8080/docs"
Write-Host ""

Push-Location $mptDir
try {
    & $mptPython main.py
    if ($LASTEXITCODE -ne 0) {
        throw "MoneyPrinterTurbo API exited with code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
