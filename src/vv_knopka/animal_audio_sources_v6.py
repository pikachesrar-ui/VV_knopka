from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from . import animal_audio_sources as _base
from . import animal_audio_sources_v4 as _v4
from . import animal_audio_sources_v5 as _v5
from .budget import BudgetLedger
from .settings import Settings
from .source_history import (
    blocked_cat_source_identities,
    cat_source_cooldown_episodes,
    prior_rendered_cat_identities,
)


_DEFAULT_REMOTE_PROBE_SECONDS = 6.0
_DEFAULT_UNKNOWN_CANDIDATE_CAP = 12


def _strict_remote_audio_probe_factory(
    *,
    minimum_mean_db: float,
    probe_seconds: float,
) -> Callable[[dict[str, Any]], bool | None]:
    """Confirm audibility remotely before a candidate can consume a Luna review.

    A technically present audio stream is not enough: several Pexels files expose an
    audio track that is effectively silent. We therefore measure the first few remote
    seconds with FFmpeg. Probe failures remain unknown rather than false, so a small
    bounded fallback pool can still be reviewed when a CDN refuses remote probing.
    """

    def probe(file_info: dict[str, Any]) -> bool | None:
        link = str(file_info.get("link") or "").strip()
        if not link:
            return False

        stream_state = _base.has_audio_stream(link, timeout=12.0)
        if stream_state is False:
            return False
        if stream_state is None:
            # Do not immediately stack a second long network/FFmpeg timeout on a
            # CDN URL that ffprobe could not inspect. A bounded unknown tail may
            # still reach the normal downloaded-file validator later.
            return None

        mean_db = _base.mean_audio_volume_db(link, seconds=max(float(probe_seconds), 1.0))
        if mean_db is not None:
            return mean_db > float(minimum_mean_db)

        # A confirmed stream with an unmeasurable level is deliberately *not*
        # treated as audible. It is only an unknown candidate and is capped later.
        return None

    return probe


def _fresh_only_finish_factory(
    *,
    unknown_candidate_cap: int,
) -> Callable[..., list[dict[str, Any]]]:
    """Return never-used stock only; bounded local history fallback is handled by v5.

    This prevents remote discovery from quietly filling a new episode with cooled
    history before the explicit v5 concentration limits are applied. Candidates whose
    remote audio could not be measured are allowed only in a small bounded tail so a
    CDN probe failure cannot trigger dozens of unnecessary vision calls.
    """

    def finish(
        fresh_confirmed: list[dict[str, Any]],
        fresh_unknown: list[dict[str, Any]],
        cooled_confirmed: list[dict[str, Any]],
        cooled_unknown: list[dict[str, Any]],
        *,
        max_candidates: int,
    ) -> list[dict[str, Any]]:
        del cooled_confirmed, cooled_unknown
        cap = max(int(max_candidates), 1)
        confirmed = list(fresh_confirmed[:cap])
        remaining = max(cap - len(confirmed), 0)
        unknown_limit = min(max(int(unknown_candidate_cap), 0), remaining)
        return (confirmed + list(fresh_unknown[:unknown_limit]))[:cap]

    return finish


def _manifest_has_cooled_reuse(source_manifest: Path) -> bool:
    if not source_manifest.exists():
        return False
    try:
        raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    for item in raw.get("clips") or []:
        if not isinstance(item, dict):
            continue
        if item.get("cooled_down_reuse") is True or item.get("reused_from_slot") not in (None, "", 0):
            return True
    return False


def _retry_safe_seed_factory(original_seed: Callable[..., list[dict[str, Any]]]) -> Callable[..., list[dict[str, Any]]]:
    """Do not stack a second cooled fallback on top of a prior failed attempt."""

    def seed(
        settings: Settings,
        *,
        slot: int,
        source_manifest: Path,
        protected: set[tuple[str, str]],
        max_sources: int,
    ) -> list[dict[str, Any]]:
        if _manifest_has_cooled_reuse(source_manifest):
            return []
        return original_seed(
            settings,
            slot=slot,
            source_manifest=source_manifest,
            protected=protected,
            max_sources=max_sources,
        )

    return seed


