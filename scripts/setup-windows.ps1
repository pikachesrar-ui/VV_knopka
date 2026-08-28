$ErrorActionPreference = "Stop"

function Find-Python311 {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $candidate = (& py -3.11 -c "import sys; print(sys.executable)" 2>$null | Select-Object -Last 1)
        if ($LASTEXITCODE -eq 0 -and $candidate) {
            return $candidate.Trim()
        }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        $candidate = (& python -c "import sys; print(sys.executable if sys.version_info >= (3, 11) else '')" 2>$null | Select-Object -Last 1)
        if ($LASTEXITCODE -eq 0 -and $candidate) {
            return $candidate.Trim()
        }
    }

    $knownPaths = @(
        "$env:LocalAppData\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )
    foreach ($candidate in $knownPaths) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "Python 3.11+ was not found. Installing Python 3.11 with uv..."
        & uv python install 3.11 | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "uv failed to install Python 3.11."
        }
        $candidate = (& uv python find 3.11 2>$null | Select-Object -Last 1)
        if ($LASTEXITCODE -eq 0 -and $candidate -and (Test-Path $candidate.Trim())) {
            return $candidate.Trim()
        }
    }

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Python 3.11+ was not found. Installing Python 3.11 with winget..."
        & winget install --id Python.Python.3.11 -e --scope user --accept-package-agreements --accept-source-agreements | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "winget failed to install Python 3.11. Install Python 3.11 manually and rerun this script."
        }

        # The current PowerShell process may not receive the installer's PATH update,
        # so resolve Python again through the launcher and the standard install path.
        if (Get-Command py -ErrorAction SilentlyContinue) {
            $candidate = (& py -3.11 -c "import sys; print(sys.executable)" 2>$null | Select-Object -Last 1)
            if ($LASTEXITCODE -eq 0 -and $candidate) {
                return $candidate.Trim()
            }
        }
        $candidate = "$env:LocalAppData\Programs\Python\Python311\python.exe"
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "Python 3.11+ is required and could not be installed automatically. Install Python 3.11, then rerun this script."
}

function Assert-LastExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE. Setup stopped; later steps were not executed."
    }
}

$pythonExe = Find-Python311
$pythonVersion = & $pythonExe -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
Assert-LastExitCode "Python version check"
Write-Host "Using Python $pythonVersion at $pythonExe"

$venvPython = ".\.venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Removing incompatible existing .venv..."
        Remove-Item -Recurse -Force .venv
    }
}

if (-not (Test-Path $venvPython)) {
    & $pythonExe -m venv .venv
    Assert-LastExitCode "Virtual environment creation"
}

& $venvPython -m pip install --upgrade pip
Assert-LastExitCode "pip upgrade"

& $venvPython -m pip install -e ".[dev]"
Assert-LastExitCode "VV_knopka dependency installation"

# Only create runtime/config files after installation has succeeded.
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env. Put OPENAI_API_KEY there; do not commit it."
} else {
    Write-Host ".env already exists; keeping it unchanged."
}

& $venvPython -m vv_knopka.cli init-pilot
Assert-LastExitCode "Pilot initialization"

& $venvPython -m pytest -q
Assert-LastExitCode "Test suite"

Write-Host ""
Write-Host "VV_knopka setup complete."
Write-Host "Next: add OPENAI_API_KEY to .env, then run:"
Write-Host "  .\.venv\Scripts\vv.exe status"
