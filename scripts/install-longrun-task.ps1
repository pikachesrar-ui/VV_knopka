param(
    [string]$At = "01:30,03:30,05:30",

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

$TimeStrings = @(
    $At -split '[,;]' |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ }
)
if ($TimeStrings.Count -eq 0) {
    throw "At must contain at least one HH:mm time."
}

$TimePattern = '^(?:[01]\d|2[0-3]):[0-5]\d$'
foreach ($TimeString in $TimeStrings) {
    if ($TimeString -notmatch $TimePattern) {
        throw "Invalid scheduled time '$TimeString'. Use HH:mm, or a comma-separated list such as 01:30,03:30,05:30."
    }
}
$TimeStrings = @($TimeStrings | Select-Object -Unique)

$ParsedTimes = @(
    foreach ($TimeString in $TimeStrings) {
        [DateTime]::ParseExact(
            $TimeString,
            "HH:mm",
            [System.Globalization.CultureInfo]::InvariantCulture
        )
    }
)

$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $Runner

Write-Host "Task name : $TaskName"
Write-Host "User      : $CurrentUser"
Write-Host "Schedule  : daily at $($TimeStrings -join ', ')"
Write-Host "Triggers  : $($TimeStrings.Count) per day"
Write-Host "Runner    : $Runner"
Write-Host "Project   : $ProjectRoot"
Write-Host "Behavior  : one review-only longrun-next per trigger; no git pull; no publishing"

if ($DryRun) {
    Write-Host "DRY RUN: scheduled task was not registered."
    exit 0
}

Import-Module ScheduledTasks -ErrorAction Stop

$ActionParams = @{
    Execute = $PowerShellExe
    Argument = $Arguments
    WorkingDirectory = $ProjectRoot
}
$Action = New-ScheduledTaskAction @ActionParams
$Triggers = @(
    foreach ($ParsedTime in $ParsedTimes) {
        New-ScheduledTaskTrigger -Daily -At $ParsedTime
    }
)

$SettingsParams = @{
    StartWhenAvailable = $true
    MultipleInstances = "IgnoreNew"
    ExecutionTimeLimit = (New-TimeSpan -Hours 4)
    AllowStartIfOnBatteries = $true
    DontStopIfGoingOnBatteries = $true
}
$Settings = New-ScheduledTaskSettingsSet @SettingsParams

# Interactive logon avoids storing or requesting a Windows password. The task
# runs while this user is logged on (the desktop may be locked).
$PrincipalParams = @{
    UserId = $CurrentUser
    LogonType = "Interactive"
    RunLevel = "Limited"
}
$Principal = New-ScheduledTaskPrincipal @PrincipalParams

$TaskParams = @{
    Action = $Action
    Trigger = $Triggers
    Settings = $Settings
    Principal = $Principal
    Description = "Generate one VV_knopka long-run video per configured trigger into ready_for_review. Publishing remains disabled."
}
$Task = New-ScheduledTask @TaskParams

Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null

$Registered = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$Info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop

Write-Host "Registered: $($Registered.TaskName)"
Write-Host "State     : $($Registered.State)"
Write-Host "Triggers  : $($Registered.Triggers.Count)"
Write-Host "Next run  : $($Info.NextRunTime)"
Write-Host "Log       : $(Join-Path $ProjectRoot 'runtime\scheduler\longrun-task.log')"
