import json
from pathlib import Path

import vv_knopka.youtube_metadata_backfill as backfill
from vv_knopka.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        raw={
            "pilot": {"runtime_dir": "runtime", "openai_budget_usd": 10.0, "auto_publish": False},
            "youtube": {"enabled": True, "auto_publish": True, "privacy_status": "public", "category_id": "15"},
        },
        root=tmp_path,
    )


def _published(settings: Settings, *, slot: int, pipeline: str, language: str) -> None:
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True, exist_ok=True)
    kind = "animals" if pipeline == "animal_compilation" else "ai"
    video = ready / f"slot-{slot:02d}-{language}-{kind}.mp4"
    video.write_bytes(b"video")
    metadata = ready / f"slot-{slot:02d}-{language}-{kind}.upload.json"
    metadata.write_text(
        json.dumps(
            {
                "slot": slot,
                "pipeline": pipeline,
                "language": language,
                "video_file": str(video),
                "youtube_title": f"Slot {slot} #shorts",
                "youtube_description": "old local description",
            }
        ),
        encoding="utf-8",
    )
    metadata.with_suffix(".youtube.json").write_text(
        json.dumps({"slot": slot, "video_id": f"video-{slot}"}),
        encoding="utf-8",
    )


class _Request:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _Videos:
    def __init__(self, snippets):
        self.snippets = snippets
        self.updates = []

    def list(self, *, part, id, maxResults):
        assert part == "snippet"
        ids = id.split(",")
        items = [
            {"id": video_id, "snippet": dict(self.snippets[video_id])}
            for video_id in ids
            if video_id in self.snippets
        ]
        return _Request({"items": items})

    def update(self, *, part, body):
        assert part == "snippet"
        self.updates.append(body)
        return _Request({"id": body["id"]})


class _Service:
    def __init__(self, snippets):
        self._videos = _Videos(snippets)

    def videos(self):
        return self._videos


def test_parse_slot_spec_supports_ranges_and_lists():
    assert backfill.parse_slot_spec("1-3,5,8-9") == {1, 2, 3, 5, 8, 9}
    assert backfill.parse_slot_spec(None) is None


def test_append_missing_hashtags_is_idempotent_and_exact():
    description, added = backfill._append_missing_hashtags("hello\n\n#shorts #catshorts", ["#cats", "#shorts"])
    assert description == "hello\n\n#shorts #catshorts\n\n#cats"
    assert added == ["#cats"]
    again, added_again = backfill._append_missing_hashtags(description, ["#cats", "#shorts"])
    assert again == description
    assert added_again == []


def test_merge_tags_preserves_more_than_twelve_existing_tags():
    existing = [f"legacy-{index}" for index in range(15)]
    merged, added = backfill._merge_tags_preserving_existing(existing, ["cats", "funny cats"])
    assert merged[:15] == existing
    assert len(merged) >= 15
    assert all(value in merged for value in added)


def test_dry_run_merges_cat_tags_without_remote_update(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    _published(settings, slot=2, pipeline="animal_compilation", language="ru")
    service = _Service(
        {
            "video-2": {
                "title": "Existing title #shorts",
                "description": "Existing description",
                "categoryId": "15",
                "tags": ["existing"],
                "defaultLanguage": "ru",
            }
        }
    )
    monkeypatch.setattr(backfill, "_readonly_service", lambda settings: service)

    results = backfill.backfill_published_metadata(settings, slots={2}, apply=False)

    assert len(results) == 1
    assert results[0]["changed"] is True
    assert results[0]["applied"] is False
    assert "existing" not in results[0]["added_tags"]
    assert "cats" in [item.casefold() for item in results[0]["added_tags"]]
    assert "#shorts" in [item.casefold() for item in results[0]["added_hashtags"]]
    assert service._videos.updates == []


def test_apply_updates_snippet_only_and_preserves_remote_title(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    _published(settings, slot=3, pipeline="ai_short", language="en")
    slot_dir = settings.runtime_dir / "slots" / "03"
    slot_dir.mkdir(parents=True, exist_ok=True)
    (slot_dir / "plan.json").write_text(
        json.dumps(
            {
                "visual_anchor": "otter",
                "hashtags": ["#otters", "#animalfacts", "#shorts"],
            }
        ),
        encoding="utf-8",
    )
    service = _Service(
        {
            "video-3": {
                "title": "Remote title must stay",
                "description": "Remote description must stay",
                "categoryId": "15",
                "tags": ["legacy tag"],
                "defaultLanguage": "en",
            }
        }
    )
    monkeypatch.setattr(backfill, "_metadata_edit_service", lambda settings: service)

    results = backfill.backfill_published_metadata(settings, slots={3}, apply=True)

    assert results[0]["applied"] is True
    assert len(service._videos.updates) == 1
    body = service._videos.updates[0]
    assert set(body) == {"id", "snippet"}
    assert body["id"] == "video-3"
    assert body["snippet"]["title"] == "Remote title must stay"
    assert body["snippet"]["description"].startswith("Remote description must stay")
    assert "#otters" in body["snippet"]["description"]
    assert "legacy tag" in body["snippet"]["tags"]
    assert "otter" in body["snippet"]["tags"]
    assert "status" not in body


def test_metadata_edit_service_loads_full_scope_set(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    token = settings.runtime_dir / "youtube" / "token.json"
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text("{}", encoding="utf-8")

    captured = {}

    class _Credentials:
        expired = False
        refresh_token = None
        valid = True

        @classmethod
        def from_authorized_user_file(cls, filename, scopes=None):
            captured["filename"] = filename
            captured["scopes"] = tuple(scopes or ())
            return cls()

        def has_scopes(self, scopes):
            return backfill.EDIT_SCOPE in set(captured["scopes"]) and set(scopes).issubset(set(captured["scopes"]))

    class _RequestClass:
        pass

    service = object()
    monkeypatch.setattr(
        backfill,
        "_google_imports",
        lambda: (_RequestClass, _Credentials, object(), lambda *args, **kwargs: service, object()),
    )
    monkeypatch.setattr(backfill, "_require_same_bound_channel", lambda settings, service: {"channel_id": "x"})

    assert backfill._metadata_edit_service(settings) is service
    assert backfill.EDIT_SCOPE in captured["scopes"]
    assert set(backfill.METADATA_SCOPES).issubset(set(captured["scopes"]))
