# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя после visual review.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

Manifest:

```text
AI slots:     1,3,5,7,9,11,13,15
Animal slots: 2,4,6,8,10,12,14
RU slots:     1,2
```

## Local accepted proof videos

- Slot 1 RU AI Short (octopus) = manual **QUALITY PASS**.
- Slot 2 RU cat compilation = manual **QUALITY PASS** after the latest mixed YouTube+stock render.
- Cat format: generic numbered cats, Impact cards, real meow, no voiceover, no BGM, strict near-9:16 sources.
- Latest shown local pytest: **81 passed in 0.55s** before the newest aspect-preflight regression tests.
- Last shown OpenAI ledger: **$0.0618 / $10.00** before the final successful YouTube candidate review; do not infer a newer number.

## First production-safe YouTube CC clip

`I_pdwiLlvuc` — `Cutest Angry Cat You’ll Ever See 😾❤️` — creator `Kawaiipets`.

Observed local pass:

```text
Rights evidence: youtube_data_api_status_license
License: YouTube Creative Commons Attribution
Dimensions: 2160x3840
Audio mean: -14.8 dB
Full clean-footage gate: PASS | confidence=0.99
```

The clean gate saw the same cat/setting across timestamps and no creator branding, social UI or added captions. This is the first YouTube CC clip accepted into production.

Previous rejected YouTube candidates remain rejected for branding/captions, livestream/social UI, stitched compilation, or bad aspect ratio. Do not weaken gates to increase yield.

## Latest slot 2 render

Final output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
1080x1920
~35.75 sec
```

FFmpeg concat printed `Non-monotonic DTS` warnings but completed successfully. User said the latest result is better and now likes it; treat this as slot-2 manual QUALITY PASS.

Only one YouTube clip appeared because only one YouTube source had passed the complete gate. Remaining material came from stock. This is expected behavior.

## Source optimization decision

Do not force `N` YouTube clips per episode. Instead grow a clean source pool over time:

```text
CC discovery + strict validation
-> reusable accepted YouTube pool grows
-> stock remains safe fallback
-> renderer uses varied accepted material
```

Before scaling, add cross-episode source-history/duplicate control so accepted clips are not overused. A larger clean YouTube pool should naturally increase YouTube-origin material per compilation without lowering standards.

## Current YouTube production flow

```text
official API CC search
-> one candidate/channel + thumbnail prescreen + reject memory
-> official CC recheck
-> low-res preview
-> deterministic near-9:16 + duration preview gate BEFORE Luna
-> contact-sheet-aware Luna temporal gate
-> only on PASS: full-quality download
-> full near-9:16 + duration + audible audio
-> final clean gate
-> production sources.json only on PASS
```

Deterministic format rejects are durable and remembered. Transient preview/tool failures are not permanent rejects.

## Next milestone: English proof pair

User considers the project close to conveyor launch. Before batch automation, produce and manually review:

1. slot 3 EN `ai_short` (facts);
2. slot 4 EN `animal_compilation` (cats).

Slot 3 previously had a poor relevance result (2/8), so do not weaken relevance gating merely to get an output. Slot 4 should reuse the now-accepted cat visual/audio/card format.

## Title direction

Keep on-card cat identity simple:

```text
#NNN — Котики
#NNN — Cats
```

Recommended YouTube-facing cat title family:

```text
Котики, которые сделали мой день 😹 #001 #shorts
Cats That Made My Day 😹 #002 #shorts
```

Do not imitate `Daily Dose of Cats` branding.

AI-fact YouTube titles should be generated from the specific hook/topic, e.g.:

```text
Octopuses Have 3 Hearts — Here’s Why 🐙 #shorts
```

Avoid one repeated `Did You Know...?` template across the channel.

## Conveyor automation direction

After slot 3 and slot 4 both receive manual QUALITY PASS, implement a **local review-first conveyor runner**. It should:

- inspect the deterministic 15-slot manifest;
- find the next unrendered eligible slot;
- run the correct pipeline;
- stop/fail closed on budget, source or quality gates;
- write outputs only to `runtime/ready_for_review`;
- never publish automatically (`auto_publish=false` remains frozen);
- keep logs/checkpoints so interrupted runs are resumable.

Only after this runner is proven locally should optional Windows Task Scheduler cadence be added. The local PC/services (including MPT for AI shorts) must be available for scheduled runs.

## Git / release

Continue on `mvp/pilot-scaffold`, Draft PR #1. Do not merge merely because both RU proof videos passed; English proof pair and conveyor behavior should be reviewed first unless the user explicitly changes the release decision.
