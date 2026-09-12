from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .settings import Settings


SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
)


class YouTubeUploadLimitReached(RuntimeError):
    """YouTube channel daily upload limit; safe to defer and retry later."""

    def __init__(self, message: str, *, slot: int = 0, retry_not_before: str | None = None):
        super().__init__(message)
        self.slot = int(slot or 0)
        self.retry_not_before = retry_not_before


def youtube_dir(settings: Settings) -> Path:
    path = settings.runtime_dir / "youtube"
    path.mkdir(parents=True, exist_ok=True)
    return path


def client_secret_path(settings: Settings) -> Path:
    configured = str(settings.raw.get("youtube", {}).get("client_secret_file") or "runtime/youtube/client_secret.json")
    path = Path(configured)
    return path if path.is_absolute() else settings.root / path


def token_path(settings: Settings) -> Path:
    return youtube_dir(settings) / "token.json"


def channel_binding_path(settings: Settings) -> Path:
    return youtube_dir(settings) / "channel.json"


def upload_limit_state_path(settings: Settings) -> Path:
    return youtube_dir(settings) / "upload-limit.json"


def _google_imports():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise RuntimeError(
            "YouTube uploader dependencies are missing. Run `pip install -e .[dev]` after pulling the latest branch."
        ) from exc
    return Request, Credentials, InstalledAppFlow, build, MediaFileUpload


