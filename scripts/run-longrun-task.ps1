param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Task Scheduler can launch Windows PowerShell/Python without an interactive UTF-8
# console. YouTube titles may contain Cyrillic and emoji, so force UTF-8 for Python
# native-command output before anything is piped into the scheduler log.
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = $Utf8NoBom
try {
    [Console]::OutputEncoding = $Utf8NoBom
}
catch {
    # A scheduled/background PowerShell host may not expose a normal console handle.
    # PYTHONIOENCODING/PYTHONUTF8 above are the important guarantees for vv executables.
}

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

    # Windows PowerShell may surface redirected native stderr as ErrorRecord objects.
    # Do not let global ErrorActionPreference=Stop terminate the runner before we can
    # inspect the native process exit code. Fail-closed decisions remain below.
    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $Output = @(& $Exe @Arguments 2>&1)
        $ExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

    $Output | ForEach-Object { Write-TaskLog ("{0}: {1}" -f $Prefix, $_) }
    return $ExitCode
}

function Get-PendingUploadCount {
    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $Output = @(& $YouTubeExe "pending-count" 2>&1)
        $ExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

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

    # Verification is intentionally done at the beginning of the NEXT real trigger,
    # not seconds after an upload. This gives YouTube time to finish processing and
    # avoids treating normal propagation delay as a missing/failed video. Dry-run CI
    # has no local OAuth material, so observability calls are skipped there.
    if (-not $DryRun) {
        $ExitCode = Invoke-Logged -Prefix "youtube-verify" -Exe $YouTubeExe -Arguments @("verify")
        if ($ExitCode -ne 0) {
            Write-TaskLog "FAIL: a previous YouTube publication is failed/missing or verification could not complete. Refusing new generation/upload until inspected."
            exit $ExitCode
        }

        # Statistics are useful telemetry, not a publication safety gate. A temporary
        # analytics/read/output failure is logged but must not stop a healthy backlog drain.
        $ExitCode = Invoke-Logged -Prefix "youtube-stats" -Exe $YouTubeExe -Arguments @("stats")
        if ($ExitCode -ne 0) {
            Write-TaskLog ("WARN: YouTube statistics collection failed with exit code {0}; continuing publication workflow." -f $ExitCode)
        }
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
