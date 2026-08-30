# VV_knopka — Agent Rules

This file is the mandatory entry point for any new ChatGPT/Codex/agent session working on this repository.

## 1. Read order before doing work

Before changing code or giving project-status claims:

1. Read this file completely.
2. Read `docs/PROJECT_HANDOFF_RU.md` completely.
3. Read `docs/PROGRESS_RU.md` completely for the newest operational checkpoint.
4. Check the current repository state, active branch, and draft PR #1.
5. Treat GitHub as source of truth for code/history; handoff as product intent; `PROGRESS_RU.md` as the live checkpoint.

## 2. Project goal

Build a review-first short-form video production pipeline under **Animals / Nature Curiosities** with two formats:

- `ai_short`: original animal/nature fact/story Short through MoneyPrinterTurbo.
- `animal_compilation`: cat compilation assembled locally with FFmpeg.

The original 15-video pilot is complete and serves as immutable validation history. Current development extends the same review-first system into deterministic unbounded generation.

## 3. Frozen pilot — immutable history

- 15 Shorts total.
- 8 `ai_short`, 7 `animal_compilation`.
- Slot 1 RU AI + slot 2 RU cats; slots 3–15 EN.
- All 15 ready outputs were generated on the user's machine.
- User subsequently reported the generated set looks normal/acceptable.
- Final explicitly shown OpenAI ledger after the pilot: **$0.1786 / $10.00**.
- Do not rebuild the frozen pilot solely for later metadata refinements.

## 4. Safety locks

Until the user explicitly changes them:

- Project-side OpenAI cap: **$10 USD**.
- `auto_publish=false`.
- Human review required.
- Production outputs only to `runtime/ready_for_review`.
- Do not silently add paid providers or increase paid usage.
- No uploader/OAuth in the current phase.
- Do not merge PR #1 merely because tests pass.

## 5. Cat production rules

- Cat renderer = local FFmpeg; MoneyPrinterTurbo is not needed.
- Broad/generic cat compilation; no voiceover and no BGM.
- Real meow on black intro/transition/end cards; no bass/drop/impact/boom SFX.
- Windows card font = `C:\Windows\Fonts\impact.ttf` with safe fallback elsewhere.
- Source footage must be licensed/commercial-use allowed, audible, already vertical and close to 9:16.
- Current aspect tolerance from 9/16 = `0.08`.
- Fewer than 5 unique usable clips -> fail closed.
- Every production clip keeps provenance/licensing metadata.
- Remote files confirmed to have no audio are filtered before Luna/candidate-cap accounting.
- Pexels/Pixabay are the normal automated downloadable stock path.
- Frozen pilot source reuse remains all-history protected.
- Long-run source reuse uses a **rolling cooldown of the previous 5 rendered cat episodes**. A source older than that window may return as fallback; using it again restarts its cooldown.
- Long-run sourcing is **fresh-first**: never-used candidates are ranked before cooled-down historical candidates.
- If a completed fresh-source pass still fails the minimum-count gate, long-run may seed **local Pexels/Pixabay files from rendered episodes outside the cooldown window**. These files are not trusted blindly: current geometry and audible-audio checks run again before acceptance.
- On retry after a recorded minimum-count failure, recover accepted local files from that failed audit and use cooled local history without paying to repeat the same fresh discovery pass first.
- Final reuse audit blocks heavy reuse inside the protected recent window while separately reporting cooled-down historical reuse.

## 6. YouTube / UGC compliance wording

- YouTube Data API is used for discovery/reference/license metadata only; `videos.list` is not a media-download endpoint.
- An uploader-declared Creative Commons license is evidence about declared metadata, not proof of full chain-of-title and not permission for an arbitrary acquisition method.
- A project geometry/audio/clean-footage PASS is a technical gate only. Never describe it as proof that YouTube acquisition is platform-compliant.
- `vv-cat-youtube` may be used for discovery/research and technical screening, but long-run production media should come from Pexels/Pixabay, creator-supplied/directly authorized files, owned footage, or another independently authorized downloadable source.
- Do not describe yt-dlp technical ability as official YouTube/API permission.
- If an independently authorized file originated from a YouTube reference, preserve attribution/rights evidence and run the same clean-footage/geometry/audio gates on that file.
- Reddit/community posts are references only; a public post is not reuse permission.

## 7. Long-run schedule

Long-run starts at **slot 16** and is deterministic rather than driven by one fragile mutable counter.

Current config:

- pipeline cycle: `animal_compilation`, `ai_short` (alternating cats/facts);
- AI language: EN;
- long-run cat language cycle starts fresh after the pilot: `en, en, en, en, ru`;
- first long-run cat is slot 16 / cat episode `#008` / EN;
- fifth long-run cat is slot 24 / cat episode `#012` / RU;
- AI fact subject cooldown = most recent 6 distinct AI visual anchors;
- cat source cooldown = previous 5 rendered cat episodes;
- long-run cat descriptions use deterministic safe variation instead of one byte-identical description forever.

Commands:

```powershell
.\.venv\Scripts\vv.exe longrun-next --dry-run
.\.venv\Scripts\vv.exe longrun-next
.\.venv\Scripts\vv.exe longrun-batch --count 3
```

Existing non-empty long-run MP4 files are resume markers just like the pilot. Attempt state is written to `runtime/long_run/state.json`.

## 8. Windows scheduled generation

User approved a **one-week test at up to 3 generated videos per night**.

Chosen Moscow-time triggers:

```text
01:30 MSK
03:30 MSK
05:30 MSK
```

Implementation:

- `scripts/run-longrun-task.ps1` runs exactly one review-only `longrun-next` per invocation.
- It runs `vv status` first, logs to `runtime/scheduler/longrun-task.log`, and uses an exclusive lock to prevent overlapping renders.
- It never runs `git pull`, never auto-updates code, and never publishes.
- A failed generation exits nonzero; the next scheduled trigger resumes the same missing slot through existing long-run resume semantics.
- `scripts/install-longrun-task.ps1` now supports one Windows Scheduled Task with multiple daily triggers.
- Default installer schedule is `01:30,03:30,05:30`; `-At "HH:mm"` remains valid for a single custom trigger, and comma/semicolon-separated times are supported.
- Task is `StartWhenAvailable`, `IgnoreNew`, battery-safe, with a four-hour execution limit.
- Because `IgnoreNew` is enabled, three triggers mean **up to** three videos/day; a still-running earlier render prevents overlap rather than spawning a second renderer.
- Current cost estimate from observed pilot/long-run usage for 21 generated videos/week is roughly **$0.25–0.50 OpenAI**, with the hard `$10` guard unchanged.
- Scheduler installation is explicit and local; no password is requested/stored.

## 9. Architecture constraints

- `VV_knopka` is orchestration/business logic.
- Do not vendor/fork all MoneyPrinterTurbo into Git history.
- Local ignored `MoneyPrinterTurbo/` checkout is allowed.
- Use MPT only for `ai_short` where practical.
- Edge TTS remains default AI-short TTS; cat compilation has no voiceover.
- Keep secrets out of Git. `.env` must never be committed.
- Real meow binary stays local/ignored or via `CAT_MEOW_FILE`.

## 10. Git workflow

Development branch: `mvp/pilot-scaffold`.
Draft review vehicle: PR #1 into `main`.

- Continue on the existing branch/PR unless there is a concrete reason to split.
- Keep `docs/PROJECT_HANDOFF_RU.md` and `docs/PROGRESS_RU.md` current.
- GitHub wins over docs on mechanical facts such as SHA/CI/file list.
- PR #1 remains draft/open/unmerged until an explicit user decision.

## 11. Current milestone

The pilot/conveyor format has been visually accepted and **the first real post-pilot long-run slot has succeeded locally**.

Confirmed on the user's machine:

```text
slot-16-en-animals.mp4
slot-16-en-animals.upload.json
Long-run conveyor outputs: slot-16-en-animals.mp4
```

The successful retry validated the cooled local-history fallback. The scheduler runner dry-run then correctly resolved **slot 17 / ai_short / EN** and showed:

```text
OpenAI spent: $0.1885 / $10.00
auto_publish: False
publication gate: PASS
long_run: True
```

The multi-trigger scheduler installer is now on the branch. Immediate continuation:

1. pull the latest scheduler installer;
2. optionally run `scripts/install-longrun-task.ps1 -DryRun` and expect the three default triggers;
3. register the task with `scripts/install-longrun-task.ps1` (no `-At` needed for the approved 01:30/03:30/05:30 schedule);
4. verify task state/next run and inspect `runtime/scheduler/longrun-task.log` after the first night;
5. publishing remains manual/review-first.

## 12. Language / title policy

- Never publish translated duplicates of the same cat episode.
- Long-run cat cadence: `en, en, en, en, ru`.
- Do not use `Daily Dose of Cats` or a close imitation.
- On-card cats remain `#NNN — Котики` / `#NNN — Cats`.
- Upload-facing title family remains `Котики, которые сделали мой день 😹 #NNN #shorts` / `Cats That Made My Day 😹 #NNN #shorts`.
- AI fact titles come from each specific plan; do not use one repeated generic template.

## 13. Context persistence

At the end of every substantial work session, update handoff/progress so a fresh chat can resume from GitHub without relying on conversational memory.