def _save_token(path: Path, credentials: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(credentials.to_json(), encoding="utf-8")


def _load_credentials(settings: Settings, *, interactive: bool) -> Any:
    Request, Credentials, InstalledAppFlow, _, _ = _google_imports()
    token = token_path(settings)
    credentials = None
    if token.exists():
        credentials = Credentials.from_authorized_user_file(str(token), SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        _save_token(token, credentials)
    if credentials and credentials.valid:
        return credentials
    if not interactive:
        raise RuntimeError("YouTube OAuth token is missing/invalid. Run `vv-youtube auth` interactively first.")

    secret = client_secret_path(settings)
    if not secret.exists():
        raise RuntimeError(
            f"YouTube OAuth client file not found: {secret}. Download a Desktop app OAuth JSON from Google Cloud "
            "and save it there; do not commit it."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(secret), scopes=list(SCOPES))
    credentials = flow.run_local_server(port=0, open_browser=True, access_type="offline", prompt="consent")
    _save_token(token, credentials)
    return credentials


def _service(settings: Settings, *, interactive: bool):
    _, _, _, build, _ = _google_imports()
    credentials = _load_credentials(settings, interactive=interactive)
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def _current_channel(service: Any) -> dict[str, str]:
    response = service.channels().list(part="id,snippet", mine=True).execute()
    items = response.get("items") or []
    if len(items) != 1:
        raise RuntimeError(f"Expected one authorized YouTube channel, got {len(items)}.")
    item = items[0]
    return {
        "channel_id": str(item.get("id") or ""),
        "channel_title": str((item.get("snippet") or {}).get("title") or ""),
    }


def authorize_and_bind(settings: Settings) -> dict[str, str]:
    service = _service(settings, interactive=True)
    channel = _current_channel(service)
    if not channel["channel_id"]:
        raise RuntimeError("Authorized account did not return a YouTube channel ID.")
    payload = {
        **channel,
        "bound_at": datetime.now(timezone.utc).isoformat(),
        "scope": list(SCOPES),
    }
    channel_binding_path(settings).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return channel


def _require_bound_service(settings: Settings):
    binding_path = channel_binding_path(settings)
    if not binding_path.exists():
        raise RuntimeError("YouTube channel is not bound. Run `vv-youtube auth` and verify the displayed channel first.")
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    service = _service(settings, interactive=False)
    current = _current_channel(service)
    if str(binding.get("channel_id") or "") != current["channel_id"]:
        raise RuntimeError(
            "Authorized YouTube channel no longer matches the locally bound channel. Refusing upload to prevent wrong-channel publishing."
        )
    return service, current


def _receipt_path(metadata_path: Path) -> Path:
    return metadata_path.with_suffix(".youtube.json")


def _load_metadata(metadata_path: Path) -> dict[str, Any]:
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    video = Path(str(raw.get("video_file") or ""))
    if not video.exists() or video.stat().st_size <= 0:
        raise RuntimeError(f"Video file from metadata does not exist or is empty: {video}")
    raw["_video_path"] = video
    return raw


def _normalize_tags(raw: Any) -> list[str]:
    if not isinstance(raw, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    total_chars = 0
    for item in raw:
        value = " ".join(str(item or "").split()).strip().lstrip("#")
        key = value.casefold()
        if not value or key in seen:
            continue
        projected = total_chars + len(value) + (1 if result else 0)
        if projected > 450:
            break
        seen.add(key)
        result.append(value[:100])
        total_chars = projected
        if len(result) >= 12:
            break
    return result


def _youtube_error_reasons(exc: BaseException) -> set[str]:
    content = getattr(exc, "content", None)
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    if isinstance(content, str):
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            errors = (payload.get("error") or {}).get("errors") or []
            reasons = {
                str(item.get("reason") or "")
                for item in errors
                if isinstance(item, dict) and item.get("reason")
            }
            if reasons:
                return reasons
    text = str(exc)
    return {"uploadLimitExceeded"} if "uploadLimitExceeded" in text else set()


def _write_upload_limit_state(settings: Settings, *, slot: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    retry = now + timedelta(hours=24)
    state = {
        "reason": "uploadLimitExceeded",
        "slot": int(slot or 0),
        "observed_at": now.isoformat(),
        "retry_not_before": retry.isoformat(),
    }
    upload_limit_state_path(settings).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def active_upload_limit(settings: Settings) -> dict[str, Any] | None:
    path = upload_limit_state_path(settings)
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        retry = datetime.fromisoformat(str(state.get("retry_not_before") or ""))
        if retry.tzinfo is None:
            retry = retry.replace(tzinfo=timezone.utc)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    if datetime.now(timezone.utc) >= retry:
        try:
            path.unlink()
        except OSError:
            pass
        return None
    return state


def _clear_upload_limit_state(settings: Settings) -> None:
    try:
        upload_limit_state_path(settings).unlink()
    except FileNotFoundError:
        pass


def upload_one(settings: Settings, metadata_path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    metadata_path = metadata_path.resolve()
    receipt = _receipt_path(metadata_path)
    if receipt.exists():
        existing = json.loads(receipt.read_text(encoding="utf-8"))
        return {"skipped": True, "reason": "already_uploaded", **existing}

    metadata = _load_metadata(metadata_path)
    youtube_cfg = settings.raw.get("youtube", {})
    requested_privacy = str(youtube_cfg.get("privacy_status") or "public").strip().lower()
    if requested_privacy not in {"public", "unlisted", "private"}:
        raise RuntimeError(f"Unsupported youtube.privacy_status={requested_privacy!r}")

    tags = _normalize_tags(metadata.get("youtube_tags"))
    contains_synthetic_media = bool(metadata.get("contains_synthetic_media", False))
    preview = {
        "slot": int(metadata.get("slot") or 0),
        "pipeline": str(metadata.get("pipeline") or ""),
        "language": str(metadata.get("language") or "en"),
        "video_file": str(metadata["_video_path"]),
        "title": str(metadata.get("youtube_title") or "").strip(),
        "description": str(metadata.get("youtube_description") or "").strip(),
        "tags": tags,
        "contains_synthetic_media": contains_synthetic_media,
        "requested_privacy": requested_privacy,
    }
    if dry_run:
        return {"dry_run": True, **preview}

    service, channel = _require_bound_service(settings)
    _, _, _, _, MediaFileUpload = _google_imports()
    snippet = {
        "title": preview["title"],
        "description": preview["description"],
        "categoryId": str(youtube_cfg.get("category_id") or "15"),
        "defaultLanguage": preview["language"],
    }
    if tags:
        snippet["tags"] = tags

    status = {
        "privacyStatus": requested_privacy,
        "selfDeclaredMadeForKids": bool(youtube_cfg.get("made_for_kids", False)),
    }
    if contains_synthetic_media:
        status["containsSyntheticMedia"] = True

    body = {"snippet": snippet, "status": status}
    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(metadata["_video_path"]), chunksize=8 * 1024 * 1024, resumable=True),
        notifySubscribers=bool(youtube_cfg.get("notify_subscribers", False)),
    )
    response = None
    try:
        while response is None:
            _, response = request.next_chunk()
    except Exception as exc:
        if "uploadLimitExceeded" in _youtube_error_reasons(exc):
            state = _write_upload_limit_state(settings, slot=preview["slot"])
            raise YouTubeUploadLimitReached(
                "YouTube daily channel upload limit reached; defer uploads and retry after the 24-hour cooldown.",
                slot=preview["slot"],
                retry_not_before=str(state["retry_not_before"]),
            ) from exc
        raise

    _clear_upload_limit_state(settings)
    video_id = str(response.get("id") or "")
    actual_privacy = str((response.get("status") or {}).get("privacyStatus") or requested_privacy)
    result = {
        "slot": preview["slot"],
        "pipeline": preview["pipeline"],
        "language": preview["language"],
        "video_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
        "channel_id": channel["channel_id"],
        "channel_title": channel["channel_title"],
        "requested_privacy": requested_privacy,
        "actual_privacy": actual_privacy,
        "publication_state": "UPLOADED",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "metadata_file": str(metadata_path),
        "video_file": preview["video_file"],
        "title": preview["title"],
        "youtube_tags": tags,
        "contains_synthetic_media": contains_synthetic_media,
    }
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def ready_metadata(settings: Settings) -> list[Path]:
    ready = settings.runtime_dir / "ready_for_review"
    paths = list(ready.glob("slot-*.upload.json")) if ready.exists() else []

    def slot_number(path: Path) -> int:
        try:
            return int(path.name.split("-", 2)[1])
        except (ValueError, IndexError):
            return 10**9

    return sorted(paths, key=slot_number)


def pending_ready_metadata(settings: Settings) -> list[Path]:
    return [path for path in ready_metadata(settings) if not _receipt_path(path).exists()]


def pending_ready_count(settings: Settings) -> int:
    return len(pending_ready_metadata(settings))


def upload_ready(
    settings: Settings,
    *,
    limit: int | None = None,
    newest: bool = False,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    pending = pending_ready_metadata(settings)
    if newest:
        pending.reverse()
    if limit is not None:
        pending = pending[: max(int(limit), 0)]
    if not pending:
        return []

    if not dry_run:
        cooldown = active_upload_limit(settings)
        if cooldown is not None:
            return [{
                "deferred": True,
                "reason": "upload_limit",
                "slot": int(cooldown.get("slot") or 0),
                "retry_not_before": str(cooldown.get("retry_not_before") or ""),
                "message": "YouTube daily upload limit cooldown is still active.",
            }]

    results: list[dict[str, Any]] = []
    for path in pending:
        try:
            results.append(upload_one(settings, path, dry_run=dry_run))
        except YouTubeUploadLimitReached as exc:
            results.append({
                "deferred": True,
                "reason": "upload_limit",
                "slot": exc.slot,
                "retry_not_before": exc.retry_not_before,
                "message": str(exc),
            })
            break
    return results
