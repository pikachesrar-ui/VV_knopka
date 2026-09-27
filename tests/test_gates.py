from pathlib import Path

from vv_knopka.gates import check_script_similarity, publication_gate
from vv_knopka.settings import load_settings


def settings():
    return load_settings(Path(__file__).parents[1] / "config" / "pilot.toml")


def test_pilot_publication_gate_is_locked():
    assert publication_gate(settings()).passed


def test_near_duplicate_script_is_blocked():
    result = check_script_similarity("cats sleep a lot", ["cats sleep a lot"], 0.92)
    assert not result.passed
