# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний показанный OpenAI ledger: **$0.0618 / $10.00**.
- Последний локальный pytest: **81 passed in 0.55s**.
- Slot 1 RU AI Short = manual QUALITY PASS.
- Cat renderer = local FFmpeg; real meow + Impact; no voiceover/BGM.
- Generic slot 2 `#001 — Котики` пользователь оценил как нормальный.
- Vertical gate подтверждён: accepted stock baseline = 6/6 Pexels clips at **720x1280 / aspect 0.5625**.

## Official YouTube Creative Commons works locally

User enabled YouTube Data API v3 and stores `YOUTUBE_API_KEY` only in ignored `.env`. Never ask for or commit the key.
Official API discovery + exact `status.license=creativeCommon` works.

## Clean-footage gate confirmed on obvious packaging

Three first Pawcsu imports were technically valid CC/9:16/audio, but `cc-clean 2` correctly rejected all 3 for visible account branding and large added captions:

```text
0 kept / 3 reviewed
3YVtMMK1Uoc REJECT 0.99
8IYWJiho1fQ REJECT 1.00
9DL-J0hKxtM REJECT 1.00
```

Do not crop/blur such branding to force a pass.

## v5 / v5.1 local search results

First thumbnail-prescreened run:

```text
Thumbnail prescreen: 2 selected / 30 reviewed / 45 raw CC
01 nWieRK7Fw-g | 10,628,088 views | 걸뽀 | clean-thumb=0.90
02 hxXfevBB9Zs | 1,347,892 views | Kumpulan Video Hewan Lucu | clean-thumb=0.90
```

`nWieRK7Fw-g` passed thumbnail screening but the full gate correctly rejected visible livestream/chat UI, creator branding and large Korean captions. This proved thumbnail-only screening is insufficient.

v5.1 added low-res temporal preflight before full production download plus reject memory.

Next local search after reject memory:

```text
Known full/preview-gate rejects skipped: 2
Thumbnail prescreen: 1 selected / 30 reviewed / 43 raw CC after reject memory
Creative Commons cat candidates: 1
01 hxXfevBB9Zs | 1,347,970 views | 🐱😻 Kucing Kaget!!! 🤣🤣🤣🤣🤣 | Kumpulan Video Hewan Lucu | clean-thumb=0.95
```

## hxXfevBB9Zs — RECHECKED WITH CONTACT-SHEET-AWARE GATE

The old full-quality v1 gate had rejected this clip with wording about a `2x2 compilation/collage`, which could have confused our generated 2x2 contact sheet with the source itself. clean-footage v2 fixed that ambiguity by explicitly distinguishing the analysis layout from real source-frame collages and sequential multi-clip edits.

User pulled v6, then locally confirmed:

```text
81 passed in 0.55s
OpenAI spent: $0.0618 / $10.00
auto_publish: False
publication gate: PASS
```

Re-import of current candidate 1 then failed **during low-res temporal preflight before any production-quality re-download**:

```text
YouTube CC candidate failed low-resolution temporal clean preflight before full download:
The cat is visible and no social branding or captions appear, but the sampled frames show clearly unrelated scenes and multiple animals/events, strongly indicating a stitched compilation.
```

This is now considered a **proven reject**, not a contact-sheet false positive. The corrected gate no longer complains about the outer 2x2 analysis sheet; it identifies temporal evidence of unrelated scenes / multiple animals and treats the source as a stitched compilation.

Operationally this validates the v2 distinction:

- clean single-scene/raw footage may pass;
- real sequential compilations fail as `multi_clip_sequence` / stitched unrelated scenes;
- generated 2x2 contact sheet alone is not a reject reason.

Because the failure occurred at low-res preflight, no new full-quality media download was needed for this recheck.

## Current YouTube source status

So far, **0 YouTube CC clips are accepted for production**:

- 3 Pawcsu clips rejected for branding/captions.
- `nWieRK7Fw-g` rejected for livestream/chat/UI/caption packaging.
- `hxXfevBB9Zs` rejected after v2 recheck as a real stitched compilation.

Pexels/Pixabay remain the accepted licensed fallback. Do not loosen clean gates merely to increase yield.

## New official search after three remembered rejects

User reran `cc-search` with the current v6/v5.1 stack:

```text
Known full/preview-gate rejects skipped: 3
Thumbnail prescreen: 2 selected / 30 reviewed / 42 raw CC after reject memory
Creative Commons cat candidates: 2
```

Current saved official report candidates:

```text
01 cQE-s_wsclw | 1,947,387 views | OMG Cute Cat Domino Reaction #shorts | Hilarious Cats | clean-thumb=0.98
02 I_pdwiLlvuc | 225,755 views | Cutest Angry Cat You’ll Ever See 😾❤️ | Kawaiipets | clean-thumb=0.90
```

Both channel names are somewhat generic/aggregator-like, so neither should be trusted from metadata alone. Candidate 1 is the first recommended temporal-preflight test because its title looks like one specific cat reaction and it has the stronger thumbnail confidence. The low-res temporal preflight remains the deciding next gate.

Do **not** rerun `cc-search` before testing these ranks, because the saved report/rank numbers may change.

## clean-footage v2 / CLI

Current CLI routes through:

```text
vv-cat-youtube = vv_knopka.youtube_cat_source_v6:main
```

v2 explicitly tells Luna:

- the outer 2x2 image is OUR generated analysis sheet;
- each tile is a different timestamp from one source video;
- never call the source a collage merely because the analysis image is 2x2 or tiles differ;
- `source_frame_collage=true` only when an individual source-frame tile itself contains split-screen/collage/ranking packaging;
- `multi_clip_sequence=true` only with strong evidence that unrelated clips are sequentially stitched together (different cats/locations/camera sources etc.);
- ordinary motion/reframing/time progression is not enough.

Gate remains strict on real branding, social UI, large captions and actual repost/compilation packaging.

Reject memory is version-aware:

- old obvious branding/UI/caption rejects remain remembered;
- stale v1 collage-only rejects were eligible for one v2 recheck;
- `hxXfevBB9Zs` is now rejected by current v2 behavior and is remembered going forward.

## Tests / CI

Latest code-head CI test job before the latest search:

```text
81 passed in 0.52s
Verify pilot lock: success
```

User independently confirmed local **81 passed in 0.55s**.

Draft PR #1 remains review-only; do not merge without explicit user decision after visual review.

## Immediate next local step

Do not rerun search. Test current candidate 1 through the low-res temporal preflight:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 1
```

If candidate 1 is rejected, then test candidate 2 from the same saved report:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 2
```

A preflight reject is expected to stop before production-quality download. A PASS proceeds to full media, real 9:16/audio checks and the final full-quality clean gate. Send the complete output after candidate 1 before changing search state.
