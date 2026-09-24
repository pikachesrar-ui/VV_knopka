param(
    [ValidateRange(1, 10)]
    [int]$Count = 3,

    [ValidateRange(1, 1440)]
    [int]$IntervalMinutes = 60,

    [ValidateRange(1, 5)]
    [int]$MaxAttemptsPerPublication = 3,

    [ValidateRange(1, 600)]
    [int]$RetryDelaySeconds = 30,

    [switch]$DryRun,

    # A detached launcher uses this switch so a stalled/selected console cannot
    # back-pressure the worker and all of its Python/FFmpeg child processes.
    [switch]$NoConsoleOutput
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = $Utf8NoBom
try { [Console]::OutputEncoding = $Utf8NoBom } catch {}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Runner = Join-Path $PSScriptRoot "run-longrun-task.ps1"
$SchedulerDir = Join-Path $ProjectRoot "runtime\scheduler"
$StatePath = Join-Path $SchedulerDir "manual-batch-state.json"
$BatchLockPath = Join-Path $SchedulerDir "manual-batch.lock"
$BatchLogPath = Join-Path $SchedulerDir "manual-batch.log"
$PowerShellExe = (Get-Command powershell.exe -ErrorAction Stop).Source

function Write-BatchHost {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Message)
    if (-not $NoConsoleOutput) {
        Write-Host $Message
    }
}

function Write-BatchLog {
    param([Parameter(Mandatory = $true)][string]$Message)
    $Line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $BatchLogPath -Value $Line -Encoding UTF8
    Write-BatchHost $Line
}

function Write-BatchState {
    param(
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][int]$Completed,
        [string]$ErrorMessage = ""
    )
    $Payload = [ordered]@{
        schema_version = 2
        status = $Status
        pid = $PID
        requested = $Count
        completed = $Completed
        interval_minutes = $IntervalMinutes
        max_attempts_per_publication = $MaxAttemptsPerPublication
        started_at = $Script:StartedAt.ToString("o")
        updated_at = [DateTimeOffset]::Now.ToString("o")
        suppress_scheduled_until = $Script:SuppressUntil.ToString("o")
        error = if ($ErrorMessage) { $ErrorMessage } else { $null }
    }
    $Temporary = "$StatePath.tmp-$PID"
    $Payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Temporary -Encoding UTF8
    Move-Item -LiteralPath $Temporary -Destination $StatePath -Force
}

if (-not (Test-Path $Runner)) {
    throw "Long-run runner was not found at $Runner"
}

if ($DryRun) {
    Write-BatchHost "DRY RUN: one click would publish $Count videos, approximately $IntervalMinutes minutes apart."
    Write-BatchHost "Runner   : $Runner"
    Write-BatchHost "Retries  : up to $MaxAttemptsPerPublication attempts per successful publication."
    Write-BatchHost "Schedule : normal 01:30/03:30/05:30 runs would be suppressed until 06:30 after this batch."
    exit 0
}

New-Item -ItemType Directory -Force -Path $SchedulerDir | Out-Null
$BatchLockStream = $null
$Completed = 0
$Script:StartedAt = [DateTimeOffset]::Now
$Cutoff = (Get-Date).Date.AddHours(6).AddMinutes(30)
if ((Get-Date) -ge $Cutoff) {
    $Cutoff = $Cutoff.AddDays(1)
}
$Script:SuppressUntil = [DateTimeOffset]$Cutoff

try {
    try {
        $BatchLockStream = [System.IO.File]::Open(
            $BatchLockPath,
            [System.IO.FileMode]::OpenOrCreate,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
    }
    catch [System.IO.IOException] {
        Write-BatchHost "VV Knopka batch is already running. A second batch was not started."
        exit 75
    }

    Write-BatchState -Status "running" -Completed 0
    Write-BatchLog "START: manual batch requested $Count publications, interval=$IntervalMinutes minutes."
    Write-BatchLog ("Night scheduler suppression until {0}." -f $Script:SuppressUntil.ToString("yyyy-MM-dd HH:mm:ss zzz"))

    $PublishNotBefore = ""
    for ($Index = 1; $Index -le $Count; $Index++) {
        $PublicationSucceeded = $false
        $LastExitCode = 0

        for ($Attempt = 1; $Attempt -le $MaxAttemptsPerPublication; $Attempt++) {
            Write-BatchLog (
                "CYCLE {0}/{1}, ATTEMPT {2}/{3}: starting safe long-run generation/publication." -f
                $Index, $Count, $Attempt, $MaxAttemptsPerPublication
            )
            $Arguments = @(
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", $Runner,
                "-ManualBatch"
            )
            if ($NoConsoleOutput) {
                $Arguments += "-NoConsoleOutput"
            }
            if ($PublishNotBefore) {
                $Arguments += @("-PublishNotBefore", $PublishNotBefore)
            }
            & $PowerShellExe @Arguments
            $LastExitCode = $LASTEXITCODE
            if ($LastExitCode -eq 0) {
                $PublicationSucceeded = $true
                break
            }

            if ($Attempt -lt $MaxAttemptsPerPublication) {
                Write-BatchLog (
                    "RETRY: cycle {0}/{1} attempt {2} exited {3}; retrying the same missing publication in {4}s." -f
                    $Index, $Count, $Attempt, $LastExitCode, $RetryDelaySeconds
                )
                Start-Sleep -Seconds $RetryDelaySeconds
            }
        }

        if (-not $PublicationSucceeded) {
            throw (
                "manual batch cycle {0} did not publish after {1} attempts; last exit code {2}" -f
                $Index, $MaxAttemptsPerPublication, $LastExitCode
            )
        }

        $Completed++
        Write-BatchState -Status "running" -Completed $Completed
        Write-BatchLog ("CYCLE {0}/{1}: publication completed." -f $Index, $Count)
        $PublishNotBefore = [DateTimeOffset]::Now.AddMinutes($IntervalMinutes).ToString("o")
    }

    Write-BatchState -Status "completed" -Completed $Completed
    Write-BatchLog "SUCCESS: manual batch completed all $Completed publications."
    Write-BatchHost ""
    Write-BatchHost "All requested VV Knopka publications completed."
}
catch {
    $Message = $_.Exception.Message
    # A failed batch must not suppress the normal night recovery schedule.
    $Script:SuppressUntil = [DateTimeOffset]::Now
    Write-BatchState -Status "failed" -Completed $Completed -ErrorMessage $Message
    Write-BatchLog ("FAIL: {0}. Normal night schedule remains available." -f $Message)
    Write-BatchHost ""
    Write-BatchHost "Batch stopped safely. Existing receipts/backlog prevent duplicate uploads."
    exit 1
}
finally {
    if ($null -ne $BatchLockStream) {
        $BatchLockStream.Dispose()
    }
    try { Remove-Item -LiteralPath $BatchLockPath -Force -ErrorAction SilentlyContinue } catch {}
}
