# VV_knopka — Agent Rules

This file is the mandatory entry point for any new ChatGPT/Codex/agent session working on this repository.

## 1. Read order before doing work

Before changing code or giving project-status claims:

1. Read this file completely.
2. Read `docs/PROJECT_HANDOFF_RU.md` completely.
3. Read `docs/PROGRESS_RU.md` completely for the newest operational checkpoint.
4. Check the current repository state, active branch, and draft PR #1.
5. Treat GitHub as source of truth for code/history; handoff as product intent; `PROGRESS_RU.md` as live checkpoint.

## 2. Project goal

Build an automated short-form video pipeline under **Animals / Nature Curiosities** with two formats:

- `ai_short`: original animal/nature fact/story Short through MoneyPrinterTurbo.
- `animal_compilation`: cat compilation assembled locally with FFmpeg.

The immutable 15-video review-first pilot is complete and visually accepted. Current phase is deterministic unbounded generation **plus user-authorized YouTube publishing**.

## 3. Frozen pilot — immutable history

- 15 Shorts total: 8 AI + 7 cat compilations.
- Slot 1 RU AI + slot 2 RU cats; slots 3–15 EN.
- All 15 ready outputs were generated and visually accepted by the user.
- Final explicitly shown pilot ledger: **$0.1786 / $10.00**.
- Do not rebuild the frozen pilot solely for later metadata refinements.
- Frozen pilot config keeps `pilot.auto_publish=false` as historical behavior.

## 4. Current safety / authorization state

User explicitly requested:

- automatically publish future generated Shorts to YouTube;
- upload the already generated ready backlog as well.

Therefore current `[youtube]` policy is intentionally:

```toml
enabled = true
auto_publish = true
privacy_status = "public"
```

Do **not** silently revert this to review-only unless the user asks.

Still mandatory:

- project-side OpenAI hard cap = **$10 USD**;
- do not add paid providers or raise paid usage without explicit approval;
- source/provenance/audio/geometry/vision gates stay fail-closed;
- OAuth secrets/tokens stay local under ignored `runtime/youtube/`;
- uploader must channel-bind and fail closed if OAuth resolves to a different channel;
- successful uploads must leave idempotent `.youtube.json` receipts to prevent duplicates;
- do not merge PR #1 merely because tests pass.

## 5. Cat production rules

- Local FFmpeg renderer; no MPT for cats.
- Generic cats; no voiceover/BGM.
- Real meow on black cards; no bass/drop/impact/boom SFX.
- Source footage: commercial-use/provenance evidence, audible, vertical close to 9:16.
- Aspect tolerance = `0.08`; fewer than 5 unique usable clips = fail closed.
- Pexels/Pixabay are normal automated downloadable stock paths.
- Frozen pilot reuse protection = all-history.
- Long-run source cooldown = previous 5 rendered cat episodes.
- Fresh never-used stock first; cooled historical sources fallback only.
- If remote minimum fails, local cooled Pexels/Pixabay history may seed fallback and is revalidated by current geometry/audio checks.

## 6. YouTube / UGC compliance wording

- YouTube Data API discovery metadata is not a media-download permission mechanism.
- Uploader-declared CC metadata does not prove chain-of-title or authorize arbitrary acquisition.
- yt-dlp capability != official YouTube/API permission.
- Production media should be Pexels/Pixabay, owned/creator-supplied/directly authorized, or another independently authorized downloadable source.
- `videos.insert` is used only to upload our finished local MP4s to the user's authorized channel.
- API projects subject to YouTube audit restriction may have uploads forced to `private`; record requested vs actual privacy separately.
- `uploadLimitExceeded` means the **YouTube channel daily upload limit**, not Google Cloud API quota. YouTube documents this limit as shared across desktop/mobile/API and recommends retrying after 24 hours.
- Advanced YouTube feature eligibility generally provides a higher daily upload limit; do not invent a fixed numeric limit because YouTube varies it by account/channel eligibility and history.

## 7. Long-run schedule

Long-run starts at slot 16 and is deterministic:

