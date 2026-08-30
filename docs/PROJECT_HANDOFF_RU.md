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

## Manual quality / latest local state

User visually accepted proof pair in both branches:

- slot 1 RU AI facts = QUALITY PASS;
- slot 2 RU cats = QUALITY PASS;
- slot 3 EN AI facts = QUALITY PASS;
- slot 4 EN cats = QUALITY PASS.

Latest explicitly shown local state before newest code patch:

```text
99 passed in 0.67s
OpenAI spent: $0.1036 / $10.00
auto_publish: False
publication gate: PASS
```

Do not guess newer local ledger/test values without new user output.

## Conveyor validation status

Completed final outputs now confirmed through **slot 9**:

- slot 5 EN AI — SUCCESS;
- slot 6 EN cats — SUCCESS;
- slot 7 EN AI — SUCCESS;
- slot 8 EN cats — SUCCESS after Pixabay helper bug fix;
- slot 9 EN AI — SUCCESS in the next batch.

Slot 8 final: `runtime/ready_for_review/slot-08-en-animals.mp4` + `.upload.json`, 1080x1920, ~35.75 s.

This demonstrates resumability and unattended sequencing across multiple cat/AI transitions.

## Current blocker: slot 10 fresh audible stock

Next `pilot-batch --count 3` completed slot 9, then slot 10 EN cats failed safely:

```text
Vertical audible-source gate found only 0/5 usable cat clips
```

No code exception occurred. With cat episodes 2/4/6/8 already rendered, prior source identities are excluded and the current top-heavy stock pool has become exhausted under the existing near-9:16 + audible-source requirements.

Do not weaken rights/audio/aspect/history rules and do not allow heavy source reuse merely to pass this gate.

## Audio-aware deep stock sourcing

Root cause found in the collector order: candidate caps were filled before audio was known. The old flow collected up to 60 Pexels / 80 Pixabay vertical candidates, ran Luna, and only then remote-probed/downloaded them. Silent stock could therefore consume the entire candidate/vision pool.

Current `animal_audio_sources_v4.py` fix:

1. prior rendered IDs are still excluded during collection;
2. near-9:16 metadata gate still runs first;
3. chosen remote file is ffprobe-checked for an audio stream **before Luna and before candidate-cap accounting**;
4. confirmed-silent remote files are skipped and collection keeps walking the catalog;
5. confirmed-audio candidates are preferred;
6. probe failures/unknowns stay fallback candidates rather than becoming permanent rejects;
7. Luna caps remain unchanged — the goal is better candidate quality, not more paid usage;
8. Pexels/Pixabay still paginate 4 pages/query;
9. cat query diversity expanded (eating/grooming/walking/jumping/home/indoor/domestic etc.);
10. Pixabay searches both `popular` and `latest` and deduplicates IDs.

`deep_stock_search` audit now records audio-prefilter settings and search orders.

Regression test explicitly proves that a page-1 confirmed-silent candidate does not consume the cap and that search proceeds to a page-2 audible candidate.

Latest tested **code-head** CI:

```text
101 passed in 0.64s
Verify pilot lock: success
```

Later docs-only commits move branch HEAD; do not misstate that exact CI as having tested those docs commits.

## Failed-attempt resume

`animal_audio_sources_v5.py` still restores validated local fresh Pexels/Pixabay clips from a previous failed `animal_audio_sources.json`. Slot 10's latest failure selected 0 clips, so the new retry mainly benefits from audio-aware search rather than recovery.

## Cat / YouTube sourcing

First accepted YouTube CC clean source remains `I_pdwiLlvuc` / Kawaiipets / 2160x3840 / audio -14.8 dB / clean PASS 0.99.

Do not force a YouTube quota. YouTube Data API is discovery/license metadata, not an official media-download endpoint. Automated production acquisition should prefer Pexels/Pixabay or creator/independently authorized downloadable files.

Cross-episode source reuse final gate allows maximum one incidental repeated identity; 2+ reused sources fail closed. Fresh-first sourcing currently excludes all prior IDs during normal discovery.

## Review-first conveyor

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count 3
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

## Upload metadata / titles

Each successful render creates `.upload.json` with proposed title/description, language/pipeline/video path, attribution, `review_required=true`, `auto_publish=false`, `publication_allowed_by_conveyor=false`.

Cat external title family: `Cats That Made My Day 😹 #NNN #shorts`; on-card remains `#NNN — Cats`. AI titles come from the specific fact plan.

## Immediate local continuation

Slots 1-9 are complete and slot 10 is pending. Pull newest code and retry only one slot first:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe pilot-next --dry-run
.\.venv\Scripts\vv.exe pilot-next
```

Expected tests around **101 passed** and dry-run slot 10 EN cats. Discovery may take longer because remote audio is checked while traversing stock, but known-silent clips should no longer waste Luna/candidate slots.

If slot 10 still fails below 5, inspect `runtime/slots/10/animal_audio_sources.json`. Next escalation: expand free/licensed provider/search strategy or only then consider the already-policy-allowed one-repeat fallback; do not relax core quality/provenance gates.

## Git / release

Continue on `mvp/pilot-scaffold`, Draft PR #1. Do not merge until separate user decision after local conveyor validation/review.
