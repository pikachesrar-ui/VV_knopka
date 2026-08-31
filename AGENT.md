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

TikTok is out of the current block.

## Frozen pilot
- 15 Shorts total, visually accepted.
- slot 1 RU AI, slot 2 RU cats, slots 3–15 EN.
- frozen pilot is immutable and remains historical review-first (`pilot.auto_publish=false`).
- do not rebuild slots 1–15 for later metadata/music/source-policy changes.

## Real YouTube checkpoint — 2026-09-01
Confirmed locally:
- ready Shorts: **16**;
- YouTube receipts: **11**;
- slots 1–11 = `VERIFIED_PUBLIC`;
- active pending queue: **slots 12–16 (5)**;
- next generation target after pending=0: **slot 17 AI EN**;
- OpenAI ledger last shown: `$0.1885/$10`;
- scheduler `VV Knopka Long Run` installed, Ready, triggers 01:30/03:30/05:30 MSK.

Real unattended validation passed: scheduler auto-uploaded slot 11, then gracefully handled `uploadLimitExceeded` with persisted cooldown/defer behavior.

The original bad unuploaded slot 16 was archived to:
`runtime/backups/slot-16-before-rebuild-20260831-231504`.
A corrected replacement slot 16 has now been rendered successfully and is the active pending artifact.

## Long-run generation
Starts at slot 16:
- cycle cats, AI, cats, AI...;
- AI EN;
- cat languages `en,en,en,en,ru`;
- AI subject cooldown 6.

Backlog-first scheduler:
1. status;
2. verify receipts;
3. best-effort stats;
4. pending > 0 => upload exactly one oldest and stop;
5. pending == 0 => generate one next long-run slot;
6. upload only newest generated video;
7. deferred/failure prevents backlog growth.

Do not generate slot 17 while upload backlog remains.

## Cat source reuse policy — IMPORTANT
The first real slot 16 / cat #008 had 5/6 cooled-down clips reused from cat #001. This was treated as a product bug.

Current anti-remake policy:
```toml
cat_source_cooldown_episodes = 5
cat_cooled_reuse_max_sources = 2
cat_cooled_reuse_max_per_history_episode = 1
```

Rules:
- fresh stock always first;
- recent 5 cat episodes stay protected;
- cooled history may contribute max 2 clips total;
- max 1 clip from any one older episode;
- fallback iterates newest-cooled episode first;
- if fresh + bounded cooled history cannot reach minimum quality/source count, fail closed;
- `source_reuse_audit.json` records cooled reuse by history slot and rejects concentration.

### Real corrected slot 16 validation
Replacement slot 16 rendered successfully under the new policy.
Final source composition:
- 6 unique clips total;
- 4 fresh Pexels clips;
- 2 cooled clips total;
- one cooled clip from slot 2 and one from slot 4;
- zero overlap with the protected recent-5-episode window.

Real audit:
```text
current_unique_sources: 6
reused_sources: []
reused_cooled_down_sources: 2
cooled_reuse_by_history_slot: {2:1, 4:1}
recent_reuse_passed: true
cooled_reuse_passed: true
passed: true
```

Final source IDs:
- fresh: `4427731`, `10467051`, `14326398`, `14927525`;
- cooled: `10358235` from slot 2, `5335581` from slot 4.

## Cat source v6 — audibility before vision
Current CLI routes cat sourcing through `animal_audio_sources_v6`.

Behavior:
- remote audio stream checked before Luna;
- confirmed stream gets FFmpeg mean-volume probe before Luna review;
- confirmed-silent files are rejected before paid vision review;
- CDN probe failures are limited to a small bounded fresh unknown tail;
- remote cooled-history candidates are excluded entirely; only bounded local v5 fallback may reuse history;
- retry cannot stack another cooled fallback on top of an existing one;
- diagnostics are appended even on sourcing failure;
- provider availability is recorded only as booleans, never secrets.

Config:
```toml
remote_audio_probe_seconds = 6.0
remote_audio_unknown_max_candidates = 12
```

