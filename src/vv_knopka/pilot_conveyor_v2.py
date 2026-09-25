from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from . import pilot_conveyor as _base
from .settings import Settings


def _run_cli_v2(config_path: Path, *args: str) -> None:
    command = [sys.executable, "-m", "vv_knopka.cli_v2", "--config", str(config_path), *args]
    completed = subprocess.run(command, cwd=str(config_path.parent.parent), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"child command failed ({completed.returncode}): {' '.join(args)}")


def run_batch(settings: Settings, *, config_path: Path, count: int, dry_run: bool = False):
    """Use the existing conveyor implementation but keep child processes on the current CLI policy."""
    original = _base._run_cli
    _base._run_cli = _run_cli_v2
    try:
        return _base.run_batch(settings, config_path=config_path, count=count, dry_run=dry_run)
    finally:
        _base._run_cli = original
