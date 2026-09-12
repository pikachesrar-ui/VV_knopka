from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    raw: dict[str, Any]
    root: Path

    @property
    def budget_usd(self) -> float:
        return float(self.raw["pilot"]["openai_budget_usd"])

    @property
    def runtime_dir(self) -> Path:
        return self.root / self.raw["pilot"].get("runtime_dir", "runtime")

    @property
    def auto_publish(self) -> bool:
        """Frozen pilot flag retained for backwards-compatible pilot safety checks."""
        return bool(self.raw["pilot"].get("auto_publish", False))

    @property
    def youtube_enabled(self) -> bool:
        return bool(self.raw.get("youtube", {}).get("enabled", False))

    @property
    def youtube_auto_publish(self) -> bool:
        return self.youtube_enabled and bool(self.raw.get("youtube", {}).get("auto_publish", False))

    @property
    def mpt_base_url(self) -> str:
        return os.getenv("MPT_BASE_URL", "http://127.0.0.1:8080").rstrip("/")


def load_settings(path: str | Path = "config/pilot.toml") -> Settings:
    config_path = Path(path).resolve()
    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)
    return Settings(raw=raw, root=config_path.parent.parent)
