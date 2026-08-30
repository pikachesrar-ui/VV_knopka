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

function Get-PendingUploadCount {
    $Output = & $YouTubeExe "pending-count" 2>&1
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -ne 0) {
        $Output | ForEach-Object { Write-TaskLog ("youtube-pending: {0}" -f $_) }
        throw "vv-youtube pending-count failed with exit code $ExitCode"
    }
    $Text = (($Output | Select-Object -Last 1) | Out-String).Trim()
    $Count = 0
    if (-not [int]::TryParse($Text, [ref]$Count)) {
        throw "Could not parse pending upload count from: $Text"
    }
    return $Count
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

    # While any ready backlog exists, each trigger spends its single publication
    # opportunity on exactly one old/pending video and does NOT generate another
    # slot. This drains the backlog and keeps scheduled upload pressure <= 3/day.
    $PendingBefore = Get-PendingUploadCount
    Write-TaskLog ("youtube-pending: {0} ready uploads before this trigger." -f $PendingBefore)
    if ($PendingBefore -gt 0) {
        $BacklogArgs = @("upload-ready", "--limit", "1")
        if ($DryRun) { $BacklogArgs += "--dry-run" }
        $ExitCode = Invoke-Logged -Prefix "youtube-backlog" -Exe $YouTubeExe -Arguments $BacklogArgs
        if ($ExitCode -ne 0) {
            Write-TaskLog "FAIL: pending YouTube upload is deferred/failed; refusing to generate another slot until publication recovers."
            exit $ExitCode
        }

        $PendingAfter = Get-PendingUploadCount
        Write-TaskLog ("BACKLOG: handled one pending upload; {0} remain. Skipping generation this trigger." -f $PendingAfter)
        exit 0
    }

    $LongRunArgs = @("longrun-next")
    if ($DryRun) { $LongRunArgs += "--dry-run" }
    $ExitCode = Invoke-Logged -Prefix "vv" -Exe $VvExe -Arguments $LongRunArgs
    if ($ExitCode -ne 0) {
        Write-TaskLog "FAIL: longrun-next failed. Resume will retry the same missing slot on the next run."
        exit $ExitCode
    }

    # Dry-run cannot create a new ready file, so this only previews current state.
    # Real runs publish the newly rendered newest ready video.
    $PostUploadArgs = @("upload-ready", "--limit", "1", "--newest")
    if ($DryRun) { $PostUploadArgs += "--dry-run" }
    $ExitCode = Invoke-Logged -Prefix "youtube-post" -Exe $YouTubeExe -Arguments $PostUploadArgs
    if ($ExitCode -ne 0) {
        Write-TaskLog "FAIL: generation completed but YouTube upload is deferred/failed. The next trigger will drain pending publication first."
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
