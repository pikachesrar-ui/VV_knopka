# VV_knopka — Agent Rules

This file is the mandatory entry point for any new ChatGPT/Codex/agent session working on this repository.

## 1. Read order before doing work

Before changing code or giving project-status claims:

1. Read this file completely.
2. Read `docs/PROJECT_HANDOFF_RU.md` completely.
3. Read `docs/PROGRESS_RU.md` completely for the newest operational checkpoint.
4. For music work also read `docs/AI_MUSIC_RU.md`.
5. Check the current repository state, active branch, and draft PR #1.
6. Treat GitHub as source of truth for code/history; handoff as product intent; `PROGRESS_RU.md` as live checkpoint.

## 2. Project goal

Build an automated short-form video pipeline under **Animals / Nature Curiosities** with two formats:

- `ai_short`: original animal/nature fact/story Short through MoneyPrinterTurbo;
- `animal_compilation`: cat compilation assembled locally with FFmpeg.

Current phase: unattended long-run generation + user-authorized YouTube publishing + verification/statistics + curated local AI-music preparation. TikTok is planned later and is explicitly out of the current block.

## 3. Frozen pilot — immutable history

- 15 Shorts total: 8 AI + 7 cat compilations.
- Slot 1 RU AI + slot 2 RU cats; slots 3–15 EN.
- All 15 ready outputs were generated and visually accepted by the user.
- Final explicitly shown frozen-pilot ledger: **$0.1786 / $10.00**.
- Do not rebuild the frozen pilot solely for later metadata refinements.
- Frozen pilot config/metadata stays review-first (`pilot.auto_publish=false`).
- Metadata v2 is long-run-only; pilot sidecars remain historical.

## 4. Real local checkpoint — 2026-08-31

Confirmed by the user on the real Windows machine:

- ready local Shorts: **16**;
- successful YouTube receipts: **11**, slots 1–11;
- `vv-youtube verify`: slots **1–11 = VERIFIED_PUBLIC**;
- all 1–11: `upload=processed`, `processing=succeeded`, `privacy=public`;
- pending ready uploads: **5**, slots 12–16;
- next generation target: **slot 17 AI EN**, but backlog-first policy blocks generation until pending reaches zero;
- current local OpenAI ledger: **$0.1885 / $10.00**;
- Scheduled Task `VV Knopka Long Run` is installed and `Ready`;
- triggers: **01:30, 03:30, 05:30 MSK**;
- Windows timezone confirmed `Russian Standard Time (UTC+03:00)`.

PowerShell windows do not need to remain open. The PC must remain on and the Windows user logged in; sleep/hibernation should not interrupt scheduled runs.

### Real scheduler production validation

The scheduler has now been validated against the real channel:

1. it automatically published **slot 11**;
2. slot 11 later verified as `VERIFIED_PUBLIC`;
3. the following upload opportunity hit YouTube `uploadLimitExceeded`;
4. the new uploader persisted cooldown cleanly instead of crashing;
5. local status reported:

```text
pending ready uploads: 5
upload limit cooldown until: 2026-09-01T00:30:07.333703+00:00
```

That retry time is about **03:30 MSK on 2026-09-01**. During an active cooldown the uploader must not hit the upload endpoint.

## 5. Authorization / safety state

The user explicitly authorized:

- automatically publish future generated Shorts to YouTube;
- upload the existing ready backlog;
- YouTube metadata/discovery improvements;
- fail-closed automatic fact checking for long-run AI facts;
- preparation of a small rotating AI-generated background-music library.

Current YouTube policy is intentionally:

```toml
[youtube]
enabled = true
auto_publish = true
privacy_status = "public"
```

Do **not** silently revert this to review-only unless the user asks.

Still mandatory:

- OpenAI project-side hard cap = **$10 USD**;
- do not add paid providers or raise the paid cap without explicit approval;
- source/provenance/audio/geometry/vision gates stay fail-closed;
- OAuth secrets/tokens stay local under ignored `runtime/youtube/`;
- uploader must channel-bind and fail closed if OAuth resolves to a different channel;
- successful uploads must leave idempotent `.youtube.json` receipts;
- draft PR #1 stays open/draft/unmerged until explicit user decision.

## 6. Long-run schedule

Long-run starts at slot 16 and is deterministic:

