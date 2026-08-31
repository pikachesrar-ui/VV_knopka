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

## Real YouTube checkpoint — 2026-08-31
Confirmed locally:
- ready before slot-16 rebuild: 16 Shorts;
- YouTube receipts: 11;
- slots 1–11 = `VERIFIED_PUBLIC`;
- pending queue before rebuild: slots 12–16;
- OpenAI ledger: `$0.1885/$10`;
- scheduler `VV Knopka Long Run` installed, Ready, triggers 01:30/03:30/05:30 MSK.

Real unattended validation passed: scheduler auto-uploaded slot 11, then gracefully handled `uploadLimitExceeded` with persisted cooldown/defer behavior.

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

## Cat source reuse policy — IMPORTANT
The user inspected real slot 16 / cat episode #008 and found heavy repetition from episode #001.
Audit proved:
- 6 final sources;
- 5 were cooled-down Pexels sources from slot 2 / cat #001;
- fresh search contributed only one source;
- old policy passed because it bounded only recent-window reuse, not cooled-history concentration.

This is now treated as a product bug.

Current policy:
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
- fallback iterates newest-cooled episode first, not oldest-first;
- if fresh + bounded cooled history cannot reach the minimum quality/source count, fail closed rather than build a near-remake of an older compilation;
- `source_reuse_audit.json` records cooled reuse by history slot and fails on concentration/total-limit violations.

Existing bad slot 16 is not published and should be archived/rebuilt before its upload turn. Do not regenerate slot 17 while backlog remains.

## AI music — production approved
ACE-Step 1.5 local setup/generation works on user's RTX 3060.
All 8 tracks were generated, listened to and explicitly approved:
- `cute_01.wav`, `cute_02.wav`;
- `playful_01.wav`, `playful_02.wav`;
- `curious_01.wav`, `curious_02.wav`;
- `calm_01.wav`, `calm_02.wav`.

Real mixed-video previews were accepted:
- AI mix: good at `ai_volume=0.10` with ducking;
- cat first preview was too quiet;
- cat v2 accepted at `cat_volume=0.11` with `cat_ducking=false`.

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
Music-related negative comments should be topic-classified separately, aggregated across multiple comments/videos, and initially produce recommendations only. Never mutate production policy because of one negative comment.

## Immediate continuation
1. wait for current CI after cat anti-remake + music activation;
2. local `git pull`;
3. archive existing unuploaded slot 16 artifacts;
4. rebuild slot 16 through `vv longrun-next` so it uses strict source policy + approved production music + final metadata;
5. inspect new source audits and preview slot 16;
6. keep scheduler draining slots 12–16;
7. only after pending reaches zero allow slot 17 AI EN.

After substantive work update this file plus `docs/PROJECT_HANDOFF_RU.md` and `docs/PROGRESS_RU.md`.
