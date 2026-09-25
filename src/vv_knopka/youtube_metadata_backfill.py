from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .publication_metadata import (
    _CAT_HASHTAGS_EN,
    _CAT_HASHTAGS_RU,
    _hashtags,
    _youtube_tags,
)
from .settings import Settings
from .youtube_uploader import (
    SCOPES,
    _current_channel,
    _google_imports,
    _load_credentials,
    _normalize_tags,
    _save_token,
    channel_binding_path,
    client_secret_path,
    ready_metadata,
    token_path,
)


EDIT_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
METADATA_SCOPES = tuple(dict.fromkeys((*SCOPES, EDIT_SCOPE)))


def parse_slot_spec(value: str | None) -> set[int] | None:
    if value is None or not str(value).strip():
        return None
    result: set[int] = set()
    for raw in str(value).split(","):
        part = raw.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            start, end = int(left), int(right)
            if start <= 0 or end <= 0 or end < start:
                raise ValueError(f"invalid slot range: {part!r}")
            result.update(range(start, end + 1))
        else:
            slot = int(part)
            if slot <= 0:
                raise ValueError(f"invalid slot: {part!r}")
            result.add(slot)
    return result


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _receipt_path(metadata_path: Path) -> Path:
    return metadata_path.with_suffix(".youtube.json")


def _published_targets(settings: Settings, slots: set[int] | None) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for metadata_path in ready_metadata(settings):
        metadata = _read_json(metadata_path)
        slot = int(metadata.get("slot") or 0)
        if slot <= 0 or (slots is not None and slot not in slots):
            continue
        receipt_path = _receipt_path(metadata_path)
        receipt = _read_json(receipt_path)
        video_id = str(receipt.get("video_id") or "").strip()
        if not video_id:
            continue
        targets.append(
            {
                "slot": slot,
                "pipeline": str(metadata.get("pipeline") or receipt.get("pipeline") or "").strip(),
                "language": str(metadata.get("language") or receipt.get("language") or "en").strip().lower(),
                "video_id": video_id,
                "metadata_path": metadata_path,
                "receipt_path": receipt_path,
            }
        )
    return sorted(targets, key=lambda item: int(item["slot"]))


def _desired_discovery_metadata(settings: Settings, target: dict[str, Any]) -> tuple[list[str], list[str]]:
    slot = int(target["slot"])
    pipeline = str(target.get("pipeline") or "")
    language = str(target.get("language") or "en")

    if pipeline == "animal_compilation":
        hashtags = _hashtags(_CAT_HASHTAGS_RU if language == "ru" else _CAT_HASHTAGS_EN)
        tags = _youtube_tags(hashtags, "cats", "funny cats", "cat compilation", "animals")
        return hashtags, tags

    plan = _read_json(settings.runtime_dir / "slots" / f"{slot:02d}" / "plan.json")
    fallback = ("#животные", "#факты", "#shorts") if language == "ru" else ("#animals", "#animalfacts", "#shorts")
    hashtags = _hashtags(list(plan.get("hashtags") or []), fallback=fallback)
    anchor = str(plan.get("visual_anchor") or "").strip()
    tags = _youtube_tags(hashtags, anchor, "animal facts", "nature facts", "animals")
    return hashtags, tags


def _append_missing_hashtags(description: str, hashtags: Iterable[str]) -> tuple[str, list[str]]:
    value = str(description or "")
    existing = {match.casefold() for match in re.findall(r"(?<!\w)#[\w]+", value, flags=re.UNICODE)}
    missing = [tag for tag in hashtags if str(tag).casefold() not in existing]
    if not missing:
        return value, []
    suffix = " ".join(missing)
    updated = f"{value.rstrip()}\n\n{suffix}" if value.strip() else suffix
    if len(updated.encode("utf-8")) > 5000:
        raise RuntimeError("metadata backfill would exceed YouTube's 5000-byte description limit")
    return updated, missing


def _youtube_tag_budget(values: list[str]) -> int:
    if not values:
        return 0
    total = max(len(values) - 1, 0)  # commas between tags count toward the API limit
    for value in values:
        total += len(value) + (2 if " " in value else 0)  # YouTube counts implicit quotes around tags with spaces
    return total


def _merge_tags_preserving_existing(
    current_tags: Iterable[Any],
    desired_tags: Iterable[Any],
    *,
    safe_limit: int = 450,
) -> tuple[list[str], list[str]]:
    """Keep every remote tag exactly as returned, then append safe new tags when space allows."""
    merged = [str(value) for value in current_tags if str(value or "").strip()]
    seen = {" ".join(value.split()).strip().lstrip("#").casefold() for value in merged}
    added: list[str] = []

    for value in _normalize_tags(list(desired_tags)):
        key = " ".join(value.split()).strip().lstrip("#").casefold()
        if not key or key in seen:
            continue
        candidate = merged + [value]
        if _youtube_tag_budget(candidate) > max(int(safe_limit), 0):
            continue
        merged.append(value)
        added.append(value)
        seen.add(key)
    return merged, added


