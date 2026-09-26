from __future__ import annotations

import argparse
from pathlib import Path

from .content_strategy import build_strategy_report
from .settings import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="vv-strategy")
    parser.add_argument("--config", default="config/pilot.toml")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("report")
    args = parser.parse_args()
    settings = load_settings(Path(args.config).resolve())
    result = build_strategy_report(settings)
    print(f"strategy report: {result['checkpoint_videos']} checkpoint videos | {result['output_file']}")
    for category, share in result["allocations"].items():
        stats = result["categories"][category]
        print(f"{category}: target={share * 100:.1f}% | samples={stats['samples']} | score={stats['shrunk_score']:.3f}")


if __name__ == "__main__":
    main()
