from pathlib import Path

from vv_knopka.budget import BudgetLedger
from vv_knopka.settings import load_settings


def test_known_model_prices(tmp_path):
    settings = load_settings(Path(__file__).parents[1] / "config" / "pilot.toml")
    object.__setattr__(settings, "root", tmp_path)
    ledger = BudgetLedger(settings)
    assert ledger.price("gpt-5.6-luna", 1_000_000, 1_000_000) == 1.4
    assert ledger.price("gpt-5.6-terra", 1_000_000, 1_000_000) == 14.0
