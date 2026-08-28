from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from .animal_compilation import render_compilation, write_stock_sources_manifest
from .budget import BudgetLedger
from .gates import publication_gate
from .manifest import build_manifest, write_manifest
from .material_fallback import CuratedMaterialFallbackError, load_duration_sufficient_materials
from .mpt import MoneyPrinterTurboClient
from .openai_client import OpenAIPlanner
from .pexels_curator import prepare_pexels_materials
from .settings import load_settings


def _slot(settings, number: int):
    slots = {slot.slot: slot for slot in build_manifest(settings)}
    if number not in slots:
        raise SystemExit(f"slot must be 1..{len(slots)}")
    return slots[number]


def _multi_source_audit_exhausted(slot_dir) -> bool:
    audit_path = slot_dir / "ai_materials.json"
    if not audit_path.exists():
        return False
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    providers = audit.get("providers") or {}
    pexels_reviewed = int((providers.get("pexels") or {}).get("vision_reviewed") or 0)
    pixabay_reviewed = int((providers.get("pixabay") or {}).get("vision_reviewed") or 0)
    return pexels_reviewed > 0 and pixabay_reviewed > 0


def _prepare_ai_materials(settings, content, *, slot, slot_dir, ledger):
    # Prefer the already-reviewed local cache. Narrow subjects often have only a
    # few good stock sources; MPT can safely use later non-overlapping segments
    # from those long approved sources in random concat mode.
    try:
        materials, stats = load_duration_sufficient_materials(settings, slot_dir=slot_dir)
        print(
            "Reusing approved stock: "
            f"{stats['unique_sources']} unique sources, "
            f"{stats['reusable_seconds']:.1f}s reusable footage"
        )
        return materials
    except CuratedMaterialFallbackError as cached_error:
        # If both providers have already been visually exhausted, another call
        # would only spend money reviewing the same pool again. Fail without a
        # new API charge and surface the duration/source diagnostic instead.
        if _multi_source_audit_exhausted(slot_dir):
            raise SystemExit(
                f"Cached multi-source audit is exhausted: {cached_error} "
                "No additional vision calls were made."
            ) from cached_error

    try:
        return prepare_pexels_materials(
            settings,
            content,
            slot=slot,
            slot_dir=slot_dir,
            ledger=ledger,
        )
    except RuntimeError:
        # The search function writes its audit before failing on the old 8-file
        # preference. The newly downloaded approved clips may still satisfy the
        # more meaningful duration-based fallback, so check once before surfacing
        # the original failure.
        try:
            materials, stats = load_duration_sufficient_materials(settings, slot_dir=slot_dir)
            print(
                "Using duration-sufficient approved stock: "
                f"{stats['unique_sources']} unique sources, "
                f"{stats['reusable_seconds']:.1f}s reusable footage"
            )
            return materials
        except CuratedMaterialFallbackError:
            raise


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv")
    parser.add_argument("--config", default="config/pilot.toml")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-pilot")
    sub.add_parser("status")
    plan = sub.add_parser("plan")
    plan.add_argument("slot", type=int)
    plan.add_argument("--topic", default=None, help="Explicit topic/animal requested by the user")
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

    slot = _slot(settings, args.slot)
    slot_dir = settings.runtime_dir / "slots" / f"{slot.slot:02d}"
    slot_dir.mkdir(parents=True, exist_ok=True)

    if args.command == "plan":
        planner = OpenAIPlanner(settings, ledger)
        content = planner.create_plan(
            slot=slot.slot,
            pipeline=slot.pipeline,
            language=slot.language,
            topic_hint=args.topic,
        )
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

        materials = _prepare_ai_materials(
            settings,
            content,
            slot=slot.slot,
            slot_dir=slot_dir,
            ledger=ledger,
        )
        print(f"Curated stock materials: {len(materials)}")
        print(f"Material audit: {slot_dir / 'ai_materials.json'}")

        mpt = MoneyPrinterTurboClient(settings)
        task_id = mpt.create_ai_video(content, slot.language, materials=materials)
        print(f"MPT task: {task_id}")
        task = mpt.wait(task_id)
        (slot_dir / "mpt-task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
        output = settings.runtime_dir / "ready_for_review" / f"slot-{slot.slot:02d}-{slot.language}-ai.mp4"
        print(mpt.download_video(task, output))
        return

    if args.command == "render-animal":
        if slot.pipeline != "animal_compilation":
            raise SystemExit("render-animal can only be used on animal_compilation slots")
        plan_path = slot_dir / "plan.json"
        if not plan_path.exists():
            raise SystemExit(f"missing {plan_path}; run `vv plan {slot.slot} --topic cats` first")
        content = json.loads(plan_path.read_text(encoding="utf-8"))
        source_manifest = slot_dir / "sources.json"

        if not source_manifest.exists():
            materials = _prepare_ai_materials(
                settings,
                content,
                slot=slot.slot,
                slot_dir=slot_dir,
                ledger=ledger,
            )
            animal_cfg = settings.raw.get("animal", {})
            write_stock_sources_manifest(
                settings,
                materials,
                source_manifest,
                max_clips=int(animal_cfg.get("material_count", 6)),
                min_unique_clips=int(animal_cfg.get("min_unique_materials", 5)),
            )
            print(f"Auto-curated licensed animal sources: {source_manifest}")
            print(f"Material audit: {slot_dir / 'ai_materials.json'}")

        output = settings.runtime_dir / "ready_for_review" / f"slot-{slot.slot:02d}-{slot.language}-animals.mp4"
        print(render_compilation(settings, source_manifest, output))
        return


if __name__ == "__main__":
    main()