def _append_v6_audit(
    settings: Settings,
    *,
    slot: int,
    slot_dir: Path,
    probe_seconds: float,
    unknown_candidate_cap: int,
) -> None:
    audit_path = slot_dir / "animal_audio_sources.json"
    if not audit_path.exists():
        return

    protected = blocked_cat_source_identities(settings, before_slot=slot)
    all_prior = prior_rendered_cat_identities(settings, before_slot=slot)
    try:
        _v4._append_deep_search_audit(
            slot_dir,
            all_prior_count=len(all_prior),
            protected_count=len(protected),
            cooldown_episodes=cat_source_cooldown_episodes(settings),
        )
    except Exception:
        # Diagnostic enrichment must never replace the original sourcing failure.
        pass

    try:
        raw = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    animal_cfg = settings.raw.get("animal", {})
    raw["remote_audibility_gate"] = {
        "enabled": True,
        "order": "audio-before-vision",
        "minimum_mean_volume_db": float(animal_cfg.get("min_source_mean_volume_db", -55.0)),
        "probe_seconds": float(probe_seconds),
        "unknown_candidates_max_per_provider": int(unknown_candidate_cap),
        "remote_cooled_candidates_allowed": False,
        "policy": (
            "measure remote source audibility before Luna review; confirmed-silent files are rejected before vision; "
            "only a small bounded pool of unmeasurable fresh candidates may reach vision; cooled history is handled "
            "only by the explicit bounded local fallback"
        ),
    }
    raw["provider_availability"] = {
        "pexels_api_key_present": bool(os.getenv("PEXELS_API_KEY", "").strip()),
        "pixabay_api_key_present": bool(os.getenv("PIXABAY_API_KEY", "").strip()),
    }
    audit_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_audio_animal_sources(
    settings: Settings,
    plan: dict[str, Any],
    *,
    slot: int,
    slot_dir: Path,
    source_manifest: Path,
    ledger: BudgetLedger,
) -> Path:
    """v5 anti-remake policy plus remote audibility-first discovery."""
    animal_cfg = settings.raw.get("animal", {})
    minimum_mean_db = float(animal_cfg.get("min_source_mean_volume_db", -55.0))
    probe_seconds = float(animal_cfg.get("remote_audio_probe_seconds", _DEFAULT_REMOTE_PROBE_SECONDS))
    unknown_candidate_cap = max(
        int(animal_cfg.get("remote_audio_unknown_max_candidates", _DEFAULT_UNKNOWN_CANDIDATE_CAP)),
        0,
    )

    original_probe = _v4._audio_probe_state
    original_finish = _v4._finish_fresh_first
    original_seed = _v5.seed_cooled_history_sources

    _v4._audio_probe_state = _strict_remote_audio_probe_factory(
        minimum_mean_db=minimum_mean_db,
        probe_seconds=probe_seconds,
    )
    _v4._finish_fresh_first = _fresh_only_finish_factory(
        unknown_candidate_cap=unknown_candidate_cap,
    )
    _v5.seed_cooled_history_sources = _retry_safe_seed_factory(original_seed)

    try:
        return _v5.ensure_audio_animal_sources(
            settings,
            plan,
            slot=slot,
            slot_dir=slot_dir,
            source_manifest=source_manifest,
            ledger=ledger,
        )
    finally:
        _v4._audio_probe_state = original_probe
        _v4._finish_fresh_first = original_finish
        _v5.seed_cooled_history_sources = original_seed
        _append_v6_audit(
            settings,
            slot=slot,
            slot_dir=slot_dir,
            probe_seconds=probe_seconds,
            unknown_candidate_cap=unknown_candidate_cap,
        )
