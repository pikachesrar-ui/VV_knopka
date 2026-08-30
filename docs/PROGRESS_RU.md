# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний показанный OpenAI ledger: **$0.0618 / $10.00** до последнего успешного YouTube clean-review; не угадывать более новый ledger.
- Последний показанный локальный pytest: **81 passed in 0.55s** до последних aspect-preflight / MPT-health regression tests.
- Slot 1 RU AI Short (octopus) = manual **QUALITY PASS**.
- Slot 2 RU cats = manual **QUALITY PASS** after successful mixed YouTube+stock render.
- Cat renderer = local FFmpeg; real meow + Impact; no voiceover/BGM.
- Production output remains review-first under `runtime/ready_for_review`.

## Первый принятый YouTube CC production source

Current saved-report candidate #2 successfully passed the complete production path:

```text
I_pdwiLlvuc | Cutest Angry Cat You’ll Ever See 😾❤️ | Kawaiipets
Rights evidence: youtube_data_api_status_license
License: YouTube Creative Commons Attribution
Dimensions: 2160x3840
Audio mean: -14.8 dB
Full clean-footage gate: PASS | confidence=0.99
```

Clean review found the same clearly visible cat in a consistent setting with no creator branding, social UI or added captions. This is the **first YouTube CC source accepted for production**.

All earlier problematic candidates remain rejected:

- 3 Pawcsu clips — branding/handle/large captions.
- `nWieRK7Fw-g` — livestream/chat UI + branding/captions.
- `hxXfevBB9Zs` — real stitched multi-clip sequence after contact-sheet-aware v2 recheck.
- `cQE-s_wsclw` — full source 502×720, outside near-9:16 tolerance; deterministic preview format gate was added so future cases fail before Luna/full download.

## Latest slot 2 mixed render — QUALITY PASS

User rendered slot 2 after accepting `I_pdwiLlvuc`.

Final output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
1080x1920
~35.75 s
```

FFmpeg emitted several `Non-monotonic DTS` warnings during concat, but completed the render and final faststart copy successfully.

User verdict: the result is **better and now liked/accepted**. Treat slot 2 RU cat format as manual QUALITY PASS.

The render used only one YouTube clip because only one YouTube CC source had passed every production gate at that point. This is expected, not a selector failure. Remaining material came from accepted stock fallback.

## Source-pool optimization decision

Do **not** force a minimum YouTube quota per episode. That would either fail unnecessarily or pressure the system to weaken gates.

Preferred long-run behavior:

```text
background/source acquisition
-> accumulate reusable clean YouTube CC pool over time
-> retain Pexels/Pixabay fallback
-> renderer prefers varied accepted sources when available
-> never require unsafe/unverified media merely to hit a YouTube count
```

As the clean YouTube pool grows to several clips, later compilations should naturally contain more YouTube-origin footage. Add duplicate/history controls before large-scale reuse so the same clip is not overused across episodes.

## Current launch phase

Both Russian proof-of-format videos are accepted:

1. slot 1 RU AI fact Short = QUALITY PASS;
2. slot 2 RU cat compilation = QUALITY PASS.

Next before starting the remaining pilot conveyor:

1. **English AI-fact test:** slot 3 (`ai_short`, EN); previous slot-3 relevance attempt was poor, so material relevance gate remains important.
2. **English cat test:** slot 4 (`animal_compilation`, EN) using the accepted cat format.
3. Freeze YouTube title policy. Keep simple numbered cat on-card identity, but YouTube-facing titles should be more natural/hooky; AI-fact titles should be topic-specific rather than a repeated template.
4. Add a local review-first conveyor runner that processes the next unrendered pilot slot(s), writes only to `runtime/ready_for_review`, respects the `$10` budget and never publishes automatically.
5. Optionally wire that runner to Windows Task Scheduler only after both English test videos pass manual review.

Frozen manifest reminder from `config/pilot.toml`:

```text
AI slots:     1,3,5,7,9,11,13,15
Animal slots: 2,4,6,8,10,12,14
RU slots:     1,2
```

## Slot 3 EN — current state / MPT blocker

User successfully created:

```text
runtime/slots/03/plan.json
```

Then ran `vv render-ai 3`. The material stage succeeded and found/reused:

```text
Using duration-sufficient approved stock: 4 unique sources, 79.0s reusable footage
Curated stock materials: 4
```

Render then failed before creating an MPT task with:

```text
httpx.ConnectError / WinError 10061
```

This means the separate local MoneyPrinterTurbo API was not running/listening at the configured local endpoint. It is not an OpenAI/material-selection failure. The already prepared slot-3 plan/material cache can be reused; do not regenerate them just because MPT was offline.

MoneyPrinterTurbo remains a separate upstream service and should be started from the local ignored checkout in another terminal. Current upstream documented API startup:

```powershell
cd D:\KiraS\VV_knopka\MoneyPrinterTurbo
uv run python main.py
```

(or `python main.py` from its active environment). API docs should then be reachable at `http://127.0.0.1:8080/docs`.

## MPT early health preflight — IMPLEMENTED

New module:

```text
src/vv_knopka/mpt_health.py
```

`vv render-ai SLOT` now checks MPT reachability **before** preparing/reviewing materials. If MPT is offline, it exits with a short actionable message telling the user to start `uv run python main.py`, instead of doing provider/vision work first and ending in a long `httpx.ConnectError` traceback.

This is intentionally only a health preflight for now. VV_knopka does **not** automatically spawn or kill MoneyPrinterTurbo yet. Process lifecycle should be implemented with the future `pilot-next`/conveyor runner so unattended operation can start MPT safely and know when it is ready.

GitHub CI on the MPT-health code head:

```text
86 passed in 0.64s
Verify pilot lock: success
```

Windows-bootstrap was still running at that exact check; do not claim the entire workflow complete without rechecking.

## Current title direction

Recommended cat YouTube title family (external title, not necessarily the black-card title):

```text
RU: Котики, которые сделали мой день 😹 #001 #shorts
EN: Cats That Made My Day 😹 #002 #shorts
```

Keep the internal/on-card cat series identity simple (`#NNN — Котики` / `#NNN — Cats`). Avoid copying `Daily Dose of Cats` naming.

AI-fact titles should be generated from the actual fact/hook, for example:

```text
Octopuses Have 3 Hearts — Here’s Why 🐙 #shorts
```

Avoid using one identical `Did You Know...?` template for every upload.

## Immediate next local step

Start MPT in a second PowerShell:

```powershell
cd D:\KiraS\VV_knopka\MoneyPrinterTurbo
uv run python main.py
```

Verify `http://127.0.0.1:8080/docs`, then in the VV_knopka terminal:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe render-ai 3
```

Expected test count around **86 passed**. Do **not** rerun `vv plan 3`; existing plan and 4-source/79s material cache should be reused.

After slot 3 renders, visually inspect it. If EN AI facts pass, render slot 4 EN cats. After both EN proofs pass, implement the local review-first conveyor runner and only then consider Windows Task Scheduler / later upload OAuth.

Draft PR #1 remains review-only; do not merge without explicit user decision after visual review.