- pipeline cycle: cats, AI, cats, AI...
- AI language EN;
- long-run cat language cycle: `en,en,en,en,ru`;
- cat episode numbering continues after pilot (#008 at slot16);
- AI fact subject cooldown = 6 recent distinct anchors;
- cat source cooldown = 5 recent cat episodes.

Slot 16 EN cats / #008 succeeded locally. Next generation target remains slot 17 AI EN until scheduler/backlog policy permits new generation.

## 8. YouTube uploader

Entry point:

```powershell
.\.venv\Scripts\vv-youtube.exe status
.\.venv\Scripts\vv-youtube.exe auth
.\.venv\Scripts\vv-youtube.exe pending-count
.\.venv\Scripts\vv-youtube.exe upload-ready --dry-run
.\.venv\Scripts\vv-youtube.exe upload-ready
```

Implementation:

- OAuth scopes: `youtube.upload` + `youtube.readonly`.
- Desktop-app OAuth JSON: `runtime/youtube/client_secret.json`.
- Token: `runtime/youtube/token.json`.
- Bound channel: `runtime/youtube/channel.json`.
- each successful ready upload writes `<metadata>.youtube.json` receipt;
- queue defaults oldest slot first; `--newest --limit 1` is scheduler post-render path;
- requested vs actual privacy stored separately;
- `uploadLimitExceeded` is converted to a clean `DEFERRED` result/exit code 75 instead of traceback;
- daily-limit observation is persisted to ignored `runtime/youtube/upload-limit.json` with conservative 24-hour `retry_not_before`;
- while cooldown is active uploader does not keep hammering the upload endpoint.

Full setup/operations guide: `docs/YOUTUBE_PUBLISHING_RU.md`.

## 9. Windows scheduled generation + publication

Approved one-week schedule, Moscow time:

```text
01:30
03:30
05:30
```

To respect YouTube daily limits and drain the existing backlog, each trigger now has at most **one upload opportunity**:

1. lock + status checks;
2. count pending ready uploads;
3. if any pending/backlog exists, upload exactly one oldest pending and end the trigger **without generating**;
4. only when pending count is zero, generate one next long-run slot and upload that new video;
5. if YouTube returns daily limit or another upload failure, do not generate another slot until pending publication recovers.

This caps scheduler upload pressure at 3/day for the approved triggers and makes the backlog shrink instead of accumulating new local videos while old ones wait.

Default installer:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1
```

No `git pull`/auto-update runs inside the scheduled task.

## 10. Architecture constraints

- `VV_knopka` = orchestration/business logic.
- Do not vendor MoneyPrinterTurbo.
- Edge TTS remains default AI-short TTS.
- Keep secrets out of Git; `.env` and `runtime/` are ignored.
- Real meow stays local/ignored or via `CAT_MEOW_FILE`.

## 11. Git workflow

Development branch: `mvp/pilot-scaffold`.
Draft PR #1 into `main` stays open/draft/unmerged until explicit user decision.

Keep `AGENT.md`, `PROJECT_HANDOFF_RU.md`, and `PROGRESS_RU.md` current after substantive work.

## 12. Current milestone / immediate continuation

Real OAuth succeeded on the user's machine. The first real backlog upload attempt then hit YouTube's channel-level `uploadLimitExceeded` restriction. Any successful uploads before the error should already have receipts and must not be duplicated.

Immediate local workflow:

1. inspect `.youtube.json` receipts / YouTube Studio to see how many uploads succeeded and whether actual privacy is public;
2. check YouTube Studio → Settings → Channel → Feature eligibility; Advanced features can provide higher daily upload limits;
3. pull the upload-limit handling fix and reinstall editable package;
4. do not repeatedly hammer `upload-ready` while the platform limit is active; YouTube says retry after 24 hours unless feature eligibility has legitimately increased the available limit;
5. once backlog can resume, receipts make reruns idempotent;
6. scheduler drains one backlog item per trigger before any new generation.

## 13. Language / title policy

- Never publish translated duplicates of the same cat episode.
- Cat cadence `en,en,en,en,ru`.
- Do not imitate `Daily Dose of Cats`.
- Cats titles remain `Котики, которые сделали мой день 😹 #NNN #shorts` / `Cats That Made My Day 😹 #NNN #shorts`.
- AI titles remain plan-specific.

## 14. Context persistence

At the end of every substantial session update handoff/progress so a fresh chat can resume from GitHub without relying on conversational memory.
