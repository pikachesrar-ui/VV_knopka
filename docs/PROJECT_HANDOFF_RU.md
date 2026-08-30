# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя после visual review.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

## Локально подтверждено

- Windows path `D:\KiraS\VV_knopka`, `.venv` Python 3.11.
- Latest shown OpenAI ledger **$0.0530 / $10.00**; publication gate PASS.
- Latest shown local pytest **73 passed in 0.47s** before v5.1 pull.
- Slot 1 octopus = manual QUALITY PASS.
- Cat renderer local FFmpeg; Impact + real meow; no voiceover/BGM.
- Production cats = broad generic `#NNN — Котики` / `#NNN — Cats`; narrow themes abandoned.
- Generic vertical slot 2 baseline manually accepted as normal.
- Strict near-9:16 stock baseline validated: six Pexels sources exactly 720×1280 / aspect 0.5625.

## YouTube Data API / Creative Commons

User has Google Cloud project `VV Knopka`, enabled YouTube Data API v3 and stores `YOUTUBE_API_KEY` locally in ignored `.env`. Never ask for or commit the key.

Official API discovery works with `search.list(videoLicense=creativeCommon)` plus `videos.status.license=creativeCommon` verification.

## Full clean-footage gate — proven useful

Three first Pawcsu CC imports were technically valid (CC, 2160×3840, audible) but visually packaged. `cc-clean 2` rejected all 3 at confidence 0.99–1.00 for `Pawcsu/@Pawcsu`, avatar/branding and large added captions. This is desired. Never crop/blur branding merely to make such media pass.

A production YouTube clip must ultimately carry `clean_footage_approved=true`.

## v5 official search — local result

Thumbnail-prescreened search produced:

```text
Thumbnail prescreen: 2 selected / 30 reviewed / 45 raw CC
Creative Commons cat candidates: 2
```

Candidates:

```text
01 nWieRK7Fw-g | 10,628,088 views | 태어나서 깻잎 처음 맛본 고양이의 반응ㅋㅋㅋ | 걸뽀 | clean-thumb=0.90
02 hxXfevBB9Zs | 1,347,892 views | 🐱😻 Kucing Kaget!!! 🤣🤣🤣🤣🤣 | Kumpulan Video Hewan Lucu | clean-thumb=0.90
```

Candidate 2 looked like an aggregator/compilation channel from its channel name and was not preferred.

## Critical finding: thumbnail PASS can still hide packaged video

User ran:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 1
```

The full 2160×3840 source downloaded, then strict clean gate rejected it:

```text
ValueError: YouTube CC candidate passed the license/format gates but failed the clean-footage anti-repost gate:
Frames visibly include livestream/social chat UI, creator branding, and large Korean caption overlays in a split-screen presentation.
```

So thumbnail-only prescreen is useful but insufficient. The final temporal gate worked correctly.

## Current implementation: v5.1 low-resolution temporal preflight

New module:

```text
src/vv_knopka/youtube_cc_preflight.py
```

`vv-cat-youtube` still routes to `youtube_cat_source_v5:main`, but the v5 implementation has been upgraded to v5.1 behavior.

### Search

Official `cc-search` now does:

```text
exact API CC search
-> funny cat / funny kitten / cat playing / cat reaction
-> reject-memory filter for locally failed video IDs
-> one candidate per channel
-> Luna thumbnail prescreen
-> official report
```

Expected header:

```text
YouTube CC search v5.1: official API + clean thumbnail prescreen + reject memory
```

Known failed video IDs are read from:

```text
runtime/slots/*/youtube_clean_reviews/*.json
```

If `clean_footage_approved=false`, that video ID is omitted from future official search results before thumbnail review. This should exclude `nWieRK7Fw-g` on the next run.

### Import

Official `cc-import` now uses two visual stages:

```text
1. official API status.license=creativeCommon recheck
2. LOW-RES preview download (prefer <=360p)
3. 4-frame Luna clean-footage review on preview
4. if PREVIEW REJECT -> stop; DO NOT download production-quality media
5. if PREVIEW PASS -> download full-quality source
6. real ffprobe near-9:16 + duration + audible-audio gates
7. full-quality 4-frame Luna clean review
8. only final PASS may remain in production sources.json
```

Expected pass output begins:

```text
Low-res temporal clean preflight: PASS | confidence=...
```

and later:

```text
Full clean-footage gate: PASS | confidence=...
```

This preserves the strict final gate while avoiding full-quality downloads for obviously packaged/chat/overlay videos.

The yt-dlp warning about missing JS runtime was non-fatal in the observed candidate-1 run; download succeeded. It is not the cause of the clean rejection.

## Tests / CI

Preflight/reject-memory regression tests cover:

- reading failed clean-review video IDs;
- filtering known rejects from search candidate pools;
- low-res preflight rejection before production import;
- low-res preflight pass metadata.

GitHub code-head CI:

```text
77 passed in 0.59s
Verify pilot lock: success
```

Windows-bootstrap was still running at that exact check. Documentation commits followed; always inspect live final HEAD/CI before making a stronger claim.

## Immediate next local step

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-youtube.exe cc-search
```

Expected pytest ≈ **77 passed**.

Send the new `cc-search` output. The previously rejected `nWieRK7Fw-g` should be skipped. Do not import from the stale two-candidate report after re-running search; use the new candidate ranks.

## Ordinary YouTube test-only

Standard/unverified YouTube is not production-safe just because testing is local. Already-local exact files may only use `test-add` / `test-render` under `runtime/test_only`, with `do_not_publish=true`, `publication_allowed=false`, `commercial_use_allowed=false`, `rights_verified=false`.

Do not merge Draft PR #1 until explicit user approval after visual pilot review.
