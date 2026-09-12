from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from .settings import Settings


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reasons: tuple[str, ...]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_script_similarity(script: str, prior_scripts: list[str], threshold: float) -> GateResult:
    score = max((SequenceMatcher(None, script, p).ratio() for p in prior_scripts), default=0.0)
    if score >= threshold:
        return GateResult(False, (f"script similarity {score:.3f} >= {threshold:.3f}",))
    return GateResult(True, ())


def check_source_manifest(path: Path, settings: Settings) -> GateResult:
    if not path.exists():
        return GateResult(False, ("source manifest missing",))
    data = json.loads(path.read_text(encoding="utf-8"))
    reasons: list[str] = []
    for i, clip in enumerate(data.get("clips", []), 1):
        if not clip.get("source_url") or not clip.get("license"):
            reasons.append(f"clip {i}: provenance incomplete")
        if settings.raw["safety"]["require_commercial_use_flag"] and not clip.get("commercial_use_allowed"):
            reasons.append(f"clip {i}: commercial use not approved")
    if len(data.get("clips", [])) < 3:
        reasons.append("need at least 3 clips")
    return GateResult(not reasons, tuple(reasons))


def publication_gate(settings: Settings) -> GateResult:
    reasons: list[str] = []
    if settings.auto_publish:
        reasons.append("pilot must keep auto_publish=false")
    if not settings.raw["pilot"].get("review_required", True):
        reasons.append("human review must stay enabled")
    if settings.raw["audio"].get("transition_sfx") != "none":
        reasons.append("transition SFX must be none for the pilot")
    return GateResult(not reasons, tuple(reasons))
