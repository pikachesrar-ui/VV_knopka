param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^(?:[01]\d|2[0-3]):[0-5]\d$')]
    [string]$At,

    [string]$TaskName = "VV Knopka Long Run",

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Runner = Join-Path $PSScriptRoot "run-longrun-task.ps1"
$PowerShellExe = (Get-Command powershell.exe -ErrorAction Stop).Source

if (-not (Test-Path $Runner)) {
    throw "Scheduler runner was not found at $Runner"
}

$ParsedTime = [DateTime]::ParseExact(
    $At,
    "HH:mm",
    [System.Globalization.CultureInfo]::InvariantCulture
)

$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $Runner

Write-Host "Task name : $TaskName"
Write-Host "User      : $CurrentUser"
Write-Host "Schedule  : daily at $At"
Write-Host "Runner    : $Runner"
Write-Host "Project   : $ProjectRoot"
Write-Host "Behavior  : one review-only longrun-next per launch; no git pull; no publishing"

if ($DryRun) {
    Write-Host "DRY RUN: scheduled task was not registered."
    exit 0
}

Import-Module ScheduledTasks -ErrorAction Stop

$Action = New-ScheduledTaskAction \
    -Execute $PowerShellExe \
    -Argument $Arguments \
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At $ParsedTime

$Settings = New-ScheduledTaskSettingsSet \
    -StartWhenAvailable \
    -MultipleInstances IgnoreNew \
    -ExecutionTimeLimit (New-TimeSpan -Hours 4) \
    -AllowStartIfOnBatteries \
    -DontStopIfGoingOnBatteries

# Interactive logon avoids storing or requesting a Windows password. The task
# runs while this user is logged on (the desktop may be locked).
$Principal = New-ScheduledTaskPrincipal \
    -UserId $CurrentUser \
    -LogonType Interactive \
    -RunLevel Limited

$Task = New-ScheduledTask \
    -Action $Action \
    -Trigger $Trigger \
    -Settings $Settings \
    -Principal $Principal \
    -Description "Generate one VV_knopka long-run video into ready_for_review. Publishing remains disabled."

Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null

$Registered = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$Info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop

Write-Host "Registered: $($Registered.TaskName)"
Write-Host "State     : $($Registered.State)"
Write-Host "Next run  : $($Info.NextRunTime)"
Write-Host "Log       : $(Join-Path $ProjectRoot 'runtime\scheduler\longrun-task.log')"
