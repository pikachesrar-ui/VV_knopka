# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

Manifest:

```text
AI slots:     1,3,5,7,9,11,13,15
Animal slots: 2,4,6,8,10,12,14
RU slots:     1,2
```

## Manual quality / local state

User visually accepted proof pair in both branches:

- slot 1 RU AI facts = QUALITY PASS;
- slot 2 RU cats = QUALITY PASS;
- slot 3 EN AI facts = QUALITY PASS;
- slot 4 EN cats = QUALITY PASS.

Last explicitly shown local OpenAI ledger was `$0.1036 / $10.00`; do not guess newer value without new `vv status` output.

## Conveyor validation status

Final ready outputs are now user-confirmed through **slot 13**.

Successful conveyor sequence so far:

- slot 5 EN AI — SUCCESS;
- slot 6 EN cats — SUCCESS;
- slot 7 EN AI — SUCCESS;
- slot 8 EN cats — SUCCESS after Pixabay helper fix;
- slot 9 EN AI — SUCCESS;
- slot 10 EN cats — SUCCESS after remote-audio prefilter improvement;
- slot 11 EN AI — SUCCESS;
- slot 12 EN cats — SUCCESS;
- slot 13 EN AI — SUCCESS.

Most recent `pilot-batch --count 3` completed slots 11 -> 12 -> 13 without interruption. Slot 12 produced a final 1080x1920 ~35.75 s cat Short and upload metadata; slot 13 then completed plan-on-demand, 8 curated stock materials, MPT render and upload metadata.

This is strong end-to-end evidence that the review-first conveyor can sequence AI -> cats -> AI autonomously and resume without regenerating completed slots.

Remaining pilot slots:

```text
slot 14 — EN animal_compilation
slot 15 — EN ai_short
```

## Cat sourcing architecture

Keep all current gates:

- licensed/commercial-use provenance;
- source already near 9:16;
- audible source audio;
- vision relevance;
- cross-episode history;
- fail closed below 5 usable clips.

Remote-audio prefilter in `animal_audio_sources_v4.py` runs before Luna/candidate-cap accounting so confirmed-silent stock no longer wastes finite vision capacity. Pexels/Pixabay search uses history exclusion, deeper pagination/query diversity, and Pixabay `popular` + `latest` ordering.

Cross-episode final reuse gate permits at most one incidental repeated `provider + provider_id`; 2+ reused identities fail closed.

First accepted clean YouTube CC reference remains `I_pdwiLlvuc` / Kawaiipets / 2160x3840 / audio -14.8 dB / clean gate PASS 0.99. Do not force a YouTube quota. YouTube Data API is for discovery/license metadata, not an official media-download endpoint; production acquisition should prefer explicitly downloadable/licensed stock or independently authorized source files.

## Review-first conveyor

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count N
```

- strict manifest order;
- non-empty expected MP4 = completion marker/resume boundary;
- state: `runtime/conveyor/state.json`;
- AI: plan-on-demand + managed/check MPT + render;
- cats: licensed sourcing + geometry/audio/vision/history gates + local FFmpeg;
- stop on first failure;
- outputs only `runtime/ready_for_review`;
- `$10` OpenAI hard guard;
- `auto_publish=false`; no uploader/OAuth yet.

Each successful render creates `.upload.json` with proposed title/description, language/pipeline/video path, required attribution, `review_required=true`, `auto_publish=false`, `publication_allowed_by_conveyor=false`.

## Immediate local continuation

Because slots 1–13 have ready outputs, the next pending slot must be slot 14.

```powershell
cd D:\KiraS\VV_knopka
.\.venv\Scripts\vv.exe pilot-next --dry-run
```

Expected:

```text
slot 14: animal_compilation / en
```

Then finish the frozen pilot with:

```powershell
.\.venv\Scripts\vv.exe pilot-batch --count 2
```

Expected: slot 14 cats, then slot 15 AI facts. After both complete, visually review the newest generated MP4s before changing publication policy. Do not enable automatic upload merely because the conveyor completed; Windows Task Scheduler and YouTube uploader/OAuth are a later explicit phase.

## Git / release

Continue on `mvp/pilot-scaffold`, Draft PR #1. Do not merge until separate user decision after local conveyor validation/review.
