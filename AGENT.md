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
- user explicitly approved metadata-only discovery upgrades (tags/hashtags) for already-rendered pilot videos.

## Real YouTube checkpoint — 2026-09-02
Confirmed locally:
- slots 1–11 published and `VERIFIED_PUBLIC`;
- slots 1–11 discovery metadata backfill is complete and final dry-run was UNCHANGED;
- slots 12–15 were upgraded locally to metadata v2 before first upload;
- corrected replacement slot 16 passed source/music/metadata audits;
- pending ready uploads now: exactly 5 => slots 12–16;
- slot 17 has NOT been generated, which is correct under backlog-first behavior;
- next generation target after pending=0 is slot 17 AI EN;
- OpenAI ledger last shown: `$0.2024/$10`;
- scheduler `VV Knopka Long Run` is installed with triggers 01:30/03:30/05:30 MSK.

The first bad unuploaded slot 16 remains archived at:
`runtime/backups/slot-16-before-rebuild-20260831-231504`.

## Scheduler incident — 2026-09-02
Real unattended behavior:
- 2026-08-31 01:30 slot 11 uploaded successfully;
- 2026-08-31 03:30 slot 12 hit YouTube `uploadLimitExceeded`; persisted cooldown worked as intended;
- after cooldown expiry, triggers on 2026-09-01 and 2026-09-02 successfully verified slots 1–11, then died immediately after verify with only `ERROR: Traceback (most recent call last):` in scheduler log;
- because the failure happened before pending upload handling, slots 12–16 remained untouched and slot 17 was not generated.

Manual `vv-youtube stats` on 2026-09-02 succeeded and wrote a fresh statistics snapshot containing Cyrillic/emoji titles (including `😹`). This isolated the problem to Windows Task Scheduler/native output encoding and PowerShell stderr handling, not the YouTube stats API.

Fix now present in branch:
- scheduled Python output forced to UTF-8 via `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1`;
- PowerShell output encoding set to UTF-8 where supported;
- native stderr is captured with temporary `ErrorActionPreference=Continue`, then real process exit codes drive decisions;
- `stats` is truly best-effort: stats/output failure logs WARN and does not block healthy backlog publication;
- verify/pending/upload/generation safety gates remain fail-closed.

Regression test: `tests/test_scheduler_runner.py`.

IMPORTANT: the installed Windows scheduler intentionally performs **no git pull**. A local checkout must pull latest `mvp/pilot-scaffold` before the scheduler uses this fix. Reinstalling the task is not required because the task points to the same `scripts/run-longrun-task.ps1` path.

## Scheduler / autonomy
Backlog-first scheduler:
1. `vv status`;
2. YouTube status + receipt verification;
3. best-effort statistics;
4. pending > 0 => upload exactly one oldest and stop;
5. pending == 0 => generate exactly one `longrun-next` slot;
6. upload only the newest generated video;
7. deferred/failure prevents backlog growth.

Do not generate slot 17 manually while upload backlog remains.

For AI slots the conveyor can auto-start MoneyPrinterTurbo, wait for readiness, render, and stop only the MPT process it launched. Cat slots do not need MPT.

The OpenAI project-side hard cap is `$10`. New generation stops fail-closed when the ledger reaches the cap. Existing ready backlog can still be uploaded because backlog handling runs before new generation.

## First real stats sample — telemetry only
Manual snapshot on 2026-09-02:
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

## Pending pilot metadata upgrade — slots 12–15 REAL COMPLETE
User ran:
```powershell
vv-youtube upgrade-pending-metadata --slots 12-15
vv-youtube upgrade-pending-metadata --slots 12-15 --apply
```

Real apply result:
```text
4 pending sidecars
changed=4
applied=4
```

Behavior:
- default is dry-run;
- only ready sidecars without a `.youtube.json` receipt are eligible;
- adds/merges `youtube_tags`;
- appends only missing hashtags to `youtube_description`;
- records `youtube_hashtags` and `metadata_version=2`;
- preserves title, review/publication flags and unrelated sidecar fields;
- never changes MP4 bytes;
- creates one-time original backups under `runtime/youtube/pending-metadata-backups/`;
- skips already-published slots automatically.

## Published metadata backfill — REAL VALIDATED
User authorized and ran:
```powershell
vv-youtube auth-metadata
vv-youtube backfill-metadata --slots 1-11 --apply
```

Final result: all slots 1–11 UNCHANGED on dry-run; hidden tags/hashtags are already present remotely.

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

Rules:
- remote audio stream / audibility prefilter before Luna when measurable;
- confirmed-silent files rejected before paid vision;
- small bounded unknown CDN tail only;
- remote cooled history excluded from discovery;
- old clips only through explicit bounded local fallback;
- retry cannot stack extra cooled fallback;
- fail closed if minimum quality/source count cannot be reached.

Real replacement slot 16:
```text
Pexels candidates: 54
vision reviewed: 54
vision approved: 51
new Pexels audio accepted: 3
Pixabay candidates: 0
```
`vision_reviewed=54` remains a later efficiency/cost optimization target, not a correctness blocker.

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

Replacement slot 16 real audit:
```text
track: curious_02.wav
applied_to_video: true
music_volume_applied: 0.11
ducking: false
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
- published metadata backfill for legacy videos;
- unpublished sidecar metadata upgrade for pending legacy videos.

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
1. pull latest `mvp/pilot-scaffold` on the Windows machine so the scheduler receives the UTF-8 fix;
2. verify a real task run reaches `youtube-stats`, then `youtube-pending`, then handles oldest pending slot 12;
3. if successful, leave scheduler autonomous again;
4. it should drain slots 12–16 oldest-first;
5. once pending reaches zero it should generate slot 17 AI EN automatically with MPT lifecycle/fact-check/music/metadata v2;
6. do not manually generate slot 17 while pending > 0.

After substantive work update this file plus `docs/PROJECT_HANDOFF_RU.md` and `docs/PROGRESS_RU.md`.
