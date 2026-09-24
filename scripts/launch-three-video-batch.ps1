param(
    [ValidateRange(1, 10)]
    [int]$Count = 3,

    [ValidateRange(1, 1440)]
    [int]$IntervalMinutes = 60,

    [ValidateRange(1, 5)]
    [int]$MaxAttemptsPerPublication = 3,

    [ValidateRange(1, 600)]
    [int]$RetryDelaySeconds = 30,

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = $Utf8NoBom
try { [Console]::OutputEncoding = $Utf8NoBom } catch {}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$WorkerScript = Join-Path $PSScriptRoot "start-three-video-batch.ps1"
$SchedulerDir = Join-Path $ProjectRoot "runtime\scheduler"
$StatePath = Join-Path $SchedulerDir "manual-batch-state.json"
$BatchLogPath = Join-Path $SchedulerDir "manual-batch.log"
$TaskLogPath = Join-Path $SchedulerDir "longrun-task.log"
$PowerShellExe = (Get-Command powershell.exe -ErrorAction Stop).Source

function Read-BatchState {
    if (-not (Test-Path $StatePath)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Find-RunningBatchProcess {
    $State = Read-BatchState
    if ($null -eq $State -or [string]$State.status -ne "running") {
        return $null
    }
    $ProcessId = [int]$State.pid
    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $Process) {
        return $null
    }
    $Details = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $Details -or [string]$Details.CommandLine -notlike "*start-three-video-batch.ps1*") {
        return $null
    }
    return $Process
}

function Show-LatestLine {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Kind
    )
    if (-not (Test-Path $Path)) {
        return
    }
    $Line = Get-Content -LiteralPath $Path -Tail 1 -Encoding UTF8 -ErrorAction SilentlyContinue
    if ($null -eq $Line) {
        return
    }
    $Text = [string]$Line
    if ($Script:LastLines[$Kind] -ne $Text) {
        $Script:LastLines[$Kind] = $Text
        Write-Host $Text
    }
}

if (-not (Test-Path $WorkerScript)) {
    throw "Manual batch worker was not found at $WorkerScript"
}

if ($DryRun) {
    & $PowerShellExe -NoProfile -ExecutionPolicy Bypass -File $WorkerScript `
        -Count $Count `
        -IntervalMinutes $IntervalMinutes `
        -MaxAttemptsPerPublication $MaxAttemptsPerPublication `
        -RetryDelaySeconds $RetryDelaySeconds `
        -DryRun
    exit $LASTEXITCODE
}

New-Item -ItemType Directory -Force -Path $SchedulerDir | Out-Null
$WorkerProcess = Find-RunningBatchProcess

if ($null -ne $WorkerProcess) {
    Write-Host ("VV Knopka batch is already running as PID {0}; attached monitor only." -f $WorkerProcess.Id)
}
else {
    $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $WorkerStdout = Join-Path $SchedulerDir "manual-batch-worker-$Stamp.stdout.log"
    $WorkerStderr = Join-Path $SchedulerDir "manual-batch-worker-$Stamp.stderr.log"
    $WorkerArguments = (
        '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" ' +
        '-Count {1} -IntervalMinutes {2} -MaxAttemptsPerPublication {3} ' +
        '-RetryDelaySeconds {4} -NoConsoleOutput'
    ) -f $WorkerScript, $Count, $IntervalMinutes, $MaxAttemptsPerPublication, $RetryDelaySeconds

    $WorkerProcess = Start-Process `
        -FilePath $PowerShellExe `
        -ArgumentList $WorkerArguments `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $WorkerStdout `
        -RedirectStandardError $WorkerStderr `
        -PassThru

    Write-Host ("VV Knopka background batch started as PID {0}." -f $WorkerProcess.Id)
}

Write-Host "This window is only a log monitor. Selecting text or closing it cannot pause the batch."
Write-Host ("State: {0}" -f $StatePath)
Write-Host ""

$Script:LastLines = @{}
while ($true) {
    try {
        $WorkerProcess.Refresh()
        if ($WorkerProcess.HasExited) {
            break
        }
    }
    catch {
        break
    }

    Show-LatestLine -Path $BatchLogPath -Kind "batch"
    Show-LatestLine -Path $TaskLogPath -Kind "task"
    Start-Sleep -Seconds 3
}

Show-LatestLine -Path $BatchLogPath -Kind "batch"
Show-LatestLine -Path $TaskLogPath -Kind "task"
$FinalState = Read-BatchState
Write-Host ""
if ($null -ne $FinalState) {
    Write-Host ("Batch finished: status={0}, completed={1}/{2}." -f $FinalState.status, $FinalState.completed, $FinalState.requested)
    if ($FinalState.error) {
        Write-Host ("Error: {0}" -f $FinalState.error)
    }
}
else {
    Write-Host "Background worker exited before a readable state file was written. Check worker stderr in runtime\scheduler."
}
Write-Host "You may close this monitor window."