- pipeline cycle: cats, AI, cats, AI...;
- AI language EN;
- cat language cycle: `en,en,en,en,ru`;
- cat numbering continues after pilot (#008 at slot 16);
- AI subject cooldown = 6 recent distinct anchors;
- cat source cooldown = 5 recent cat episodes.

Each Windows trigger is backlog-first:

1. lock + `vv status`;
2. `vv-youtube status`;
3. verify existing uploaded receipts when credentials exist;
4. best-effort collect YouTube stats;
5. if pending > 0, upload exactly one oldest pending and stop without generation;
6. only when pending == 0, generate one next long-run slot;
7. upload only that newly rendered slot;
8. deferred/failed publication prevents new generation from expanding backlog.

Normal maximum = **3 upload opportunities/day**.

## 7. YouTube upload / daily-limit behavior

Commands:

```powershell
.\.venv\Scripts\vv-youtube.exe status
.\.venv\Scripts\vv-youtube.exe auth
.\.venv\Scripts\vv-youtube.exe pending-count
.\.venv\Scripts\vv-youtube.exe verify
.\.venv\Scripts\vv-youtube.exe stats
.\.venv\Scripts\vv-youtube.exe report
.\.venv\Scripts\vv-youtube.exe upload-ready --dry-run
.\.venv\Scripts\vv-youtube.exe upload-ready --limit 1
```

Guarantees:

- OAuth scopes: `youtube.upload` + `youtube.readonly`;
- OAuth/client/token/channel files live under ignored `runtime/youtube/`;
- requested and actual privacy stored separately;
- receipts are duplicate guards;
- `uploadLimitExceeded` is YouTube channel daily limit, not Google Cloud quota;
- it becomes clean `DEFERRED` / exit code `75`;
- conservative 24h cooldown is persisted locally;
- uploader does not hammer the endpoint during active cooldown.

This graceful-limit behavior has now been validated on the real unattended scheduler, not only in tests.

## 8. YouTube metadata v2 — long-run only

Future long-run metadata includes:

- 3–5 relevant hashtags in description;
- deterministic CTA rotation for cats;
- AI planner hashtags are reused instead of discarded;
- normalized/capped `snippet.tags`;
- `metadata_version=2`;
- long-run publication fields reflect real authorization: when YouTube auto-publish is enabled, `auto_publish=true`, `review_required=false`, `publication_allowed_by_conveyor=true`;
- frozen pilot remains historical review-first.

`vv status` separately reports:

```text
pilot auto_publish (historical): False
youtube auto_publish: True
```

YouTube `containsSyntheticMedia` is sent only when metadata says disclosure is warranted, including actually applied AI-generated music or an explicit planner recommendation. Do not blanket-mark every use of AI assistance.

## 9. YouTube observability / performance learning

`vv-youtube verify` checks receipt videos for:

- upload status;
- processing status;
- privacy;
- failure/rejection;
- missing videos.

Failed/missing publication is fail-closed for unattended scheduling.

`vv-youtube stats` stores current views/likes/comments snapshots plus append-only local history.

`vv-youtube report` builds age-aware metrics:

- views/hour;
- likes per 1000 views;
- comments per 1000 views;
- aggregate `ai_short` vs `animal_compilation`.

First real report had only 11 videos / extremely low counts. Do not optimize policy from that tiny sample. It only proves the measurement path works.

## 10. Long-run AI fact-check gate

Long-run `ai_short` planning is fail-closed before render:

```text
OpenAI plan candidate
 -> bounded evidence web search
 -> structured claim verdict + actual sources
 -> PASS: promote to plan.json
 -> FAIL: no render / no publish
```

Config:

```toml
fact_check_enabled = true
fact_check_model = "gpt-5.6-luna"
fact_check_max_tool_calls = 1
fact_check_max_estimated_cost_usd = 0.05
web_search_call_usd = 0.01
```

Model token cost and fixed web-search-call cost are both written to the same `$10` ledger. Do not loosen the gate merely to make generation succeed.

## 11. MoneyPrinterTurbo lifecycle

`VV_knopka` does not vendor MPT.

`MPTProcessManager` can start local MoneyPrinterTurbo when an AI slot needs it, wait for readiness, log under runtime, and stop only the process it started. Manual `render-ai` also uses automatic availability handling.

Therefore a permanently open MoneyPrinterTurbo PowerShell window is no longer a product requirement, assuming the local MPT checkout/environment exists and starts successfully.

## 12. AI background music

User approved quiet pleasant AI-generated BGM using a small curated rotating library.

Production music remains intentionally OFF:

```toml
[music]
enabled = false
```

Do not enable it until generated candidates are listened to and explicitly approved.

Implemented:

- target generator: **ACE-Step 1.5** locally;
- ignored checkout: `ACE-Step-1.5/`;
- local approved library: `runtime/assets/music/`;
- generated-but-unapproved files: `runtime/assets/music/candidates/`;
- production selector does not scan `candidates/`;
- `vv-music status`, `list`, `generate-library`, `approve`;
- REST client for ACE-Step async API + `/health`;
- automatic ACE-Step API start/wait/stop;
- Windows setup/debug helpers with CI dry-runs;
- stable initial candidates: `cute_01/02`, `playful_01/02`, `curious_01/02`, `calm_01/02`;
- deterministic selection + recent-track cooldown;
- per-slot `music.json` with SHA256/generator/disclosure data;
- quiet pipeline-specific volumes + sidechain ducking;
- when approved local music is enabled, MPT BGM is muted to avoid double music;
- applied AI music can trigger YouTube synthetic-media disclosure.

First local setup/generation:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-acestep-windows.ps1
.\.venv\Scripts\vv-music.exe status
.\.venv\Scripts\vv-music.exe generate-library --count 8 --duration 45
```

Generated WAVs remain candidates. `vv-music approve ...` moves selected tracks to approved library but does **not** turn `music.enabled=true`.

Full guide: `docs/AI_MUSIC_RU.md`.

## 13. Cat production rules

- Local FFmpeg renderer; no MPT for cats.
- Generic cats; no voiceover.
- Real source audio stays primary.
- Real meow on black cards; no bass/drop/impact/boom SFX.
- Future approved BGM must remain very quiet.
- Source footage requires provenance/commercial-use evidence, audible audio, near-9:16 geometry.
- Aspect tolerance = `0.08`; fewer than 5 unique usable clips = fail closed.
- Pexels/Pixabay normal automated sources.
- Frozen pilot reuse protection = all-history.
- Long-run source cooldown = previous 5 rendered cat episodes.
- Fresh never-used stock first; cooled historical source fallback only.

## 14. YouTube / UGC compliance wording

- YouTube Data API discovery metadata is not media-download permission.
- Uploader-declared CC metadata is not chain-of-title proof.
- yt-dlp capability != official permission.
- Production media should be Pexels/Pixabay, owned/creator-supplied/directly authorized, or another independently authorized downloadable source.
- `videos.insert` uploads only our finished local MP4s to the authorized channel.
- Never invent/hardcode a numeric YouTube daily upload limit.

For ACE-Step: repository code is open source, but generated audio still requires normal originality/copyright caution. Do not make blanket legal guarantees about generated tracks.

## 15. Git / CI workflow

Development branch: `mvp/pilot-scaffold`.
Draft PR #1 into `main` stays open/draft/unmerged until explicit user decision.

Latest fully green code checkpoint before this operational-doc update:

```text
head: 936bd0956ad0c08fb236c1a97aada6ff0464e88d
workflow: 33419768393
pytest: 147 passed in 0.90s
Ubuntu: success
Windows bootstrap: success
Windows scheduler dry-run: success
Windows ACE-Step helper dry-run: success
```

## 16. Immediate continuation

Current next steps:

1. let scheduler continue draining slots 12–16 under the proven cooldown/backlog-first policy;
2. locally run ACE-Step setup on the user's RTX 3060;
3. generate 8 candidate WAVs;
4. user listens and approves only good candidates; keep `music.enabled=false` meanwhile;
5. after backlog reaches zero, validate slot 17 end-to-end: plan -> fact-check -> MPT auto-start -> render -> metadata v2 -> YouTube -> verification/stats;
6. once enough channel data exists, use `vv-youtube report` for controlled comparisons, including music ON vs OFF.

TikTok remains a later separate work block.

## 17. Context persistence

After substantial work update `AGENT.md`, `docs/PROJECT_HANDOFF_RU.md`, and `docs/PROGRESS_RU.md` so a fresh chat can resume from GitHub without relying on conversation memory.
