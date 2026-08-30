# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя после visual review.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

## Локально подтверждено

- Windows path `D:\KiraS\VV_knopka`, `.venv` Python 3.11.
- Latest shown OpenAI ledger before clean-review: **$0.0509 / $10.00**; publication gate PASS.
- Slot 1 octopus = manual QUALITY PASS.
- Cat renderer local FFmpeg; Impact + real meow; no voiceover/BGM.
- Production cats = broad generic `#NNN — Котики` / `#NNN — Cats`; narrow themes abandoned.
- Generic vertical slot 2 baseline manually accepted as normal.
- Strict near-9:16 stock baseline validated: six Pexels sources exactly 720×1280 / aspect 0.5625.

## YouTube Data API / CC

User has Google Cloud project `VV Knopka`, enabled YouTube Data API v3 and stores `YOUTUBE_API_KEY` locally in ignored `.env`. Never ask for or commit the key.

Official API CC discovery works: `search.list(videoLicense=creativeCommon)` plus `videos.status.license=creativeCommon` returned 15 real CC candidates.

First imported candidates 1, 8, 14 were all technically valid CC, 2160×3840 and audible, but all came from `Pawcsu` and were visually packaged with `Pawcsu/@Pawcsu` branding + large captions.

## Full clean-footage gate — confirmed locally

User ran `vv-cat-youtube cc-clean 2` and got:

```text
YouTube clean-footage audit: 0 kept / 3 reviewed
[REJECT] 3YVtMMK1Uoc | confidence=0.99 | Pawcsu/@Pawcsu branding + large headline caption
[REJECT] 8IYWJiho1fQ | confidence=1.00 | Pawcsu/@Pawcsu branding + large caption
[REJECT] 9DL-J0hKxtM | confidence=1.00 | Pawcsu branding/avatar/handle + large headline caption
```

This is the desired behavior. Do not crop/blur such branding to make a source pass. Production `sources.json` no longer contains those three YouTube entries; downloaded files remain only for audit/local inspection.

Full import gate remains:

```text
official CC recheck -> download -> near-9:16 -> duration -> audible audio -> 4-frame Luna clean review -> production only on PASS
```

Any production YouTube clip must carry `clean_footage_approved=true`.

## Current implementation: YouTube CC v5 prescreen

`pyproject.toml` now maps:

```text
vv-cat-youtube = vv_knopka.youtube_cat_source_v5:main
```

New module:

```text
src/vv_knopka/youtube_cc_prescreen.py
```

Official `cc-search` v5 now does:

```text
exact YouTube API CC search
-> default queries: funny cat / funny kitten / cat playing / cat reaction
-> larger ranked CC pool
-> enrich canonical channel + thumbnail
-> max one candidate per channel
-> Luna thumbnail prescreen
-> require domestic cat
-> reject branding/@handle/avatar/social UI/watermark/large caption/split-screen/ranking/repost packaging
-> save only clean-looking candidates to official report
```

Thumbnail prescreen is only a cheap prefilter. It does not replace the final 4-frame gate after `cc-import` downloads the actual video.

Expected v5 header:

```text
YouTube CC search v5: official API + clean thumbnail prescreen
No OAuth/channel login; thumbnails only at prescreen; no media download
```

Output candidate label is `[API-CC+CLEAN?]` and includes `clean-thumb=<confidence>`.

## Tests / CI

Latest code-head CI after v5:

```text
73 passed in 0.59s
Verify pilot lock: success
```

Windows-bootstrap was still running at that check. Recheck live final-head CI before claiming the entire latest workflow is green.

## Immediate next local step

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-youtube.exe cc-search
```

Expected pytest ≈ **73 passed**. `cc-search` now makes a few small Luna thumbnail-review calls under the existing `$10` budget.

User should send the complete new `cc-search` output. IMPORTANT: v5 overwrites `runtime/trends/youtube-cat-cc-official.json`; after that, candidate numbers refer to the new clean-prescreened report, not the old 15-item list.

Then import promising candidates one by one:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate N
```

A thumbnail PASS may still fail the strict full-video gate; do not bypass it. Once several clean YouTube CC clips pass, render slot 2 and compare against the accepted Pexels baseline.

## Ordinary YouTube test-only

Standard/unverified YouTube is not production-safe just because testing is local. Already-local exact files may only use `test-add` / `test-render` under `runtime/test_only`, with `do_not_publish=true`, `publication_allowed=false`, `commercial_use_allowed=false`, `rights_verified=false`.

Do not merge Draft PR #1 until explicit user approval after visual pilot review.
