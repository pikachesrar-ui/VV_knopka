from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from .animal_audio_sources_v2 import ensure_audio_animal_sources
from .animal_episode import build_episode_metadata
from .animal_highlights import select_highlights
from .animal_v3 import render_cat_v3
from .budget import BudgetLedger
from .cat_compilation import build_generic_cat_plan
from .gates import publication_gate
from .manifest import build_manifest, write_manifest
from .material_fallback import CuratedMaterialFallbackError, load_duration_sufficient_materials
from .mpt import MoneyPrinterTurboClient
from .mpt_health import require_mpt_available
from .openai_client import OpenAIPlanner
from .pexels_curator import prepare_pexels_materials
from .pilot_conveyor import run_batch
from .publication_metadata import write_upload_metadata
from .settings import load_settings
from .source_history import audit_cat_source_reuse


def _slot(settings, number: int):
    slots = {slot.slot: slot for slot in build_manifest(settings)}
    if number not in slots:
        raise SystemExit(f"slot must be 1..{len(slots)}")
    return slots[number]


def _multi_source_audit_exhausted(slot_dir, *, expected_anchor: str | None = None) -> bool:
    audit_path = slot_dir / "ai_materials.json"
    if not audit_path.exists():
        return False
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    normalized_expected = str(expected_anchor or "").strip()
    audit_anchor = str(audit.get("visual_anchor") or "").strip()
    if normalized_expected and audit_anchor.casefold() != normalized_expected.casefold():
        return False

    providers = audit.get("providers") or {}
    pexels_reviewed = int((providers.get("pexels") or {}).get("vision_reviewed") or 0)
    pixabay_reviewed = int((providers.get("pixabay") or {}).get("vision_reviewed") or 0)
    return pexels_reviewed > 0 and pixabay_reviewed > 0


def _prepare_ai_materials(settings, content, *, slot, slot_dir, ledger):
    expected_anchor = str(content.get("visual_anchor") or "").strip()
    try:
        materials, stats = load_duration_sufficient_materials(
            settings,
            slot_dir=slot_dir,
            expected_anchor=expected_anchor,
        )
        print(
            "Reusing approved stock: "
            f"{stats['unique_sources']} unique sources, "
            f"{stats['reusable_seconds']:.1f}s reusable footage"
        )
        return materials
    except CuratedMaterialFallbackError as cached_error:
        if _multi_source_audit_exhausted(slot_dir, expected_anchor=expected_anchor):
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
        try:
            materials, stats = load_duration_sufficient_materials(
                settings,
                slot_dir=slot_dir,
                expected_anchor=expected_anchor,
            )
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
    ai = sub.add_parser("render-ai")
    ai.add_argument("slot", type=int)
    animal = sub.add_parser("render-animal")
    animal.add_argument("slot", type=int)
    next_cmd = sub.add_parser("pilot-next", help="Render the next missing pilot slot into ready_for_review")
    next_cmd.add_argument("--dry-run", action="store_true")
    batch = sub.add_parser("pilot-batch", help="Render several missing pilot slots, stopping on first failure")
    batch.add_argument("--count", type=int, default=3)
    batch.add_argument("--dry-run", action="store_true")
    plan.add_argument("--topic", default=None, help="Explicit topic/animal requested by the user")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    settings = load_settings(config_path)
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

    if args.command in {"pilot-next", "pilot-batch"}:
        count = 1 if args.command == "pilot-next" else max(int(args.count), 0)
        try:
            outputs = run_batch(settings, config_path=config_path, count=count, dry_run=bool(args.dry_run))
        except RuntimeError as exc:
            raise SystemExit(f"Pilot conveyor stopped: {exc}") from exc
        if outputs:
            print("Pilot conveyor outputs:")
            for output in outputs:
                print(output)
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

        try:
            require_mpt_available(settings)
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc

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
        rendered = Path(mpt.download_video(task, output))
        print(rendered)
        print(f"Upload metadata: {write_upload_metadata(settings, slot=slot, output=rendered, slot_dir=slot_dir)}")
        return

    if args.command == "render-animal":
        if slot.pipeline != "animal_compilation":
            raise SystemExit("render-animal can only be used on animal_compilation slots")

        content = build_generic_cat_plan(slot.language)
        effective_plan = slot_dir / "effective-plan.json"
        effective_plan.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"Cat compilation mode: generic | title={content.get('title')} | "
            f"effective plan: {effective_plan}"
        )

        source_manifest = slot_dir / "sources.json"
        source_manifest = ensure_audio_animal_sources(
            settings,
            content,
            slot=slot.slot,
            slot_dir=slot_dir,
            source_manifest=source_manifest,
            ledger=ledger,
        )
        source_data = json.loads(source_manifest.read_text(encoding="utf-8"))
        print(f"Audible vertical licensed cat sources: {len(source_data.get('clips', []))}")
        print(f"Audio/source audit: {slot_dir / 'animal_audio_sources.json'}")
        try:
            reuse_audit = audit_cat_source_reuse(settings, slot=slot.slot, source_manifest=source_manifest)
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"Cross-episode source reuse audit: {reuse_audit}")

        animal_cfg = settings.raw.get("animal", {})
        highlight_manifest = select_highlights(
            settings,
            ledger,
            source_manifest=source_manifest,
            slot_dir=slot_dir,
            language=slot.language,
            editorial_plan=content,
            clip_seconds=float(animal_cfg.get("clip_seconds", 5)),
        )
        print(f"Highlight edit: {highlight_manifest}")

        episode_manifest = build_episode_metadata(
            settings,
            slot=slot.slot,
            language=slot.language,
            plan=content,
            highlight_manifest=highlight_manifest,
            output=slot_dir / "episode.json",
        )
        episode_data = json.loads(episode_manifest.read_text(encoding="utf-8"))
        print(f"Cat episode: {episode_data['display_title']}")
        print(f"End card: {episode_data['end_text']}")

        output = settings.runtime_dir / "ready_for_review" / f"slot-{slot.slot:02d}-{slot.language}-animals.mp4"
        rendered = Path(
            render_cat_v3(
                settings,
                source_manifest,
                highlight_manifest,
                episode_manifest,
                output,
                language=slot.language,
            )
        )
        print(rendered)
        print(f"Upload metadata: {write_upload_metadata(settings, slot=slot, output=rendered, slot_dir=slot_dir)}")
        return


if __name__ == "__main__":
    main()
