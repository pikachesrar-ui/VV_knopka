# VV_knopka — Agent Rules

This file is the mandatory entry point for any new ChatGPT/Codex/agent session working on this repository.

## 1. Read order before doing work

Before changing code or giving project-status claims:

1. Read this file completely.
2. Read `docs/PROJECT_HANDOFF_RU.md` completely.
3. Read `docs/PROGRESS_RU.md` completely for the newest operational checkpoint.
4. Check the current repository state, active branch, and draft PR #1.
5. Treat GitHub as the source of truth for code/history; handoff as product intent; `PROGRESS_RU.md` as the live checkpoint.

## 2. Project goal

Build a review-first short-form video production pipeline for a 15-video YouTube Shorts pilot under **Animals / Nature Curiosities**.

Two pipelines:

- `ai_short`: original animal/nature fact/story Short through MoneyPrinterTurbo.
- `animal_compilation`: cat compilation assembled locally with FFmpeg.

## 3. Frozen pilot scope

Until the user explicitly changes it:

- 15 Shorts total.
- 8 `ai_short`.
- 7 `animal_compilation`.
- Exactly 2 Russian experiments total: slot 1 AI + slot 2 cats.
- Remaining 13 Shorts are English.
- One YouTube channel for the pilot.
- Project-side OpenAI budget cap: **$10 USD**.
- `auto_publish=false` and human review required.
- Production outputs only to `runtime/ready_for_review`.
- Do not silently add paid providers or increase paid usage.

## 4. Current cat production rules

- Cat renderer = local FFmpeg; MoneyPrinterTurbo is not needed.
- **Production mode is a broad cat compilation, not a narrow themed episode.**
- `render-animal` ignores stale `trend-theme.json` and builds a generic cat plan (`Котики` / `Cats`).
- Reddit/community/theme tooling may remain as research/reference tooling, but it does not drive production rendering unless the user explicitly changes this decision again.
- No voiceover.
- No background music.
- One fixed real meow on black intro/transition/end cards.
- No loud bass/drop/impact/boom SFX.
- Intro/inter-clip cards repeat the unique numbered episode title; end card is localized.
- Windows card font = accepted **Impact** (`C:\Windows\Fonts\impact.ttf`); do not restart font experiments without a concrete reason.
- Cat stock must have genuine audible source audio; effectively silent clips fail closed.
- Cat source footage must already be vertical and close to **9:16**. Landscape 16:9, square, and visibly-wide portrait footage fail the source gate rather than relying on blur-fill.
- Current configured width/height tolerance from 9/16 is `0.08`.
- Cached/local/imported clips must be checked with real `ffprobe` dimensions as well as provider metadata.
- If fewer than 5 unique licensed, audible, vertical production clips are available, fail closed.
- Every production clip keeps provenance/licensing metadata.

## 5. YouTube / UGC source rules

- YouTube Creative Commons Attribution is an allowed production candidate only after rights evidence is verified and attribution is preserved.
- User now has `YouTube Data API v3` enabled and a local `YOUTUBE_API_KEY` in ignored `.env`; never ask for the key or commit it.
- `vv-cat-youtube cc-search` must **prefer the official YouTube Data API** when the key is present: `search.list(videoLicense=creativeCommon)` plus `videos.list` and `status.license == creativeCommon`.
- The no-key YouTube CC-filter/yt-dlp path remains fallback/research only (`--no-key`) because yt-dlp license metadata is optional.
- Preferred production import is `vv-cat-youtube cc-import <slot> --candidate N` from a saved official CC report. It must recheck current `status.license == creativeCommon` through the API immediately before download.
- The imported source still must pass near-9:16, duration and audible-audio gates before entering production `sources.json`.
- Standard/unverified YouTube media is **not** production media merely because the current use is a local experiment.
- A separate test-only path may accept an already-local file for private quality comparison, but it must stay under `runtime/test_only`, carry `do_not_publish=true`, `publication_allowed=false`, `commercial_use_allowed=false`, and never enter production `sources.json` or `runtime/ready_for_review`.
- Do not add automatic downloading of standard/unverified YouTube/TikTok media as the normal workflow.
- Reddit/community posts are references only; a public post is not reuse permission.

## 6. YouTube/content-safety rules

- The system is not a mass-upload spam bot.
- Avoid highly repetitive or near-duplicate uploads.
- Keep duplicate/similarity gates enabled.
- Preserve AI-disclosure metadata where relevant.
- Human review remains required before publishing during the pilot.

## 7. Architecture constraints

- `VV_knopka` is orchestration/business logic.
- Do not vendor/fork the entire MoneyPrinterTurbo codebase into Git history without a strong reason.
- Local ignored `MoneyPrinterTurbo/` checkout is allowed.
- Use MPT only for `ai_short` where practical.
- Edge TTS remains the default AI-short TTS; cat compilation has no voiceover.
- Keep secrets out of Git. `.env` must never be committed.
- Real meow binary stays local/ignored (`runtime/assets/...`) or via `CAT_MEOW_FILE`.

## 8. Git workflow

Development branch: `mvp/pilot-scaffold`.
Draft review vehicle: **PR #1** into `main`.

- Continue on the existing branch/PR unless there is a concrete reason to split.
- Do not merge PR #1 merely because tests pass; rendered pilot videos need visual review first.
- Keep `docs/PROJECT_HANDOFF_RU.md` and `docs/PROGRESS_RU.md` current.
- GitHub wins over docs on mechanical facts such as SHA/CI/file list.

## 9. Current milestone

Slot 1 Russian AI Short (octopus) has manual **QUALITY PASS**.

Slot 2 cat base format now also has an important manual checkpoint:

1. Impact cards / real meow / no voice / no BGM are accepted.
2. Narrow themes were rejected in favor of generic `#001 — Котики`.
3. Near-9:16 gate is locally confirmed: the latest user render selected six sources and **all six were exactly 720×1280 (9:16)**.
4. User's verdict on this generic vertical render: **«да, норм»**.
5. Current focus is testing whether officially verified YouTube Creative Commons can supply funnier/more UGC-like cats than Pexels.
6. Google Cloud/YouTube Data API key is now available locally, so official API CC discovery is preferred over no-key discovery.
7. Keep Pexels/Pixabay as licensed fallback.
8. Ordinary unverified YouTube files, if used for private quality comparison, stay in the isolated test-only flow and are never production candidates.
9. Only after cat sourcing is accepted, return to slot 3 / remaining pilot.

## 10. Language policy for cats

- Never publish translated duplicates of the same cat episode.
- Long-run cadence: `en, en, en, en, ru` (80% EN / 20% RU).
- Frozen pilot: slot 2 RU, remaining six cat slots EN.
- Do not use `Daily Dose of Cats` or a close imitation.

## 11. Context persistence

At the end of every substantial work session, update handoff/progress so a fresh chat can resume from GitHub without relying on conversational memory.
