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
$YouTubeExe = Join-Path $ProjectRoot ".venv\Scripts\vv-youtube.exe"

New-Item -ItemType Directory -Force -Path $SchedulerDir | Out-Null

function Write-TaskLog {
    param([Parameter(Mandatory = $true)][string]$Message)
    $Line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $LogPath -Value $Line -Encoding UTF8
    Write-Host $Line
}

function Invoke-Logged {
    param(
        [Parameter(Mandatory = $true)][string]$Prefix,
        [Parameter(Mandatory = $true)][string]$Exe,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & $Exe @Arguments 2>&1 | ForEach-Object { Write-TaskLog ("{0}: {1}" -f $Prefix, $_) }
    return $LASTEXITCODE
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
    if (-not (Test-Path $YouTubeExe)) {
        throw "vv-youtube.exe was not found at $YouTubeExe. Pull latest code and reinstall with pip install -e .[dev]."
    }

    Set-Location $ProjectRoot
    Write-TaskLog ("START: long-run scheduled task (dry_run={0})." -f [bool]$DryRun)

    $ExitCode = Invoke-Logged -Prefix "status" -Exe $VvExe -Arguments @("status")
    if ($ExitCode -ne 0) {
        throw "vv status failed with exit code $ExitCode"
    }

    $ExitCode = Invoke-Logged -Prefix "youtube-status" -Exe $YouTubeExe -Arguments @("status")
    if ($ExitCode -ne 0) {
        throw "vv-youtube status failed with exit code $ExitCode"
    }

    # First heal one older failed/pending publication, if any. In dry-run this is
    # a preview only. Once the initial backlog has been explicitly uploaded this
    # normally becomes a no-op.
    $PreUploadArgs = @("upload-ready", "--limit", "1")
    if ($DryRun) { $PreUploadArgs += "--dry-run" }
    $ExitCode = Invoke-Logged -Prefix "youtube-pre" -Exe $YouTubeExe -Arguments $PreUploadArgs
    if ($ExitCode -ne 0) {
        Write-TaskLog "FAIL: pending YouTube retry failed; refusing to generate another slot until publication recovers."
        exit $ExitCode
    }

    $LongRunArgs = @("longrun-next")
    if ($DryRun) { $LongRunArgs += "--dry-run" }
    $ExitCode = Invoke-Logged -Prefix "vv" -Exe $VvExe -Arguments $LongRunArgs
    if ($ExitCode -ne 0) {
        Write-TaskLog "FAIL: longrun-next failed. Resume will retry the same missing slot on the next run."
        exit $ExitCode
    }

    # Dry-run cannot create a new ready file, so only preview the existing newest
    # pending upload. Real runs publish the newly rendered newest ready video.
    $PostUploadArgs = @("upload-ready", "--limit", "1", "--newest")
    if ($DryRun) { $PostUploadArgs += "--dry-run" }
    $ExitCode = Invoke-Logged -Prefix "youtube-post" -Exe $YouTubeExe -Arguments $PostUploadArgs
    if ($ExitCode -ne 0) {
        Write-TaskLog "FAIL: generation completed but YouTube upload failed. The next trigger will retry pending publication first."
        exit $ExitCode
    }

    Write-TaskLog "SUCCESS: scheduled generation + YouTube publication completed."
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
