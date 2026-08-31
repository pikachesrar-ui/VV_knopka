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

- `ai_short`: original animal/nature fact/story Short through MoneyPrinterTurbo;
- `animal_compilation`: cat compilation assembled locally with FFmpeg.

Current product goal is an unattended long-run system that can generate, validate, publish and observe YouTube Shorts. TikTok is planned later and is explicitly out of the current work block.

## 3. Frozen pilot — immutable history

- 15 Shorts total: 8 AI + 7 cat compilations.
- Slot 1 RU AI + slot 2 RU cats; slots 3–15 EN.
- All 15 ready outputs were generated and visually accepted by the user.
- Final explicitly shown pilot ledger: **$0.1786 / $10.00**.
- Do not rebuild the frozen pilot solely for later metadata refinements.
- Frozen pilot config/metadata stays review-first (`pilot.auto_publish=false`).
- YouTube metadata v2 is long-run-only so pilot sidecars remain historically stable.

## 4. Current real local checkpoint (2026-08-31)

Confirmed by the user on the real Windows machine:

- ready local Shorts: **16**;
- successful YouTube receipts: **10** (slots 1–10);
- every checked receipt had `requested_privacy=public` and `actual_privacy=public`;
- pending ready uploads: **6** (slots 11–16);
- next generation target remains slot **17 AI EN**, but generation is backlog-first and must wait until pending publication drains;
- Windows scheduled task `VV Knopka Long Run` is installed and `Ready`;
- triggers: **01:30, 03:30, 05:30 MSK**;
- Windows timezone confirmed `Russian Standard Time (UTC+03:00)`.

PowerShell windows do not need to remain open for Task Scheduler. The PC must remain on and the Windows user logged in; sleep/hibernation should not interrupt scheduled runs.

## 5. Current authorization / safety state

User explicitly authorized:

- automatically publish future generated Shorts to YouTube;
- upload the already generated ready backlog;
- add YouTube metadata/discovery improvements;
- add an automatic fact-check gate for long-run AI facts;
- prepare an AI-generated background-music library and rotation infrastructure.

Current `[youtube]` policy is intentionally:

```toml
enabled = true
auto_publish = true
privacy_status = "public"
```

Do **not** silently revert this to review-only unless the user asks.

Still mandatory:

- project-side OpenAI hard cap = **$10 USD**;
- no new paid provider or increased paid cap without explicit user approval;
- source/provenance/audio/geometry/vision gates stay fail-closed;
- OAuth secrets/tokens stay local under ignored `runtime/youtube/`;
- uploader must channel-bind and fail closed if OAuth resolves to a different channel;
- successful uploads must leave idempotent `.youtube.json` receipts;
- draft PR #1 must stay open/draft/unmerged until an explicit user decision.

## 6. Long-run schedule

Long-run starts at slot 16 and is deterministic:

