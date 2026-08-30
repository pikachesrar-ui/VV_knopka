from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .settings import Settings


SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
)


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
        raise RuntimeError("YouTube OAuth token is missing/invalid. Run `vv youtube-auth` interactively first.")

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
        raise RuntimeError("YouTube channel is not bound. Run `vv youtube-auth` and verify the displayed channel first.")
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

    preview = {
        "slot": int(metadata.get("slot") or 0),
        "video_file": str(metadata["_video_path"]),
        "title": str(metadata.get("youtube_title") or "").strip(),
        "description": str(metadata.get("youtube_description") or "").strip(),
        "requested_privacy": requested_privacy,
    }
    if dry_run:
        return {"dry_run": True, **preview}

    service, channel = _require_bound_service(settings)
    _, _, _, _, MediaFileUpload = _google_imports()
    body = {
        "snippet": {
            "title": preview["title"],
            "description": preview["description"],
            "categoryId": str(youtube_cfg.get("category_id") or "15"),
            "defaultLanguage": str(metadata.get("language") or "en"),
        },
        "status": {
            "privacyStatus": requested_privacy,
            "selfDeclaredMadeForKids": bool(youtube_cfg.get("made_for_kids", False)),
        },
    }
    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(metadata["_video_path"]), chunksize=8 * 1024 * 1024, resumable=True),
        notifySubscribers=bool(youtube_cfg.get("notify_subscribers", False)),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = str(response.get("id") or "")
    actual_privacy = str((response.get("status") or {}).get("privacyStatus") or requested_privacy)
    result = {
        "slot": preview["slot"],
        "video_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
        "channel_id": channel["channel_id"],
        "channel_title": channel["channel_title"],
        "requested_privacy": requested_privacy,
        "actual_privacy": actual_privacy,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "metadata_file": str(metadata_path),
        "video_file": preview["video_file"],
        "title": preview["title"],
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


def upload_ready(
    settings: Settings,
    *,
    limit: int | None = None,
    newest: bool = False,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    pending = [path for path in ready_metadata(settings) if not _receipt_path(path).exists()]
    if newest:
        pending.reverse()
    if limit is not None:
        pending = pending[: max(int(limit), 0)]
    return [upload_one(settings, path, dry_run=dry_run) for path in pending]
