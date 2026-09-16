from pathlib import Path


def test_windows_scheduler_runner_forces_utf8_and_preserves_best_effort_stats() -> None:
    script = Path("scripts/run-longrun-task.ps1").read_text(encoding="utf-8")

    assert '$env:PYTHONIOENCODING = "utf-8"' in script
    assert '$env:PYTHONUTF8 = "1"' in script
    assert '[Console]::OutputEncoding = $Utf8NoBom' in script
    assert '$ErrorActionPreference = "Continue"' in script
    assert 'WARN: YouTube statistics collection failed' in script
    assert 'continuing publication workflow' in script


def test_scheduler_runner_respects_manual_batch_and_delayed_publication() -> None:
    script = Path("scripts/run-longrun-task.ps1").read_text(encoding="utf-8")

    assert '[switch]$ManualBatch' in script
    assert '[string]$PublishNotBefore' in script
    assert 'manual-batch-state.json' in script
    assert 'Get-ManualBatchSuppression' in script
    assert 'Wait-ForPublicationWindow' in script
    assert 'if ($ManualBatch) { exit 75 }' in script
    assert script.count('Wait-ForPublicationWindow') >= 3


def test_manual_batch_uses_three_safe_cycles_and_stops_on_failure() -> None:
    script = Path("scripts/start-three-video-batch.ps1").read_text(encoding="utf-8")

    assert '[int]$Count = 3' in script
    assert '[int]$IntervalMinutes = 60' in script
    assert 'manual-batch.lock' in script
    assert 'manual-batch-state.json' in script
    assert '"-ManualBatch"' in script
    assert '"-PublishNotBefore"' in script
    assert 'if ($ExitCode -ne 0)' in script
    assert 'Normal night schedule remains available' in script


def test_shortcut_installer_targets_manual_batch_script() -> None:
    script = Path("scripts/install-manual-batch-shortcut.ps1").read_text(encoding="utf-8")

    assert 'start-three-video-batch.ps1' in script
    assert 'WScript.Shell' in script
    assert '-NoExit -NoProfile' in script
    assert 'GetFolderPath("Desktop")' in script
    assert 'GetFolderPath("Programs")' in script
    assert 'Pin to taskbar' in script
