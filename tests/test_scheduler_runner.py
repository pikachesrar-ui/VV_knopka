from pathlib import Path


def test_windows_scheduler_runner_forces_utf8_and_preserves_best_effort_stats() -> None:
    script = Path("scripts/run-longrun-task.ps1").read_text(encoding="utf-8")

    assert '$env:PYTHONIOENCODING = "utf-8"' in script
    assert '$env:PYTHONUTF8 = "1"' in script
    assert '[Console]::OutputEncoding = $Utf8NoBom' in script
    assert '$ErrorActionPreference = "Continue"' in script
    assert 'WARN: YouTube statistics collection failed' in script
    assert 'continuing publication workflow' in script
    assert '[switch]$NoConsoleOutput' in script
    assert 'if (-not $NoConsoleOutput)' in script


def test_scheduler_runner_respects_manual_batch_and_delayed_publication() -> None:
    script = Path("scripts/run-longrun-task.ps1").read_text(encoding="utf-8")

    assert '[switch]$ManualBatch' in script
    assert '[string]$PublishNotBefore' in script
    assert 'manual-batch-state.json' in script
    assert 'Get-ManualBatchSuppression' in script
    assert 'Wait-ForPublicationWindow' in script
    assert 'if ($ManualBatch) { exit 75 }' in script
    assert script.count('Wait-ForPublicationWindow') >= 3


def test_manual_batch_retries_each_publication_but_keeps_gates_fail_closed() -> None:
    script = Path("scripts/start-three-video-batch.ps1").read_text(encoding="utf-8")

    assert '[int]$Count = 3' in script
    assert '[int]$IntervalMinutes = 60' in script
    assert '[int]$MaxAttemptsPerPublication = 5' in script
    assert '[int]$RetryDelaySeconds = 30' in script
    assert '[int]$AttemptTimeoutMinutes = 90' in script
    assert 'manual-batch.lock' in script
    assert 'manual-batch-state.json' in script
    assert '"-ManualBatch"' in script
    assert '[switch]$NoConsoleOutput' in script
    assert '$Arguments += "-NoConsoleOutput"' in script
    assert '"-PublishNotBefore"' in script
    assert 'for ($Attempt = 1; $Attempt -le $MaxAttemptsPerPublication; $Attempt++)' in script
    assert 'if ($LastExitCode -eq 0)' in script
    assert 'retrying the same missing publication' in script
    assert '$Child.WaitForExit($AttemptTimeoutMinutes * 60 * 1000)' in script
    assert 'Stop-ProcessTreeBestEffort -ProcessId $Child.Id' in script
    assert '-FilePath "taskkill.exe"' in script
    assert 'timeout remains retryable' in script
    assert '[Math]::Pow(2, $Attempt - 1)' in script
    assert 'did not publish after {1} attempts' in script
    assert 'Normal night schedule remains available' in script


def test_scheduler_enforces_critical_qa_and_runs_weekly_metadata_research() -> None:
    script = Path("scripts/run-longrun-task.ps1").read_text(encoding="utf-8")

    assert script.count('"--enforce"') >= 2
    assert 'critical video QA failed' in script
    assert 'vv-research.exe' in script
    assert '"collect", "--if-due-hours", "168"' in script


def test_detached_launcher_separates_worker_from_monitor_console() -> None:
    script = Path("scripts/launch-three-video-batch.ps1").read_text(encoding="utf-8")

    assert 'Start-Process' in script
    assert '-WindowStyle Hidden' in script
    assert '-RedirectStandardOutput' in script
    assert '-RedirectStandardError' in script
    assert '-NoConsoleOutput' in script
    assert 'Selecting text or closing it cannot pause the batch' in script
    assert 'Find-RunningBatchProcess' in script
    assert 'Get-CimInstance Win32_Process' in script
    assert 'start-three-video-batch.ps1' in script
    assert '[int]$MaxAttemptsPerPublication = 5' in script


def test_shortcut_installer_targets_manual_batch_script() -> None:
    script = Path("scripts/install-manual-batch-shortcut.ps1").read_text(encoding="utf-8")

    assert 'launch-three-video-batch.ps1' in script
    assert 'WScript.Shell' in script
    assert '-NoExit -NoProfile' in script
    assert 'GetFolderPath("Desktop")' in script
    assert 'GetFolderPath("Programs")' in script
    assert 'Pin to taskbar' in script
