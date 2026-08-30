from __future__ import annotations

from . import cli as _cli
from .animal_audio_sources_v3 import ensure_audio_animal_sources
from .pilot_conveyor_v2 import run_batch


def main() -> None:
    # Keep the stable CLI implementation while swapping in the current cat-source
    # refresh policy and conveyor child routing. This avoids broad edits to the
    # already-tested command parser during the pilot.
    original_sources = _cli.ensure_audio_animal_sources
    original_batch = _cli.run_batch
    _cli.ensure_audio_animal_sources = ensure_audio_animal_sources
    _cli.run_batch = run_batch
    try:
        _cli.main()
    finally:
        _cli.ensure_audio_animal_sources = original_sources
        _cli.run_batch = original_batch


if __name__ == "__main__":
    main()
