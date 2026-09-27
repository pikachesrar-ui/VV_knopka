from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json

from .settings import Settings


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class UsageRecord:
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    token_cost_usd: float
    fixed_cost_usd: float
    cost_usd: float
    purpose: str


class BudgetLedger:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.runtime_dir / "openai_usage.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def spent_usd(self) -> float:
        if not self.path.exists():
            return 0.0
        total = 0.0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                total += float(json.loads(line)["cost_usd"])
        return total

    def ensure_room(self, estimated_usd: float) -> None:
        projected = self.spent_usd() + estimated_usd
        if projected > self.settings.budget_usd:
            raise BudgetExceeded(
                f"OpenAI pilot budget guard: projected ${projected:.4f} exceeds "
                f"${self.settings.budget_usd:.2f}"
            )

    def price(self, model: str, input_tokens: int, output_tokens: int) -> float:
        cfg = self.settings.raw["openai"]
        if "terra" in model:
            input_rate = float(cfg["terra_input_per_million_usd"])
            output_rate = float(cfg["terra_output_per_million_usd"])
        elif "luna" in model:
            input_rate = float(cfg["luna_input_per_million_usd"])
            output_rate = float(cfg["luna_output_per_million_usd"])
        else:
            raise ValueError(f"No local price table for model: {model}")
        return input_tokens / 1_000_000 * input_rate + output_tokens / 1_000_000 * output_rate

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        purpose: str,
        *,
        fixed_cost_usd: float = 0.0,
    ) -> UsageRecord:
        token_cost = self.price(model, input_tokens, output_tokens)
        fixed_cost = max(float(fixed_cost_usd), 0.0)
        cost = token_cost + fixed_cost
        if self.spent_usd() + cost > self.settings.budget_usd:
            raise BudgetExceeded("Provider usage would cross the configured pilot budget")
        record = UsageRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            token_cost_usd=token_cost,
            fixed_cost_usd=fixed_cost,
            cost_usd=cost,
            purpose=purpose,
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        return record
