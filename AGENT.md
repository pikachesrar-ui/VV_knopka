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

## Real YouTube checkpoint — 2026-09-01
Confirmed locally:
- ready Shorts: 16;
- slots 1–11 published and VERIFIED_PUBLIC;
- slots 1–11 have discovery hidden tags + hashtags after real `backfill-metadata --apply`;
- final verification dry-run for slots 1–11 returned UNCHANGED for every slot;
- slots 12–15 were still unpublished when upgraded locally and now have metadata-v2 sidecars with hidden tags + hashtags;
- real `backfill-metadata --slots 12-15 --apply` immediately after the local upgrade found no receipts, confirming none of 12–15 had been uploaded yet;
- active pending queue was therefore slots 12–16 at that checkpoint;
- next generation target after pending=0 is slot 17 AI EN;
- OpenAI ledger last shown: `$0.1885/$10`;
- scheduler `VV Knopka Long Run` installed, Ready, triggers 01:30/03:30/05:30 MSK.

The first bad unuploaded slot 16 was archived to:
`runtime/backups/slot-16-before-rebuild-20260831-231504`.
The corrected replacement slot 16 is active and passed source/music/metadata audits.

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

## Pending pilot metadata upgrade — slots 12–15 REAL COMPLETE
Slots 12–15 were rendered before long-run metadata v2. User explicitly asked to upgrade them before leaving the conveyor unattended.

Implemented and real-run command:
```powershell
vv-youtube upgrade-pending-metadata --slots 12-15
vv-youtube upgrade-pending-metadata --slots 12-15 --apply
```

Real dry-run proposed:
- slot 12 cats tags/hashtags;
- slot 13 dog discovery tags/hashtags;
- slot 14 cats tags/hashtags;
- slot 15 elephant discovery tags/hashtags.

Real apply result:
```text
4 pending sidecars
changed=4
applied=4
```

Immediately after apply, `backfill-metadata --slots 12-15 --apply` returned `No uploaded receipt videos matched the requested slots`, so these four remained pending and will be uploaded for the first time with the upgraded metadata.

Behavior:
- default is dry-run;
- only ready sidecars without a `.youtube.json` receipt are eligible;
- adds/merges `youtube_tags`;
- appends only missing hashtags to `youtube_description`;
- records `youtube_hashtags` and `metadata_version=2`;
- preserves title, review/publication flags and every unrelated sidecar field;
- never changes MP4 bytes;
- creates one-time original backups under `runtime/youtube/pending-metadata-backups/`;
- skips already-published slots automatically;
- writes audit `runtime/youtube/pending-metadata-upgrade-latest.json`.

## Published metadata backfill — REAL VALIDATED
User authorized and ran:
```powershell
vv-youtube auth-metadata
vv-youtube backfill-metadata --slots 1-11 --apply
```

Real result:
- 11/11 initially updated;
- slots 1–6 and 8–11 immediately became idempotent;
- slot 7 briefly showed a YouTube read-after-write consistency delay, then also returned UNCHANGED;
- final dry-run: all slots 1–11 UNCHANGED.

Backfill preserves remote title/category/language/existing tags, only appends missing hashtags/tags, and never touches privacy/status/video URL/views/video bytes.

## Cat source reuse policy
The original slot 16 / cat #008 had 5/6 cooled clips reused from cat #001. Fixed policy:
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

Do not optimize content strategy from the first tiny statistics sample.

## AI fact-check
Long-run AI planning is fail-closed before render:
`candidate -> bounded web-search evidence check -> PASS/FAIL`.
FAIL means no render/no publish. Costs remain inside the project-side `$10` ledger.

## Safety
- OpenAI hard cap `$10`;
- no new paid providers without explicit approval;
- secrets/tokens stay ignored/local;
- provenance/commercial-use/audio/geometry/vision gates remain fail-closed;
- Draft PR #1 stays open/draft/unmerged.

## Immediate continuation
1. metadata cleanup is complete for published 1–11 and pending 12–15;
2. leave scheduler alone for a few days under normal healthy operation;
3. it should drain slots 12–16 oldest-first;
4. once pending reaches zero it should generate slot 17 AI EN automatically, using MPT lifecycle/fact-check/music/metadata v2;
5. continue alternating long-run slots until a safety/failure gate or the `$10` generation budget stops new generation;
6. later optimize cat audio-first discovery cost if desired.

After substantive work update this file plus `docs/PROJECT_HANDOFF_RU.md` and `docs/PROGRESS_RU.md`.
