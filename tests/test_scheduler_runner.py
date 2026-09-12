from pathlib import Path


def test_windows_scheduler_runner_forces_utf8_and_preserves_best_effort_stats() -> None:
    script = Path("scripts/run-longrun-task.ps1").read_text(encoding="utf-8")

    assert '$env:PYTHONIOENCODING = "utf-8"' in script
    assert '$env:PYTHONUTF8 = "1"' in script
    assert '[Console]::OutputEncoding = $Utf8NoBom' in script
    assert '$ErrorActionPreference = "Continue"' in script
    assert 'WARN: YouTube statistics collection failed' in script
    assert 'continuing publication workflow' in script