- pipeline cycle: cats, AI, cats, AI...;
- AI language EN;
- long-run cat language cycle: `en,en,en,en,ru`;
- cat episode numbering continues after pilot (#008 at slot 16);
- AI subject cooldown = 6 recent distinct anchors;
- cat source cooldown = 5 recent cat episodes.

Scheduler is **backlog-first** with one publication opportunity per trigger:

1. lock + status;
2. verify existing YouTube receipts when credentials exist;
3. best-effort collect YouTube statistics;
4. if pending uploads exist, upload exactly one oldest pending and stop without generation;
5. only when pending is zero, generate one next long-run slot;
6. upload only that newly rendered slot;
7. a deferred/failed publication prevents further generation from expanding backlog.

This caps normal scheduled upload pressure at **3 uploads/day** for the approved triggers.

## 7. YouTube uploader and observability

Entry point:

```powershell
.\.venv\Scripts\vv-youtube.exe status
.\.venv\Scripts\vv-youtube.exe auth
.\.venv\Scripts\vv-youtube.exe pending-count
.\.venv\Scripts\vv-youtube.exe verify
.\.venv\Scripts\vv-youtube.exe stats
.\.venv\Scripts\vv-youtube.exe upload-ready --dry-run
.\.venv\Scripts\vv-youtube.exe upload-ready --limit 1
```

Implementation guarantees:

- OAuth scopes: `youtube.upload` + `youtube.readonly`;
- Desktop OAuth JSON: `runtime/youtube/client_secret.json`;
- token: `runtime/youtube/token.json`;
- channel binding: `runtime/youtube/channel.json`;
- upload-limit state: `runtime/youtube/upload-limit.json`;
- queue defaults oldest slot first; scheduler uses one item only;
- requested vs actual privacy stored separately;
- `uploadLimitExceeded` is converted to clean `DEFERRED` / exit code `75`;
- a conservative 24h cooldown prevents repeated endpoint hammering;
- receipts are idempotency source of truth.

`vv-youtube verify` checks receipt videos via YouTube API and records publication states around upload/processing/privacy/failure/rejection. Failed/missing videos are fail-closed for the scheduler.

`vv-youtube stats` records current views/likes/comments snapshots for uploaded receipt videos. Statistics are observational and must not block publication if collection itself fails.

## 8. YouTube metadata v2 — long-run only

Future long-run metadata now includes:

- 3–5 relevant hashtags in description;
- deterministic CTA rotation for cat videos;
- AI planner hashtags reused instead of discarded;
- `snippet.tags` keyword tags (normalized/capped);
- explicit metadata version 2;
- long-run publication fields aligned with real policy: when YouTube auto-publish is enabled, `auto_publish=true`, `review_required=false`, `publication_allowed_by_conveyor=true`;
- frozen pilot keeps historical review-first fields.

YouTube `containsSyntheticMedia` is sent only when metadata says disclosure is warranted, including applied AI-generated music or a planner recommendation. Do not blanket-mark every use of AI assistance.

## 9. AI fact-check gate

Long-run `ai_short` planning is now fail-closed before rendering.

Flow:

```text
OpenAI plan candidate
  -> bounded evidence web search
  -> fact-check audit
  -> PASS: promote to plan.json
  -> FAIL: do not render/publish
```

Config:

```toml
fact_check_enabled = true
fact_check_model = "gpt-5.6-luna"
fact_check_max_tool_calls = 1
fact_check_max_estimated_cost_usd = 0.05
web_search_call_usd = 0.01
```

The fact checker requires supported claim verdicts plus actual returned evidence sources. Its model token cost and fixed web-search call cost are both written to the same `$10` project ledger.

Do not loosen this gate just to make generation succeed.

## 10. MoneyPrinterTurbo lifecycle

`VV_knopka` does not vendor MoneyPrinterTurbo.

Long-run conveyor already has an `MPTProcessManager` capable of starting local MoneyPrinterTurbo when an AI slot needs it, waiting for health readiness, logging under runtime, and shutting down the process it started. Manual `render-ai` also uses the automatic availability helper.

Therefore an already-open MoneyPrinterTurbo PowerShell window is no longer a product requirement for future long-run AI generation, assuming the local MPT checkout/environment exists and starts successfully.

## 11. Background music plan/infrastructure

User approved adding quiet pleasant AI-generated background music and rotating a small curated library.

Current state:

- music infrastructure implemented;
- target generator = **ACE-Step** locally;
- library directory = `runtime/assets/music` (ignored/local assets);
- selector supports pipeline-oriented names such as `curious_*`, `calm_*`, `cute_*`, `playful_*`;
- deterministic rotation with recent-track cooldown;
- per-slot `music.json` audit includes track name/hash/generator/disclosure data;
- FFmpeg mixer preserves primary voice/source audio and supports ducking;
- when our local library is enabled, MPT background music is muted to avoid double-BGM;
- **`music.enabled=false` remains mandatory until initial tracks are locally generated and listened to/approved by the user**.

Initial planned library: about 8–12 instrumental tracks. User help is expected only for the local ACE-Step generation/listening checkpoint.

## 12. Cat production rules

- Local FFmpeg renderer; no MPT for cats.
- Generic cats; no voiceover.
- Real source audio stays primary.
- Real meow on black cards; no bass/drop/impact/boom SFX.
- Frozen pilot and current approved outputs stay unchanged.
- Future long-run may receive very quiet approved background music only after `music.enabled` is explicitly turned on.
- Source footage must carry provenance/commercial-use evidence, audible audio and near-9:16 geometry.
- Aspect tolerance = `0.08`; fewer than 5 unique usable clips = fail closed.
- Pexels/Pixabay are normal automated downloadable stock paths.
- Frozen pilot reuse protection = all-history.
- Long-run source cooldown = previous 5 rendered cat episodes.
- Fresh never-used stock first; cooled historical sources fallback only.

## 13. YouTube / UGC compliance wording

- YouTube Data API discovery metadata is not a media-download permission mechanism.
- Uploader-declared CC metadata does not prove chain-of-title or authorize arbitrary acquisition.
- yt-dlp capability != official YouTube/API permission.
- Production media should be Pexels/Pixabay, owned/creator-supplied/directly authorized, or another independently authorized downloadable source.
- `videos.insert` is used only to upload our finished local MP4s to the user's authorized channel.
- `uploadLimitExceeded` means YouTube channel daily upload limit, not Google Cloud quota; exact numeric limit must not be invented/hardcoded.

## 14. Git / CI workflow

Development branch: `mvp/pilot-scaffold`.
Draft PR #1 into `main` stays open/draft/unmerged until explicit user decision.

Last fully green YouTube-v2 checkpoint before documentation refresh:

```text
head: cdf9e2adbc709a93269ef7b2a560f890544a9075
workflow: 33416185965
pytest: 138 passed
Ubuntu: success
Windows bootstrap/scheduler dry-run: success
```

Later documentation/semantic commits move HEAD and must be rechecked before declaring the new HEAD green.

## 15. Immediate continuation

1. Keep the existing real scheduler enabled and let slots 11–16 drain after YouTube permits uploads again.
2. Pull/reinstall latest branch locally before relying on new metadata/fact-check/observability behavior.
3. Confirm `vv-youtube verify` and `vv-youtube stats` against the real 10 receipts.
4. Confirm slot 17 goes through fact-check + automatic MPT lifecycle end-to-end only after backlog reaches zero.
5. Generate initial ACE-Step music library locally, listen/approve tracks, then enable music and perform a small music-vs-no-music comparison.
6. TikTok remains a later separate work block.

## 16. Context persistence

At the end of every substantial session update `AGENT.md`, `docs/PROJECT_HANDOFF_RU.md`, and `docs/PROGRESS_RU.md` so a fresh chat can resume from GitHub without relying on conversational memory.
