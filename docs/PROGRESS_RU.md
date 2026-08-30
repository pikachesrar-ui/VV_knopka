# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний показанный OpenAI ledger: **$0.0618 / $10.00** (до последнего candidate-1 preflight/import; не угадывать более новый ledger).
- Последний локальный pytest: **81 passed in 0.55s** (до нового aspect-preflight фикса).
- Slot 1 RU AI Short = manual QUALITY PASS.
- Cat renderer = local FFmpeg; real meow + Impact; no voiceover/BGM.
- Generic slot 2 `#001 — Котики` пользователь оценил как нормальный.
- Vertical gate подтверждён: accepted stock baseline = 6/6 Pexels clips at **720x1280 / aspect 0.5625**.

## Official YouTube Creative Commons works locally

User enabled YouTube Data API v3 and stores `YOUTUBE_API_KEY` only in ignored `.env`. Never ask for or commit the key.
Official API discovery + exact `status.license=creativeCommon` works.

## Proven rejects so far

- Three Pawcsu CC clips: reject for visible account branding + large captions.
- `nWieRK7Fw-g`: reject for livestream/social chat UI, creator branding and Korean caption overlays.
- `hxXfevBB9Zs`: after contact-sheet-aware v2 recheck, reject as real stitched multi-clip sequence.

Do not crop/blur branding and do not weaken gates merely to raise yield.

## Current search report

Latest user search:

```text
Known full/preview-gate rejects skipped: 3
Thumbnail prescreen: 2 selected / 30 reviewed / 42 raw CC after reject memory
Creative Commons cat candidates: 2
01 cQE-s_wsclw | 1,947,387 views | OMG Cute Cat Domino Reaction #shorts | Hilarious Cats | clean-thumb=0.98
02 I_pdwiLlvuc | 225,755 views | Cutest Angry Cat You’ll Ever See 😾❤️ | Kawaiipets | clean-thumb=0.90
```

Do not rerun `cc-search` before testing these current ranks.

## cQE-s_wsclw — FORMAT REJECT FOUND

User tested current candidate 1. Its low-res clean preflight had passed, so production media was downloaded. Deterministic production validation then rejected it:

```text
ValueError: YouTube cat source is 502x720; production/test cat sources must already be near 9:16 portrait
```

`502/720 ≈ 0.6972`, whereas 9:16 is `0.5625`; with configured tolerance `0.08`, this is outside the accepted range. The rejection is correct, but it happened too late: full media had already downloaded and the visual preflight had already run.

## Aspect/duration preflight — IMPLEMENTED

`src/vv_knopka/youtube_cc_preflight.py` now runs deterministic preview gates **before Luna**:

```text
low-res preview download
-> real ffprobe dimensions
-> near-9:16 check using the same source_aspect_tolerance
-> minimum duration check
-> ONLY THEN Luna temporal clean review
-> ONLY THEN production-quality download
```

So a future `502x720` candidate must fail before OpenAI vision spend and before full-quality download.

Deterministic format rejects are written to:

```text
runtime/slots/<slot>/youtube_preflight_rejects/<video-id>.json
```

with `durable_reject=true`. Reject memory now includes those files as well as clean-review rejects. Transient preview decode/tool failures are auditable but **not** durable rejects, so a temporary yt-dlp/ffprobe problem does not permanently poison a candidate.

Current v6 version-aware reject memory was updated to preserve these deterministic format rejects while retaining the previous clean-review version rules.

## Tests / CI

New regression coverage verifies:

- `502x720` is rejected at low-res format preflight;
- Luna is not called for that deterministic reject;
- a durable format-reject audit is written;
- format rejects are included in future search reject-memory;
- existing temporal clean preflight behavior remains intact.

GitHub CI `test` job on code head `0644e8aebef937a5348a224ba4dfe32594513a53` completed successfully, including `Test` and `Verify pilot lock`. Windows-bootstrap was still running at that exact check.

## Immediate next local step

Pull/reinstall, then re-run current candidate 1 **once** from the still-current two-candidate report:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 1
```

Expected behavior: it should now fail at `low-resolution format preflight before Luna/full download` with dimensions near the same `502x720` aspect (the exact low-res dimensions may be scaled but aspect should match), and create a durable reject audit. The already-downloaded full file can remain on disk for audit; it must not enter production.

Then, **without rerunning search**, test current candidate 2:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 2
```

Send the output for candidate 2 (and candidate 1 if behavior differs from expectation). Draft PR #1 remains review-only; do not merge without explicit user decision after visual review.
