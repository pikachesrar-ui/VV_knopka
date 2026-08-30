param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SchedulerDir = Join-Path $ProjectRoot "runtime\scheduler"
$LogPath = Join-Path $SchedulerDir "longrun-task.log"
$LockPath = Join-Path $SchedulerDir "longrun-task.lock"
$VvExe = Join-Path $ProjectRoot ".venv\Scripts\vv.exe"

New-Item -ItemType Directory -Force -Path $SchedulerDir | Out-Null

function Write-TaskLog {
    param([Parameter(Mandatory = $true)][string]$Message)
    $Line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $LogPath -Value $Line -Encoding UTF8
    Write-Host $Line
}

$LockStream = $null
try {
    try {
        $LockStream = [System.IO.File]::Open(
            $LockPath,
            [System.IO.FileMode]::OpenOrCreate,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
    }
    catch [System.IO.IOException] {
        Write-TaskLog "SKIP: another long-run task already holds the scheduler lock."
        exit 0
    }

    if (-not (Test-Path $VvExe)) {
        throw "vv.exe was not found at $VvExe. Run scripts/setup-windows.ps1 or reinstall the editable package first."
    }

    Set-Location $ProjectRoot
    Write-TaskLog ("START: long-run scheduled task (dry_run={0})." -f [bool]$DryRun)

    & $VvExe status 2>&1 | ForEach-Object { Write-TaskLog ("status: {0}" -f $_) }
    if ($LASTEXITCODE -ne 0) {
        throw "vv status failed with exit code $LASTEXITCODE"
    }

    $LongRunArgs = @("longrun-next")
    if ($DryRun) {
        $LongRunArgs += "--dry-run"
    }

    & $VvExe @LongRunArgs 2>&1 | ForEach-Object { Write-TaskLog ("vv: {0}" -f $_) }
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -ne 0) {
        Write-TaskLog "FAIL: longrun-next exited with code $ExitCode. Resume will retry the same missing slot on the next run."
        exit $ExitCode
    }

    Write-TaskLog "SUCCESS: scheduled longrun-next completed."
    exit 0
}
catch {
    Write-TaskLog ("ERROR: {0}" -f $_.Exception.Message)
    exit 1
}
finally {
    if ($null -ne $LockStream) {
        $LockStream.Dispose()
    }
    try {
        Remove-Item -LiteralPath $LockPath -Force -ErrorAction SilentlyContinue
    }
    catch {
        # The OS handle is the actual lock; a leftover empty file is harmless.
    }
}
