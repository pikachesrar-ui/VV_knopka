# VV_knopka — Agent Rules

This file is the mandatory entry point for any new ChatGPT/Codex/agent session working on this repository.

## Read order
1. Read this file.
2. Read `docs/PROJECT_HANDOFF_RU.md`.
3. Read `docs/PROGRESS_RU.md`.
4. For music read `docs/AI_MUSIC_RU.md`.
5. For future comment feedback read `docs/YOUTUBE_COMMENT_FEEDBACK_RU.md`.
6. Check branch/HEAD/CI and Draft PR #1.

GitHub is source of truth. Development branch: `mvp/pilot-scaffold`.
Draft PR #1 must remain **open/draft/unmerged** until the user explicitly decides to merge.

## Product
Automated animal/nature Shorts pipeline:
- `ai_short`: original animal/nature fact Short via MoneyPrinterTurbo;
- `animal_compilation`: cat compilation via local FFmpeg.

TikTok is explicitly out of the current block.

## Frozen pilot
- 15 Shorts total, visually accepted.
- slot 1 RU AI, slot 2 RU cats, slots 3–15 EN.
- video bytes for slots 1–15 are immutable: do not rerender them for later metadata/music/source-policy changes.
- metadata-only discovery upgrades were approved for already-rendered pilot videos.

## Real YouTube checkpoint — 2026-09-02
Confirmed locally:
- slots 1–12 published;
- slots 1–11 were `VERIFIED_PUBLIC` immediately before the latest upload;
- slot 12 was uploaded by the repaired scheduler at 2026-09-02 03:35 MSK with requested=`public`, actual=`public`;
- slot 12 URL: `https://www.youtube.com/watch?v=nrGanPLeVps`;
- pending ready uploads now exactly 4 => slots 13–16;
- slot 17 has NOT been generated, which is correct under backlog-first behavior;
- next generation target after pending=0 is slot 17 AI EN;
- OpenAI ledger last shown: `$0.2024/$10`;
- scheduler `VV Knopka Long Run` is installed with triggers 01:30/03:30/05:30 MSK.

## Scheduler incident — 2026-09-02 — CLOSED
History:
- 2026-08-31 01:30 slot 11 uploaded successfully;
- 2026-08-31 03:30 slot 12 hit YouTube `uploadLimitExceeded`; persisted cooldown worked;
- after cooldown expiry, unattended runs verified 1–11 but terminated immediately after verify because Windows PowerShell/native output handling surfaced the Python traceback as a terminating error;
- backlog stayed at slots 12–16 and slot 17 was not generated.

Manual `vv-youtube stats` succeeded and wrote a fresh snapshot containing Cyrillic/emoji titles, isolating the issue to Windows scheduled stdout/stderr handling.

Fix in `scripts/run-longrun-task.ps1`:
- `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1`;
- UTF-8 PowerShell output where supported;
- native stderr captured under temporary `ErrorActionPreference=Continue` and decisions made from real `$LASTEXITCODE`;
- stats remains best-effort;
- verify/pending/upload/generation remain fail-closed.

Regression test: `tests/test_scheduler_runner.py`.

Real post-fix validation:
```text
verify 1–11: VERIFIED_PUBLIC
stats: SUCCESS
pending before: 5
slot 12: UPLOADED public/public
pending after: 4
```
Therefore the fix is operationally validated. A replacement glyph `�` for one emoji in the text log is cosmetic only and did not block stats/upload.

## Scheduler / autonomy
Backlog-first scheduler:
1. `vv status`;
2. YouTube status + receipt verification;
3. best-effort statistics;
4. pending > 0 => upload exactly one oldest and stop;
5. pending == 0 => generate exactly one `longrun-next` slot;
6. upload only the newest generated video;
7. deferred/failure prevents backlog growth.

Current expected drain:
`slot 13 -> slot 14 -> slot 15 -> slot 16 -> pending=0 -> auto-generate slot 17 AI EN`.

Do not generate slot 17 manually while upload backlog remains.

For AI slots the conveyor can auto-start MoneyPrinterTurbo, wait for readiness, render, and stop only the MPT process it launched. Cat slots do not need MPT.

The OpenAI project-side hard cap is `$10`. New generation stops fail-closed when the ledger reaches the cap. Existing ready backlog can still be uploaded because backlog handling runs before new generation.

## First real stats sample — telemetry only
Snapshot before slot 12 upload:
```text
slot 1: 0 views
slot 2: 6
slot 3: 2
slot 4: 1
slot 5: 18
slot 6: 2
slot 7: 1
slot 8: 1
slot 9: 1
slot 10: 3
slot 11: 8
```
Do not optimize content strategy from this tiny/young sample.

## Metadata checkpoint
Published slots 1–11 have discovery hidden tags + hashtags remotely; final backfill dry-run was UNCHANGED.
Legacy slots 12–15 were upgraded locally to metadata v2 before first upload. Slot 12 has now been successfully published from its upgraded sidecar; slots 13–15 remain pending. Slot 16 was generated under metadata v2.

## Cat source reuse policy
Current policy:
```toml
cat_source_cooldown_episodes = 5
cat_cooled_reuse_max_sources = 2
cat_cooled_reuse_max_per_history_episode = 1
```

Replacement slot 16 real composition:
- 6 unique clips;
- 4 fresh Pexels;
- 2 cooled total;
- one from slot 2 and one from slot 4;
- zero overlap with protected recent-5 cat episodes;
- `source_reuse_audit.json`: PASS.

## Cat source v6 — audibility before vision
Current CLI routes cat sourcing through `animal_audio_sources_v6`.
Rules remain audio-first, bounded reuse, fail-closed on insufficient quality/source count.

## AI music — production approved
All 8 ACE-Step tracks were generated, listened to and approved.
Current production profile:
```toml
[music]
enabled = true
ai_volume = 0.10
cat_volume = 0.11
ai_ducking = true
cat_ducking = false
```
Long-run metadata sets `contains_synthetic_media=true` when AI music or the planner warrants disclosure.

## YouTube v2 / observability
Implemented and real-channel validated:
- metadata v2, hashtags, CTA, hidden tags;
- conditional synthetic-media flag;
- graceful upload-limit cooldown;
- `vv-youtube verify`;
- `vv-youtube stats` + history;
- `vv-youtube report` age-aware metrics;
- published metadata backfill;
- unpublished sidecar metadata upgrade.

## AI fact-check
Long-run AI planning is fail-closed before render:
`candidate -> bounded web-search evidence check -> PASS/FAIL`.
FAIL means no render/no publish. Costs remain inside the project-side `$10` ledger.

## Safety
- OpenAI hard cap `$10`;
- no new paid providers without explicit approval;
- secrets/tokens stay ignored/local;
- provenance/commercial-use/audio/geometry/vision/fact-check gates remain fail-closed;
- Draft PR #1 stays open/draft/unmerged;
- TikTok remains out of scope.

## Immediate continuation
1. do not manually upload or generate while the repaired scheduler is healthy;
2. allow scheduler to drain slots 13–16 oldest-first;
3. when pending reaches zero it should auto-generate slot 17 AI EN and upload it;
4. after several triggers inspect receipts, scheduler log, OpenAI ledger and stats;
5. do not merge Draft PR #1 without explicit user instruction.

After substantive work update this file plus `docs/PROJECT_HANDOFF_RU.md` and `docs/PROGRESS_RU.md`.
