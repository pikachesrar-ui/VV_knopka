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
Confirmed locally before slot-16 replacement:
- YouTube receipts: 11;
- slots 1–11 = `VERIFIED_PUBLIC`;
- OpenAI ledger last shown: `$0.1885/$10`;
- scheduler `VV Knopka Long Run` installed, Ready, triggers 01:30/03:30/05:30 MSK.

Real unattended validation passed: scheduler auto-uploaded slot 11, then gracefully handled `uploadLimitExceeded` with persisted cooldown/defer behavior.

The bad unuploaded slot 16 was archived to `runtime/backups/slot-16-before-rebuild-20260831-231504` and removed from the active ready queue. Active upload backlog is therefore slots 12–15 until a replacement slot 16 is successfully rendered.

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

Do not generate slot 17 while slot 16 is missing or upload backlog remains.

## Cat source reuse policy — IMPORTANT
The user inspected real slot 16 / cat episode #008 and found heavy repetition from episode #001.
Original audit proved:
- 6 final sources;
- 5 were cooled-down Pexels sources from slot 2 / cat #001;
- fresh search contributed only one source.

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

### Real rebuild test
After archiving old slot 16, `vv longrun-next` ran under the anti-remake policy and correctly failed closed:
- first pass: only `1/5` usable fresh clips;
- bounded fallback raised the pool only to `3/5`;
- no replacement MP4 was produced.

Detailed audit showed the real bottleneck:
```text
Pexels candidates: 59
vision reviewed: 59
vision approved: 56
audio accepted from new Pexels candidates: 0
rejection: 56 × downloaded file is missing audible audio
selected after fallback: 3 (1 fresh + 2 cooled)
Pixabay candidates: 0
```

This proved visual relevance and 9:16 were not the limiting gates; audible source audio was.

## Cat source policy v6 — audibility before vision
Current CLI routes cat sourcing through `animal_audio_sources_v6`.

New behavior:
- remote file must first pass audio-stream inspection;
- when a stream exists, FFmpeg measures the first configured seconds against `min_source_mean_volume_db` before Luna review;
- confirmed-silent files are rejected before paid vision review;
- CDN probe failures are allowed only in a small bounded fresh `unknown` tail;
- remote cooled-history candidates are excluded entirely; only v5 bounded local fallback can reuse history;
- retry after a failed attempt cannot stack a second cooled fallback on top of existing cooled clips;
- diagnostic audit is appended even when sourcing fails;
- audit records whether Pexels/Pixabay API keys are present without exposing secrets.

Config:
```toml
remote_audio_probe_seconds = 6.0
remote_audio_unknown_max_candidates = 12
```

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

Approved local library is runtime-only and not committed. Applied AI music must propagate YouTube synthetic-media disclosure.

## YouTube v2 / observability
Implemented and real-channel validated:
- metadata v2, hashtags, CTA, tags;
- conditional synthetic-media flag;
- upload limit cooldown;
- `vv-youtube verify`;
- `vv-youtube stats` + append-only history;
- `vv-youtube report` age-aware metrics.

Do not optimize from the first tiny sample.

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
1. wait for green CI on cat-source v6;
2. local `git pull`;
3. check provider availability without printing API keys;
4. rerun `vv longrun-next` for replacement slot 16;
5. inspect `animal_audio_sources.json`, `source_reuse_audit.json`, `music.json` and preview if render succeeds;
6. if v6 still cannot find enough audible fresh stock, use provider-availability audit to decide the next sourcing expansion instead of loosening anti-remake/audio gates;
7. scheduler continues draining slots 12–15;
8. slot 17 remains blocked until replacement slot 16 and backlog policy are satisfied.

After substantive work update this file plus `docs/PROJECT_HANDOFF_RU.md` and `docs/PROGRESS_RU.md`.
