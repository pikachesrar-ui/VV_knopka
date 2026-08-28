from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from .animal_compilation import render_compilation
from .budget import BudgetLedger
from .gates import publication_gate
from .manifest import build_manifest, write_manifest
from .mpt import MoneyPrinterTurboClient
from .openai_auth import check_openai_auth, describe_openai_key
from .openai_client import OpenAIPlanner
from .settings import load_settings


def _slot(settings, number: int):
    slots = {slot.slot: slot for slot in build_manifest(settings)}
    if number not in slots:
        raise SystemExit(f"slot must be 1..{len(slots)}")
    return slots[number]


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv")
    parser.add_argument("--config", default="config/pilot.toml")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-pilot")
    sub.add_parser("status")
    sub.add_parser("doctor")
    plan = sub.add_parser("plan")
    plan.add_argument("slot", type=int)
    ai = sub.add_parser("render-ai")
    ai.add_argument("slot", type=int)
    animal = sub.add_parser("render-animal")
    animal.add_argument("slot", type=int)
    args = parser.parse_args()

    settings = load_settings(args.config)
    ledger = BudgetLedger(settings)

    if args.command == "init-pilot":
        path = write_manifest(settings)
        gate = publication_gate(settings)
        print(f"manifest: {path}")
        print(f"publication gate: {'PASS' if gate.passed else 'FAIL'}")
        if gate.reasons:
            print("; ".join(gate.reasons))
        return

    if args.command == "status":
        print(f"OpenAI spent: ${ledger.spent_usd():.4f} / ${settings.budget_usd:.2f}")
        print(f"auto_publish: {settings.auto_publish}")
        print(f"publication gate: {'PASS' if publication_gate(settings).passed else 'FAIL'}")
        return

    if args.command == "doctor":
        print(f"OPENAI_API_KEY: {describe_openai_key()}")
        result = check_openai_auth()
        print(result.message)
        if not result.ok:
            raise SystemExit(1)
        return

    slot = _slot(settings, args.slot)
    slot_dir = settings.runtime_dir / "slots" / f"{slot.slot:02d}"
    slot_dir.mkdir(parents=True, exist_ok=True)

    if args.command == "plan":
        planner = OpenAIPlanner(settings, ledger)
        content = planner.create_plan(slot=slot.slot, pipeline=slot.pipeline, language=slot.language)
        path = slot_dir / "plan.json"
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        print(path)
        return

    if args.command == "render-ai":
        if slot.pipeline != "ai_short":
            raise SystemExit("render-ai can only be used on ai_short slots")
        plan_path = slot_dir / "plan.json"
        if not plan_path.exists():
            raise SystemExit(f"missing {plan_path}; run `vv plan {slot.slot}` first")
        content = json.loads(plan_path.read_text(encoding="utf-8"))
        mpt = MoneyPrinterTurboClient(settings)
        task_id = mpt.create_ai_video(content, slot.language)
        print(f"MPT task: {task_id}")
        task = mpt.wait(task_id)
        (slot_dir / "mpt-task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
        output = settings.runtime_dir / "ready_for_review" / f"slot-{slot.slot:02d}-{slot.language}-ai.mp4"
        print(mpt.download_video(task, output))
        return

    if args.command == "render-animal":
        if slot.pipeline != "animal_compilation":
            raise SystemExit("render-animal can only be used on animal_compilation slots")
        source_manifest = slot_dir / "sources.json"
        output = settings.runtime_dir / "ready_for_review" / f"slot-{slot.slot:02d}-{slot.language}-animals.mp4"
        print(render_compilation(settings, source_manifest, output))
        return


if __name__ == "__main__":
    main()