def _require_same_bound_channel(settings: Settings, service: Any) -> dict[str, str]:
    binding = _read_json(channel_binding_path(settings))
    if not binding:
        raise RuntimeError("YouTube channel binding is missing. Run `vv-youtube auth` first.")
    current = _current_channel(service)
    if str(binding.get("channel_id") or "") != current["channel_id"]:
        raise RuntimeError("Authorized YouTube channel does not match the locally bound channel. Refusing metadata edit.")
    return current


def authorize_metadata_edit(settings: Settings) -> dict[str, str]:
    """Upgrade the local OAuth token with metadata-edit scope, preserving channel binding."""
    _, Credentials, InstalledAppFlow, build, _ = _google_imports()
    del Credentials
    secret = client_secret_path(settings)
    if not secret.exists():
        raise RuntimeError(f"YouTube OAuth client file not found: {secret}")

    token = token_path(settings)
    previous_token = token.read_text(encoding="utf-8") if token.exists() else None
    flow = InstalledAppFlow.from_client_secrets_file(str(secret), scopes=list(METADATA_SCOPES))
    credentials = flow.run_local_server(port=0, open_browser=True, access_type="offline", prompt="consent")
    service = build("youtube", "v3", credentials=credentials, cache_discovery=False)

    try:
        current = _require_same_bound_channel(settings, service)
    except Exception:
        if previous_token is not None:
            token.write_text(previous_token, encoding="utf-8")
        raise

    _save_token(token, credentials)
    binding_path = channel_binding_path(settings)
    binding = _read_json(binding_path)
    binding["scope"] = list(METADATA_SCOPES)
    binding["metadata_edit_authorized_at"] = datetime.now(timezone.utc).isoformat()
    binding_path.write_text(json.dumps(binding, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def _metadata_edit_service(settings: Settings):
    Request, Credentials, _, build, _ = _google_imports()
    token = token_path(settings)
    if not token.exists():
        raise RuntimeError("YouTube OAuth token is missing. Run `vv-youtube auth-metadata` first.")

    credentials = Credentials.from_authorized_user_file(str(token), scopes=list(METADATA_SCOPES))
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        _save_token(token, credentials)

    has_scopes = getattr(credentials, "has_scopes", None)
    if not credentials.valid or not callable(has_scopes) or not bool(has_scopes([EDIT_SCOPE])):
        raise RuntimeError(
            "Current YouTube OAuth token cannot edit video metadata. Run `vv-youtube auth-metadata` once, then retry."
        )
    service = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    _require_same_bound_channel(settings, service)
    return service


def _readonly_service(settings: Settings):
    credentials = _load_credentials(settings, interactive=False)
    _, _, _, build, _ = _google_imports()
    service = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    _require_same_bound_channel(settings, service)
    return service


def _remote_snippets(service: Any, video_ids: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for start in range(0, len(video_ids), 50):
        batch = video_ids[start : start + 50]
        if not batch:
            continue
        response = service.videos().list(
            part="snippet",
            id=",".join(batch),
            maxResults=len(batch),
        ).execute()
        for item in response.get("items") or []:
            video_id = str(item.get("id") or "")
            if video_id:
                result[video_id] = dict(item.get("snippet") or {})
    return result


def backfill_published_metadata(
    settings: Settings,
    *,
    slots: set[int] | None = None,
    apply: bool = False,
) -> list[dict[str, Any]]:
    """Merge discovery tags/hashtags into already-uploaded videos without reuploading them."""
    targets = _published_targets(settings, slots)
    if not targets:
        return []

    service = _metadata_edit_service(settings) if apply else _readonly_service(settings)
    snippets = _remote_snippets(service, [str(item["video_id"]) for item in targets])
    results: list[dict[str, Any]] = []

    for target in targets:
        video_id = str(target["video_id"])
        current = snippets.get(video_id)
        if current is None:
            results.append({**target, "missing": True, "applied": False})
            continue

        hashtags, desired_tags = _desired_discovery_metadata(settings, target)
        current_tags = [str(value) for value in (current.get("tags") or [])]
        merged_tags, added_tags = _merge_tags_preserving_existing(current_tags, desired_tags)
        new_description, added_hashtags = _append_missing_hashtags(
            str(current.get("description") or ""),
            hashtags,
        )
        changed = bool(added_tags or added_hashtags)

        result = {
            **target,
            "title": str(current.get("title") or ""),
            "added_tags": added_tags,
            "added_hashtags": added_hashtags,
            "changed": changed,
            "applied": False,
        }

        if apply and changed:
            snippet = {
                "title": str(current.get("title") or ""),
                "description": new_description,
                "categoryId": str(current.get("categoryId") or settings.raw.get("youtube", {}).get("category_id") or "15"),
                "tags": merged_tags,
            }
            for optional in ("defaultLanguage", "defaultAudioLanguage"):
                value = current.get(optional)
                if value:
                    snippet[optional] = value
            service.videos().update(
                part="snippet",
                body={"id": video_id, "snippet": snippet},
            ).execute()
            result["applied"] = True

        results.append(result)

    audit_path = settings.runtime_dir / "youtube" / "metadata-backfill-latest.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "apply": bool(apply),
                "slots": sorted(slots) if slots is not None else None,
                "results": [
                    {key: value for key, value in item.items() if key not in {"metadata_path", "receipt_path"}}
                    for item in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return results
