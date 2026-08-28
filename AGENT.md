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
- `animal_compilation`: cute/funny animal compilation with meaningful editorial framing and local FFmpeg assembly.

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

- No loud bass/drop/impact/boom transition SFX.
- Prefer micro-fades, natural audio continuity, silence, or very soft transition treatment.
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
- Integrate with current MoneyPrinterTurbo through its local API where practical.
- MoneyPrinterTurbo currently exposes `/api/v1/videos` and task-status endpoints; verify upstream before making compatibility-sensitive changes.
- Edge TTS is the preferred free/default TTS for the pilot unless testing shows a quality blocker.
- Keep secrets out of Git. `.env`/local config must never be committed.

## 7. Git workflow

Current development branch: `mvp/pilot-scaffold`.

Current review vehicle: **draft PR #1** into `main`.

Rules:

- Continue work on the existing MVP branch/PR unless there is a concrete reason to split work.
- Do not merge PR #1 merely because tests pass; the first two rendered pilot videos should be visually reviewed first.
- Keep `docs/PROJECT_HANDOFF_RU.md` updated for durable project context and `docs/PROGRESS_RU.md` updated for the newest operational checkpoint.
- If documentation contradicts live GitHub state on a mechanical fact (commit SHA, CI result, file list), GitHub wins and docs should be corrected.

## 8. Definition of the next milestone

The immediate milestone is not “finish all 15 videos.” It is:

1. Set up the project on the user's Windows PC.
2. Configure the OpenAI key locally.
3. Run the status/budget checks.
4. Install/start MoneyPrinterTurbo locally.
5. Produce **slot 1: Russian `ai_short`**.
6. Inspect the rendered result manually.
7. Produce **slot 2: Russian `animal_compilation`** after obtaining suitable licensed/source-tracked clips.
8. Use those two videos to adjust style/quality before batch-producing the remaining 13.

## 9. Context persistence rule

At the end of every substantial work session, update the handoff/progress docs so a fresh chat can resume from GitHub without relying on conversational memory.
