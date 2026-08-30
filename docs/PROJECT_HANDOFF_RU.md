# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя после visual review.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

## Локально подтверждено

- Windows path `D:\KiraS\VV_knopka`, `.venv` Python 3.11.
- Latest shown OpenAI ledger **$0.0509 / $10.00**; publication gate PASS.
- Latest local pytest before clean-footage v4: **62 passed in 0.48s**.
- Slot 1 octopus = manual QUALITY PASS.
- Cat renderer local FFmpeg; Impact + real meow; no voiceover/BGM.
- Production cats = broad generic `#NNN — Котики` / `#NNN — Cats`; narrow trend themes abandoned.
- Generic vertical slot 2 baseline manually accepted as normal.
- Strict near-9:16 stock baseline validated: six Pexels sources exactly 720×1280 / aspect 0.5625.

## YouTube Data API / CC — WORKING LOCALLY

User has project `VV Knopka`, enabled YouTube Data API v3, created API key and stores it locally in ignored `.env` as `YOUTUBE_API_KEY`. Never ask for the key or commit it.

Official `vv-cat-youtube cc-search` works and returned 15 Creative Commons cat candidates using `search.list(videoLicense=creativeCommon)` plus `videos.list` confirmation `status.license=creativeCommon`.

Report:

```text
runtime/trends/youtube-cat-cc-official.json
```

## First real YouTube CC import experiment

User imported candidates **1, 8, 14** from the saved official report. All three succeeded technically:

```text
9DL-J0hKxtM  Never about drinking water! 😼          Pawcsu  2160x3840  audio -12.0 dB
8IYWJiho1fQ  What was the reason for this? 👀        Pawcsu  2160x3840  audio -18.9 dB
3YVtMMK1Uoc  What was this cat trying to do 🤔🐾     Pawcsu  2160x3840  audio -47.4 dB
```

Each showed:

```text
Rights evidence: youtube_data_api_status_license
License: YouTube Creative Commons Attribution
```

Then `vv render-animal 2` succeeded with six sources (YouTube CC + Pexels fallback), output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

So official rights check + download + 9:16 + audible-audio + mixed-source rendering all work.

## New problem discovered by manual visual review

User showed candidate 8. The source contains a large social-media-style top block:

- `Pawcsu`
- `@Pawcsu`
- avatar / verification badge
- large caption `What was the reason for this?`

This is not desired production footage. It visually looks like taking another account's already-packaged Short, even though the YouTube upload itself is API-confirmed CC.

Product decision: **do not crop/blur branding to make such material pass**. Prefer relatively raw/self-contained cat footage. CC license verification and visual cleanliness are separate gates.

## YouTube clean-footage v4 — IMPLEMENTED

`pyproject.toml` now maps:

```text
vv-cat-youtube = vv_knopka.youtube_cat_source_v4:main
```

New modules:

```text
src/vv_knopka/youtube_clean_footage.py
src/vv_knopka/youtube_cat_source_v4.py
src/vv_knopka/animal_audio_sources_v2.py
```

`vv` cat rendering now imports source preparation from `animal_audio_sources_v2`, which wraps the existing audio/vertical stock gate and removes unreviewed legacy YouTube clips before rendering.

### New production import flow

```text
official YouTube API status.license=creativeCommon recheck
-> yt-dlp download
-> real ffprobe near-9:16 gate
-> duration gate
-> audible-source gate
-> four-frame 2x2 contact sheet
-> GPT-5.6 Luna clean-footage review
-> production sources.json only on PASS
```

Clean review rejects prominent:

- creator/channel names, `@handles`, avatars/banners;
- social-platform watermarks/UI/chrome;
- large added meme/headline captions;
- split-screen/collage/ranking layout;
- obvious already-compiled/repost packaging.

It allows incidental environmental text such as signs, labels and license plates. This is a presentation/provenance-risk gate, not legal rights verification.

Config:

```toml
youtube_clean_vision_min_confidence = 0.78
youtube_clean_vision_max_estimated_cost_usd = 0.02
```

Fail-closed rule: model `approved=true` is still rejected if any forbidden packaging flag is true. A production YouTube clip must store `clean_footage_approved=true` plus review confidence/reason/flags/hash/review path.

### Legacy/current import cleanup

Current three Pawcsu imports predate v4 and therefore do not yet have `clean_footage_approved=true`.

Migration command:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-clean 2
```

It reviews current YouTube entries, keeps only passes, removes rejects from production `sources.json`, rewrites attribution, and saves:

```text
runtime/slots/02/youtube_clean_audit.json
runtime/slots/02/youtube_clean_reviews/<video-id>.json
runtime/slots/02/youtube_clean_reviews/<video-id>.jpg
```

Downloaded media remains on disk for audit/local inspection. Clean review is SHA-cached, so re-running unchanged clips should not spend again.

Even if user skips `cc-clean`, `vv render-animal 2` now sanitizes the active manifest first: YouTube sources without `clean_footage_approved=true` are removed and Pexels/Pixabay fill missing positions.

### New import behavior

For all future:

```powershell
vv-cat-youtube cc-import 2 --candidate N
```

CC/format/audio may pass but clean gate may reject. Expected reject message begins:

```text
YouTube CC candidate passed the license/format gates but failed the clean-footage anti-repost gate
```

Do not bypass it; try another candidate.

## Tests / CI

v4 added 7 regression tests for:

- raw clean decision pass;
- creator branding fail even if model says approved;
- large caption fail;
- low-confidence fail;
- render sanitizer removing legacy/unapproved YouTube while keeping stock and clean-reviewed YouTube;
- rejected import rollback from production manifest;
- passed import clean metadata persistence.

GitHub CI `test` job on code head `90d471f18c50f9643980eacc28b0bdd8132e6021`:

```text
69 passed in 0.56s
Verify pilot lock: success
```

Windows-bootstrap was still running at that exact check. Documentation commits followed afterward; always inspect live head/CI before claiming the full latest workflow is green.

## Immediate next local checkpoint

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-youtube.exe cc-clean 2
```

Expected pytest ≈ **69 passed**. `cc-clean 2` may issue up to three small Luna calls under the existing `$10` project budget; latest user ledger before this work is `$0.0509`.

User should send the full `cc-clean 2` output. Based on PASS/REJECT results, search/import more CC candidates until several clean YouTube sources are available, then render and visually compare against the Pexels baseline.

## Ordinary YouTube test-only remains isolated

Standard/unverified YouTube is not production-safe just because testing is local. Already-local exact files may only use `test-add` / `test-render` under `runtime/test_only`, with `do_not_publish=true`, `publication_allowed=false`, `commercial_use_allowed=false`, `rights_verified=false`.

Do not merge Draft PR #1 until explicit user approval after visual pilot review.
