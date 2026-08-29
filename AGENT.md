# VV_knopka — Agent Rules

This file is the mandatory entry point for any new ChatGPT/Codex/agent session working on this repository.

## 1. Read order before doing work

Before changing code or giving project-status claims:

1. Read this file completely.
2. Read `docs/PROJECT_HANDOFF_RU.md` completely.
3. Read `docs/PROGRESS_RU.md` completely for the newest operational checkpoint.
4. Check the current repository state, active branch, and draft PR #1.
5. Treat GitHub as the source of truth for code/history; treat the handoff as the source of truth for product intent and agreed constraints; treat `PROGRESS_RU.md` as the short live checkpoint.

## 2. Project goal

Build a review-first short-form video production pipeline for a 15-video YouTube Shorts pilot.

Editorial umbrella: **Animals / Nature Curiosities**.

Two content pipelines:

- `ai_short`: original animal/nature fact/story Short generated with AI assistance and rendered through MoneyPrinterTurbo.
- `animal_compilation`: cute/funny cat/animal compilation with editorial framing and local FFmpeg assembly.

## 3. Frozen pilot scope

Until the user explicitly changes it:

- 15 Shorts total.
- 8 `ai_short`.
- 7 `animal_compilation`.
- Exactly 2 Russian experiments total: 1 per pipeline.
- Remaining 13 Shorts are English.
- All pilot videos go to one YouTube channel for now.
- Project-side OpenAI API pilot budget cap: **$10 USD**.
- Automatic publishing is **disabled** during the pilot/review stage.
- Output must go to `runtime/ready_for_review` for human inspection.
- Do not silently increase paid API usage or add new paid providers.

## 4. Animal compilation rules

- Cat/animal renderer is **local FFmpeg** and does not require MoneyPrinterTurbo to be running.
- No loud bass/drop/impact/boom transition SFX.
- Current cat format uses one short meow on black title cards; user wants one fixed **real** meow asset rather than a synthetic sound.
- No background music in the current cat format.
- No voiceover in the current cat format.
- Intro and inter-clip black cards repeat the unique numbered episode title; end card is localized `Спасибо за просмотр` / `Thanks for watching`.
- Long card text must wrap safely inside 1080x1920; do not regress to one-line overflow.
- Cat stock must have **audible source audio**, not merely a technically present silent stream. Current gate probes audio and rejects effectively silent clips.
- If fewer than 5 relevant licensed audible clips are available, fail closed rather than silently relaxing the rule.
- Do not implement a raw social-media repost scraper as the default workflow.
- Every accepted clip must retain source/provenance metadata.
- Commercial-use permission/licensing must be explicitly represented before a clip passes the source gate.
- Reused-content/copyright risk is a first-class product concern, not an afterthought.

## 5. YouTube/content-safety rules

- The system is not a mass-upload spam bot.
- Avoid highly repetitive scripts/templates and near-duplicate uploads.
- Keep duplicate/similarity checks enabled.
- Preserve AI-disclosure metadata where relevant.
- Human review remains required before publishing during the pilot.

## 6. Architecture constraints

- `VV_knopka` is our orchestration/business-logic repository.
- Do not vendor or fork the entire MoneyPrinterTurbo codebase into Git history unless there is a strong, documented reason.
- A local ignored checkout at `MoneyPrinterTurbo/` is allowed for runtime integration.
- Integrate with current MoneyPrinterTurbo through its local API for `ai_short` where practical.
- MoneyPrinterTurbo currently exposes `/api/v1/videos` and task-status endpoints; verify upstream before making compatibility-sensitive changes.
- Edge TTS remains the preferred free/default TTS for AI shorts; cat compilation currently has no voiceover.
- Keep secrets out of Git. `.env`/local config must never be committed.
- Binary meow asset should stay local/ignored (`runtime/assets/...`) or be referenced via `CAT_MEOW_FILE`; do not commit third-party sound binaries by default.

## 7. Git workflow

Current development branch: `mvp/pilot-scaffold`.

Current review vehicle: **draft PR #1** into `main`.

Rules:

- Continue work on the existing MVP branch/PR unless there is a concrete reason to split work.
- Do not merge PR #1 merely because tests pass; rendered pilot videos must be visually reviewed first.
- Keep `docs/PROJECT_HANDOFF_RU.md` updated for durable project context and `docs/PROGRESS_RU.md` updated for the newest operational checkpoint.
- If documentation contradicts live GitHub state on a mechanical fact (commit SHA, CI result, file list), GitHub wins and docs should be corrected.

## 8. Current milestone

Slot 1 (Russian `ai_short`, octopus) has received manual **QUALITY PASS**.

Current work is intentionally focused on slot 2 cats before returning to slot 3:

1. Re-render **slot 2 Russian cat compilation** with safe wrapped title cards, no voice, no BGM, longer black transitions and localized end card.
2. Use one chosen real meow asset when available.
3. Require 5-6 licensed relevant stock clips with genuine source audio; inspect `animal_audio_sources.json` if the gate cannot find enough.
4. Human-review title fit, timing, meow, source audio and pacing.
5. Only after cat format is accepted, return to the first English AI short / remaining pilot.

## 9. Language policy for cats

- Never publish a translated duplicate of the same cat episode.
- Long-run original-content cadence: `en, en, en, en, ru` (80% EN / 20% RU).
- Frozen pilot remains slot 2 RU and the other six animal slots EN.
- Do not use `Daily Dose of Cats` or a close imitation as the series/title phrase.

## 10. Context persistence rule

At the end of every substantial work session, update the handoff/progress docs so a fresh chat can resume from GitHub without relying on conversational memory.
