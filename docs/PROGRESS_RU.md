# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний показанный OpenAI ledger: **$0.0509 / $10.00**.
- Последний локальный pytest до clean-footage v4: **62 passed in 0.48s**.
- Slot 1 RU AI Short = manual QUALITY PASS.
- Cat renderer = local FFmpeg; real meow + Impact; no voiceover/BGM.
- Generic slot 2 `#001 — Котики` пользователь оценил как нормальный.
- Vertical gate локально подтверждён: accepted stock baseline = 6/6 Pexels clips at **720x1280 / aspect 0.5625**.

## Official YouTube Creative Commons works locally

User enabled YouTube Data API v3, created a local API key and stores it only in ignored `.env` as `YOUTUBE_API_KEY`. Never ask for or commit the key.

Official run:

```text
vv-cat-youtube cc-search
YouTube CC search: official YouTube Data API (videoLicense=creativeCommon)
Creative Commons cat candidates: 15
```

Report: `runtime/trends/youtube-cat-cc-official.json`.

## Three real CC imports succeeded technically

User imported candidates 1, 8 and 14 from the saved official report:

- `9DL-J0hKxtM` — `Never about drinking water! 😼` — creator `Pawcsu` — 2160×3840 — audio mean -12.0 dB.
- `8IYWJiho1fQ` — `What was the reason for this? 👀` — creator `Pawcsu` — 2160×3840 — audio mean -18.9 dB.
- `3YVtMMK1Uoc` — `What was this cat trying to do 🤔🐾` — creator `Pawcsu` — 2160×3840 — audio mean -47.4 dB.

All three showed `Rights evidence: youtube_data_api_status_license` and `License: YouTube Creative Commons Attribution`; thus API CC + 9:16 + audio gates all worked.

`vv render-animal 2` then succeeded and created `runtime/ready_for_review/slot-02-ru-animals.mp4` with six sources (YouTube CC + Pexels fallback).

## New visual blocker found: packaged/repost-like Shorts

User showed candidate 8 visually. It contains a large top block with `Pawcsu`, `@Pawcsu`, avatar/verification badge and a large pre-added caption `What was the reason for this?`.

Decision: this is not the visual style wanted for production. Do not solve it by cropping/blurring the account branding. Prefer relatively raw/self-contained cat footage.

## Clean-footage / anti-repost gate — IMPLEMENTED

New files/paths:

- `src/vv_knopka/youtube_clean_footage.py`
- `src/vv_knopka/youtube_cat_source_v4.py`
- `src/vv_knopka/animal_audio_sources_v2.py`
- `vv-cat-youtube` now routes to `youtube_cat_source_v4:main`.
- `vv render-animal` now routes cat source preparation through the v2 wrapper that refuses unreviewed YouTube clips.

Flow for new production YouTube CC import:

```text
official API CC recheck
-> download
-> near-9:16 + duration + audible audio
-> sample 4 frames into 2x2 contact sheet
-> Luna clean-footage review
-> only PASS may remain in production sources.json
```

The clean gate rejects any sampled frame with prominent:

- creator/channel name or `@handle`;
- avatar/profile/banner;
- TikTok/Instagram/Reels/Shorts-style UI/watermark;
- large added meme/headline caption;
- split-screen/collage/ranking packaging;
- obvious already-compiled/repost layout.

Incidental environmental text (signs, labels, plates) is allowed. Gate is fail-closed: even `approved=true` cannot pass if a forbidden flag is true. Config: `youtube_clean_vision_min_confidence=0.78`, max estimated call cost `$0.02` inside existing project-side `$10` budget.

Every production YouTube clip must now carry `clean_footage_approved=true`. Old imported YouTube clips without that flag are removed from the active source manifest before `render-animal`; stock fallback fills missing positions.

### Migration command for current three imports

After pulling/reinstalling:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-clean 2
```

This reviews the existing YouTube clips, keeps clean passes, removes rejected clips from production `sources.json`, writes:

```text
runtime/slots/02/youtube_clean_audit.json
runtime/slots/02/youtube_clean_reviews/<video-id>.json
```

Downloaded files are left intact for audit/local inspection.

## Tests / CI

Clean-footage v4 added 7 regression tests. GitHub CI `test` job on code head `90d471f18c50f9643980eacc28b0bdd8132e6021` passed:

```text
69 passed in 0.56s
Verify pilot lock: success
```

Windows bootstrap was still running at that check. Docs commits came afterward; recheck live head/CI before claiming entire final workflow complete.

## Immediate next local step

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-youtube.exe cc-clean 2
```

Expected pytest count: about **69**. `cc-clean 2` may make up to three small Luna review calls (cached thereafter) and therefore may increment the existing OpenAI ledger slightly.

Send the complete `cc-clean 2` output before importing more candidates. Do not merge Draft PR #1 without explicit user decision after visual review.
