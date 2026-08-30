# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя после visual review.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

## Локально подтверждено

- Windows path `D:\KiraS\VV_knopka`, `.venv` Python 3.11.
- Latest shown OpenAI ledger `$0.0340 / $10.00`; publication gate PASS.
- Slot 1 octopus = manual QUALITY PASS.
- Cat renderer local FFmpeg; Impact + real meow; no voiceover/BGM.
- Production cats = broad generic `#NNN — Котики` / `#NNN — Cats`, narrow trend themes abandoned.
- Latest generic slot 2 manually accepted as normal.
- Strict near-9:16 gate manually validated: all six selected Pexels clips were exactly 720×1280 / aspect 0.5625.

## Current milestone: better cat footage through YouTube CC

Pexels is technically acceptable but can feel stock-like. Goal: find funnier/more natural cat footage with verified YouTube Creative Commons Attribution and keep Pexels/Pixabay fallback.

Old no-key yt-dlp license discovery was exhausted: two scans, including 6000-day window, returned 0 verified CC because `license` is optional metadata.

## Google Cloud / YouTube Data API — AVAILABLE

Earlier Google Cloud signup looked unsuitable, but this changed on 2026-08-30: user successfully entered Google Cloud Console, selected project `VV Knopka`, enabled YouTube Data API v3, created an API key, and stored it locally in `.env` as:

```text
YOUTUBE_API_KEY=...
```

Never ask user to paste the key. Never commit `.env` or secrets. Public metadata search does not require OAuth/channel access.

## Official `vv-cat-youtube` v3

Entry point now maps to:

```text
src/vv_knopka/youtube_cat_source_v3.py
```

and `pyproject.toml` contains:

```text
vv-cat-youtube = vv_knopka.youtube_cat_source_v3:main
```

### `cc-search` — official API preferred

If `YOUTUBE_API_KEY` exists:

```powershell
vv-cat-youtube cc-search
```

uses:

```text
YouTube Data API search.list
videoLicense=creativeCommon
query default = cat|kitten
wide lookback (default 6000 days)
-> videos.list snippet/statistics/status/contentDetails
-> status.license must equal creativeCommon
-> rank by views/day then views
-> runtime/trends/youtube-cat-cc-official.json
```

Defaults: `scan-per-query=30`, `limit=15`; API max per search is capped at 50 in code. Repeated `--query` can replace the default query. `--no-key` forces the old no-key CC-filter fallback.

Expected prefix:

```text
YouTube CC search: official YouTube Data API (videoLicense=creativeCommon)
Public metadata only; no OAuth, no channel login, no media download
```

### `cc-import` — official recheck before download

Preferred import:

```powershell
vv-cat-youtube cc-import 2 --candidate N
```

For an official API report it:

1. validates report provenance and candidate rights flags;
2. requires local `YOUTUBE_API_KEY`;
3. calls current `videos.list(part=status,snippet,id=...)` again;
4. requires current `status.license == creativeCommon`;
5. downloads with yt-dlp only after that recheck;
6. validates real ffprobe near-9:16 orientation;
7. requires >= clip_seconds and audible source audio;
8. prepends accepted YouTube CC source to production `sources.json`;
9. writes attribution report.

Accepted source keeps title/creator/URL, license, attribution, SHA/dimensions/audio, `rights_verified=true`, `rights_verification_method=youtube_data_api_status_license`, `api_status_license=creativeCommon`.

Normal:

```powershell
vv render-animal 2
```

then uses imported YouTube CC first and stock fills remaining target slots.

### Legacy/fallback modes

- `vv-cat-youtube cc ... --url ...` remains a strict legacy URL mode requiring direct yt-dlp CC license metadata.
- no-key v2 YouTube search-filter backend remains available through `cc-search --no-key`, but official API is preferred now.

## Ordinary YouTube private comparison

Standard/unverified YouTube does not become production permission just because use is local. No automatic standard-license download in production flow.

Already-local exact files can be isolated:

```powershell
vv-cat-youtube test-add 2 --url "https://youtube..." --file "D:\path\cat.mp4" --confirm-match
vv-cat-youtube test-render 2
```

Storage only under `runtime/test_only/slot-02/`, never production sources or ready_for_review. Required locks: `do_not_publish=true`, `publication_allowed=false`, `commercial_use_allowed=false`, `rights_verified=false`.

## Tests / CI

Before official API backend: v2 code had 58 tests.

Official v3 added four tests for API discovery/dedupe, official rights evidence, report provenance, and API-key recheck requirement.

GitHub CI `test` job on code head `042ae76fc711b4cf10ab042ac70afd1560e8db5f`: **62 passed in 0.41s**, `Verify pilot lock` success. Windows bootstrap was still running separately at last check; recheck before claiming whole workflow success.

## Immediate next local step

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-youtube.exe cc-search
```

If candidates appear, send top list and choose N, then:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate N
.\.venv\Scripts\vv.exe render-animal 2
```

If API returns HTTP 400/403/quota error, send only console error text, never the key.

Do not merge Draft PR #1 until explicit user approval after visual pilot review.