Real successful replacement run:
```text
provider availability: Pexels=true, Pixabay=true
reused_audio_sources at retry start: 3
Pexels candidates: 54
vision reviewed: 54
vision approved: 51
new Pexels audio accepted: 3
Pixabay candidates: 0 (Pexels reached target before Pixabay fallback was needed)
```

`vision_reviewed=54` is still higher than desirable and is a later efficiency/cost optimization target, not a correctness blocker for the accepted slot 16.

Latest green code checkpoint for v6: `6e94b5d54309955a10ae2c499bd36e3db91f4320`, Ubuntu PASS + Windows PASS, **160 tests passed**.

## AI music — production approved
ACE-Step 1.5 local setup/generation works on user's RTX 3060.
All 8 tracks were generated, listened to and explicitly approved.

Real mixed-video previews were accepted:
- AI: `ai_volume=0.10`, ducking ON;
- cats: `cat_volume=0.11`, cat ducking OFF.

Current config intentionally enables reviewed music for future long-run renders:
```toml
[music]
enabled = true
ai_volume = 0.10
cat_volume = 0.11
ai_ducking = true
cat_ducking = false
```

Replacement slot 16 real music audit:
```text
track: curious_02.wav
applied_to_video: true
music_volume_applied: 0.11
ducking: false
```

Its YouTube metadata is `metadata_version=2` with `contains_synthetic_media=true`.
Approved local library is runtime-only and not committed.

## YouTube v2 / observability
Implemented and real-channel validated:
- metadata v2, hashtags, CTA, tags;
- conditional synthetic-media flag;
- upload limit cooldown;
- `vv-youtube verify`;
- `vv-youtube stats` + append-only history;
- `vv-youtube report` age-aware metrics.

Do not optimize content strategy from the first tiny sample.

## Published metadata backfill
User explicitly approved adding discovery metadata to already-published pilot videos.
Implemented safe commands:
```powershell
vv-youtube backfill-metadata --slots 1-11
vv-youtube auth-metadata
vv-youtube backfill-metadata --slots 1-11 --apply
```

Safety rules:
- default backfill is dry-run;
- only videos with local YouTube receipts are eligible;
- remote current snippet is read before changes;
- preserve remote title, category, language and all existing tags;
- append only missing hashtags to the existing description;
- merge hidden tags instead of replacing them;
- never touch privacy/status, video bytes, URL, views or upload receipt;
- `--apply` requires separate `youtube.force-ssl` OAuth permission;
- `auth-metadata` upgrades the existing local token only after verifying it is still the same bound channel; wrong-channel auth restores the previous token and fails closed;
- latest dry-run/apply audit is written to `runtime/youtube/metadata-backfill-latest.json`.

The existing uploader/verify automation keeps its original scopes/behavior and does not require the metadata-edit scope to continue operating.
Backfill code is awaiting/under fresh CI at this documentation checkpoint; do not call slots 1–11 updated on YouTube until the user runs the real `--apply` command and shares success output.

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

## Future comment feedback
See `docs/YOUTUBE_COMMENT_FEEDBACK_RU.md`.
Music-related negative comments should be topic-classified separately, aggregated across multiple comments/videos, and initially produce recommendations only.

## Immediate continuation
1. run/check fresh CI for YouTube metadata backfill;
2. user local `git pull`;
3. dry-run `vv-youtube backfill-metadata --slots 1-11` and inspect exact added tags/hashtags;
4. if dry-run is good, run `vv-youtube auth-metadata` once and confirm bound channel;
5. run `vv-youtube backfill-metadata --slots 1-11 --apply`, then rerun dry-run expecting `UNCHANGED`;
6. scheduler continues draining slots 12–16 oldest-first;
7. do not generate slot 17 until pending reaches zero;
8. after backlog drains, validate slot 17 AI EN end-to-end;
9. later optimize cat audio-first discovery so fewer Luna vision reviews are spent per accepted audible fresh clip.

After substantive work update this file plus `docs/PROJECT_HANDOFF_RU.md` and `docs/PROGRESS_RU.md`.
