param(
    [string]$ShortcutName = "VV Knopka - 3 Shorts",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BatchScript = Join-Path $PSScriptRoot "launch-three-video-batch.ps1"
$PowerShellExe = (Get-Command powershell.exe -ErrorAction Stop).Source
$VvExe = Join-Path $ProjectRoot ".venv\Scripts\vv.exe"
$Desktop = [Environment]::GetFolderPath("Desktop")
$StartMenu = Join-Path ([Environment]::GetFolderPath("Programs")) "VV Knopka"
$DesktopShortcut = Join-Path $Desktop "$ShortcutName.lnk"
$StartMenuShortcut = Join-Path $StartMenu "$ShortcutName.lnk"

if (-not (Test-Path $BatchScript)) {
    throw "Manual batch launcher was not found at $BatchScript"
}

Write-Host "Shortcut : $ShortcutName"
Write-Host "Desktop  : $DesktopShortcut"
Write-Host "Start    : $StartMenuShortcut"
Write-Host "Action   : generate/publish 3 videos, approximately 60 minutes apart"

if ($DryRun) {
    Write-Host "DRY RUN: shortcuts were not created."
    exit 0
}

New-Item -ItemType Directory -Force -Path $StartMenu | Out-Null
$Shell = New-Object -ComObject WScript.Shell
$Arguments = '-NoExit -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $BatchScript

foreach ($Path in @($DesktopShortcut, $StartMenuShortcut)) {
    $Shortcut = $Shell.CreateShortcut($Path)
    $Shortcut.TargetPath = $PowerShellExe
    $Shortcut.Arguments = $Arguments
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.Description = "Run three VV Knopka Shorts in a detached worker and monitor progress."
    if (Test-Path $VvExe) {
        $Shortcut.IconLocation = "$VvExe,0"
    }
    else {
        $Shortcut.IconLocation = "$PowerShellExe,0"
    }
    $Shortcut.Save()
}

Write-Host "Created both shortcuts."
Write-Host "To keep the button on the taskbar: right-click the Start-menu shortcut and choose 'Pin to taskbar'."
Write-Host "Windows does not provide a reliable supported command for pinning arbitrary shortcuts automatically."

