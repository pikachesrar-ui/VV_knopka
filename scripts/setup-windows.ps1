$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.11+ is required."
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -e ".[dev]"

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env. Put OPENAI_API_KEY there; do not commit it."
}

& .\.venv\Scripts\python.exe -m vv_knopka.cli init-pilot
& .\.venv\Scripts\python.exe -m pytest -q
