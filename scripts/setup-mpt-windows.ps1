$ErrorActionPreference = "Stop"

function Assert-LastExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$uvExe = Join-Path $repoRoot ".venv\Scripts\uv.exe"
$mptDir = Join-Path $repoRoot "MoneyPrinterTurbo"

if (-not (Test-Path $vvPython)) {
    throw "VV_knopka virtual environment is missing. Run scripts/setup-windows.ps1 first."
}

if (-not (Test-Path $uvExe)) {
    Write-Host "Installing uv into the VV_knopka helper environment..."
    & $vvPython -m pip install --upgrade uv
    Assert-LastExitCode "uv installation"
}

if (-not (Test-Path $mptDir)) {
    Write-Host "Cloning official MoneyPrinterTurbo upstream..."
    & git clone --depth 1 https://github.com/harry0703/MoneyPrinterTurbo.git $mptDir
    Assert-LastExitCode "MoneyPrinterTurbo clone"
} else {
    Write-Host "MoneyPrinterTurbo already exists; updating with fast-forward only..."
    Push-Location $mptDir
    try {
        & git pull --ff-only
        Assert-LastExitCode "MoneyPrinterTurbo update"
    } finally {
        Pop-Location
    }
}

Push-Location $mptDir
try {
    Write-Host "Ensuring Python 3.11 for MoneyPrinterTurbo..."
    & $uvExe python install 3.11
    Assert-LastExitCode "MPT Python installation"

    Write-Host "Installing locked MoneyPrinterTurbo dependencies..."
    & $uvExe sync --frozen --python 3.11
    Assert-LastExitCode "MPT dependency installation"

    if (-not (Test-Path "config.toml")) {
        Copy-Item "config.example.toml" "config.toml"
        Write-Host "Created MoneyPrinterTurbo/config.toml"
    } else {
        Write-Host "MoneyPrinterTurbo/config.toml already exists; keeping it."
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "MoneyPrinterTurbo setup complete."
Write-Host "Next: add PEXELS_API_KEY to VV_knopka/.env, then run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\configure-mpt-windows.ps1"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\start-mpt-api.ps1"
