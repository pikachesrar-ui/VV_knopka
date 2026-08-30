# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- Последний явно показанный локальный pytest перед новым audio-prefilter patch: **99 passed in 0.67s**.
- Последний явно показанный OpenAI ledger: **$0.1036 / $10.00**.
- `auto_publish=false`; publication gate = `PASS`.
- Slot 1 RU AI = manual **QUALITY PASS**.
- Slot 2 RU cats = manual **QUALITY PASS**.
- Slot 3 EN AI facts = manual **QUALITY PASS**.
- Slot 4 EN cats = manual **QUALITY PASS**.
- Slot 5 EN AI = successful conveyor render.
- Slot 6 EN cats = successful conveyor render.
- Slot 7 EN AI = successful conveyor render.
- Slot 8 EN cats = **successful one-slot retry after Pixabay helper fix**.
- Slot 9 EN AI = **successful next batch render**.

Slot 8 final output:

```text
runtime/ready_for_review/slot-08-en-animals.mp4
runtime/ready_for_review/slot-08-en-animals.upload.json
1080x1920, ~35.75 s
```

Slot 9 then completed automatically through plan-on-demand -> 8 curated stock materials -> MPT task -> final MP4 + upload metadata.

This confirms resumability: the retry did not regenerate completed slots 6/7, and the next batch skipped completed slot 8 and moved to slot 9.

## Slot 10 fresh-source exhaustion

The next batch reached slot 10 EN cats and failed safely:

```text
RuntimeError: Vertical audible-source gate found only 0/5 usable cat clips.
See runtime/slots/10/animal_audio_sources.json.
```

This is no longer a Python exception. After slots 2/4/6/8 have consumed and history-blocked earlier stock IDs, the existing deep search pool produced zero new clips that survived the full vertical + audible-source requirements.

Do not solve this by disabling source history, allowing heavy reuse, accepting silent clips, or widening the 9:16 gate.

## Root cause: candidate cap was filled before audio was known

The base flow used to:

1. collect up to 60 fresh Pexels / 80 Pixabay vertical candidates;
2. run Luna visual relevance on that finite pool;
3. only afterwards probe/download each approved file and discover whether it actually has audio.

Therefore confirmed-silent stock could consume most/all of the finite candidate and vision pool, producing `0/5` even though audible candidates might exist deeper in the catalog.

## Pre-vision remote audio filtering — IMPLEMENTED

`animal_audio_sources_v4.py` now probes the chosen remote stock file with ffprobe **before Luna and before it consumes the candidate cap**:

- remote audio `False` -> candidate is skipped immediately;
- remote audio `True` -> preferred candidate;
- transient/unknown probe -> retained only as fallback, not made a permanent reject;
- confirmed-audio candidates are ranked ahead of unknown candidates;
- Pexels/Pixabay history exclusion and near-9:16 metadata checks remain before this step;
- Luna candidate caps remain unchanged, so this should reduce wasted paid vision work rather than increase it.

Additional catalog diversity:

- generic cat queries expanded with eating/grooming/walking/jumping/home/indoor/domestic variants;
- Pixabay searches both `popular` and `latest` while deduplicating IDs;
- pagination stays at 4 pages/query for now; do not blindly increase paid candidate caps before observing the new local audit.

Audit field `deep_stock_search` records remote audio prefilter, probe timeout, query list and Pixabay orders.

Regression tests verify that a confirmed-silent candidate on page 1 does not consume the cap and that the collector continues to an audible candidate on page 2.

Latest **code-head** CI after this patch:

```text
101 passed in 0.64s
Verify pilot lock: success
```

The docs commits after that move branch HEAD; this statement is specifically about the tested code commit, not an unverified claim about every later docs-only SHA.

## Failed-attempt resume

`animal_audio_sources_v5.py` still recovers already validated fresh local Pexels/Pixabay `selected_sources` from a previous failed `animal_audio_sources.json` when present. Slot 10 reported `0/5`, so there may be nothing to recover from that specific failed attempt; the important next change is the new pre-vision audio-aware search.

## Cat production / YouTube CC

First production-safe YouTube CC source remains `I_pdwiLlvuc` / Kawaiipets / Creative Commons Attribution / 2160x3840 / audio -14.8 dB / clean gate PASS 0.99.

Do not introduce a mandatory YouTube quota. YouTube discovery/license metadata is separate from media-acquisition permission; automated production acquisition should continue preferring explicitly downloadable/licensed stock or independently authorized files.

## Review-first conveyor

Commands:

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Behavior: strict manifest order; existing ready MP4 = resumable completion marker; state in `runtime/conveyor/state.json`; AI plan-on-demand + MPT; cats use licensed source acquisition + aspect/audio/vision/history gates; stop on first failure; outputs only `runtime/ready_for_review`; no publishing; hard `$10` OpenAI guard.

## Immediate next local step

Slots 1-9 now have final outputs; slot 10 does not. After pulling the audio-prefilter patch:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe pilot-next --dry-run
.\.venv\Scripts\vv.exe pilot-next
```

Expected dry-run: **slot 10 EN animal_compilation**. Expected tests around **101 passed**.

The slot 10 retry may spend longer in stock discovery because it is now probing remote audio while walking the catalog, but it should avoid spending Luna/candidate capacity on files known to be silent. If it still cannot reach 5, inspect `runtime/slots/10/animal_audio_sources.json` before further policy changes. The next escalation should be provider/source-pool expansion or smarter free discovery, not heavy source reuse.

Draft PR #1 remains open/draft and unmerged.
