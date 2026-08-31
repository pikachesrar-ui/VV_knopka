from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from dotenv import load_dotenv

from .acestep_client import ACEStepClient, ACEStepProcessManager, api_available
from .music_library import available_tracks, music_library_dir
from .settings import load_settings


_PRESETS = (
    (
        "cute",
        96,
        "soft playful instrumental background music, warm lo-fi texture, gentle marimba, soft piano, light brushed percussion, cute curious mood, simple memorable melody, no vocals, no singing, no dramatic drops, no heavy bass, suitable under funny cat video audio",
    ),
    (
        "cute",
        100,
        "cozy cheerful instrumental, soft plucked strings, tiny bells, warm electric piano, relaxed playful rhythm, friendly whimsical cat-video mood, unobtrusive background arrangement, no vocals, no heavy bass, no dramatic transitions",
    ),
    (
        "playful",
        106,
        "light playful instrumental groove, muted percussion, pizzicato strings, soft keys, curious mischievous energy, clean loop-friendly background, no vocals, no aggressive bass, no cinematic impacts",
    ),
    (
        "playful",
        102,
        "bouncy but gentle instrumental background, marimba and soft synth plucks, warm percussion, small comedic accents, relaxed internet-video feel, no vocals, no bass drop, never overpower dialogue or original clip audio",
    ),
    (
        "curious",
        92,
        "calm curious instrumental underscore for short animal facts, soft piano, subtle mallets, airy pads, delicate pulse, sense of discovery, restrained and pleasant, no vocals, no dramatic climax, no heavy bass",
    ),
    (
        "curious",
        98,
        "gentle science-curiosity instrumental, warm keys, soft organic percussion, light plucked melody, quietly intriguing and optimistic, background-first mix, no vocals, no cinematic boom, no heavy bass",
    ),
    (
        "calm",
        88,
        "peaceful instrumental background, warm lo-fi piano, soft ambient pads, very light percussion, comforting simple melody, relaxed neutral mood, no vocals, no dramatic changes, no heavy bass",
    ),
    (
        "calm",
        90,
        "soft pleasant instrumental bed, mellow electric piano, subtle acoustic plucks, airy ambience, gentle steady rhythm, unobtrusive and loop-friendly, no vocals, no intense build, no bass drops",
    ),
)


def _candidate_dir(settings) -> Path:
    path = music_library_dir(settings) / "candidates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _approved_names(settings) -> set[str]:
    return {path.name.casefold() for path in available_tracks(settings)}


def _candidate_files(settings) -> list[Path]:
    root = _candidate_dir(settings)
    result = [path for path in root.iterdir() if path.is_file() and path.stat().st_size > 0]
    return sorted(result, key=lambda path: path.name.casefold())


def _next_name(category: str, index: int) -> str:
    same_before = sum(1 for preset in _PRESETS[: index + 1] if preset[0] == category)
    return f"{category}_{same_before:02d}.wav"


def _write_manifest(settings, records: list[dict]) -> Path:
    path = _candidate_dir(settings) / "generation.json"
    previous: list[dict] = []
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                previous = [dict(item) for item in raw if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            pass
    by_name = {str(item.get("name") or ""): item for item in previous if item.get("name")}
    for item in records:
        by_name[str(item["name"])] = item
    payload = [by_name[key] for key in sorted(by_name, key=str.casefold)]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vv-music")
    parser.add_argument("--config", default="config/pilot.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("list")

    generate = sub.add_parser("generate-library")
    generate.add_argument("--count", type=int, default=8)
    generate.add_argument("--duration", type=float, default=45.0)
    generate.add_argument("--force", action="store_true")

    approve = sub.add_parser("approve")
    approve.add_argument("names", nargs="+")

    args = parser.parse_args()
    settings = load_settings(Path(args.config).resolve())

    if args.command == "status":
        cfg = settings.raw.get("music", {})
        print(f"music enabled: {bool(cfg.get('enabled', False))}")
        print(f"library: {music_library_dir(settings)}")
        print(f"approved tracks: {len(available_tracks(settings))}")
        print(f"candidate tracks: {len(_candidate_files(settings))}")
        print(f"ACE-Step API: {'online' if api_available(settings) else 'offline'}")
        return

    if args.command == "list":
        approved = available_tracks(settings)
        candidates = _candidate_files(settings)
        print("Approved:")
        for path in approved:
            print(f"  {path.name}")
        print("Candidates:")
        for path in candidates:
            print(f"  {path.name}")
        return

    if args.command == "approve":
        candidates = {path.name.casefold(): path for path in _candidate_files(settings)}
        destination = music_library_dir(settings)
        destination.mkdir(parents=True, exist_ok=True)
        moved = 0
        for raw in args.names:
            key = Path(raw).name.casefold()
            source = candidates.get(key)
            if source is None:
                raise SystemExit(f"Candidate not found: {raw}")
            target = destination / source.name
            if target.exists():
                raise SystemExit(f"Approved track already exists: {target.name}")
            shutil.move(str(source), str(target))
            print(f"APPROVED {source.name}")
            moved += 1
        print(f"Approved {moved} track(s). music.enabled is unchanged.")
        return

    count = max(0, min(int(args.count), len(_PRESETS)))
    if count == 0:
        print("No candidates requested.")
        return

    candidate_dir = _candidate_dir(settings)
    records: list[dict] = []
    manager = ACEStepProcessManager(settings)
    try:
        manager.ensure_running()
        client = ACEStepClient(settings)
        for index, (category, bpm, prompt) in enumerate(_PRESETS[:count]):
            name = _next_name(category, index)
            output = candidate_dir / name
            if output.exists() and output.stat().st_size > 0 and not args.force:
                print(f"SKIP {name}: candidate already exists")
                continue
            print(f"GENERATING {name} | {bpm} BPM")
            track = client.generate_instrumental(
                prompt=prompt,
                output=output,
                duration_seconds=max(10.0, min(float(args.duration), 600.0)),
                bpm=bpm,
            )
            records.append(
                {
                    "name": output.name,
                    "category": category,
                    "bpm": bpm,
                    "duration_seconds": float(args.duration),
                    "prompt": prompt,
                    "task_id": track.task_id,
                    "seed_value": track.seed_value,
                    "lm_model": track.lm_model,
                    "dit_model": track.dit_model,
                    "approved": False,
                }
            )
            print(f"CANDIDATE {output}")
    finally:
        manager.close()

    manifest = _write_manifest(settings, records)
    print(f"Candidate manifest: {manifest}")
    print("Listen to the candidate WAV files before approving any of them for production rotation.")


if __name__ == "__main__":
    main()
