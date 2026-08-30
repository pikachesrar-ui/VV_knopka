# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- Последний локальный pytest: **92 passed in 0.79s** до нового auto-refresh source patch.
- Последний показанный OpenAI ledger: **$0.0887 / $10.00**.
- `auto_publish=false`; publication gate = `PASS`.
- Slot 1 RU AI = manual **QUALITY PASS**.
- Slot 2 RU cats = manual **QUALITY PASS**.
- Slot 3 EN AI facts = manual **QUALITY PASS**.
- Slot 4 EN cats = manual **QUALITY PASS**.
- Slot 5 EN AI = **первый успешный настоящий conveyor render**.

Slot 5 был создан полностью через:

```powershell
.\.venv\Scripts\vv.exe pilot-next
```

Результат:

```text
runtime/slots/05/plan.json
Curated stock materials: 8
MPT task: bde437d8-38e1-48c2-bc41-8515a5d68595
runtime/ready_for_review/slot-05-en-ai.mp4
runtime/ready_for_review/slot-05-en-ai.upload.json
```

Это подтверждает локально: next-slot discovery, plan-on-demand, MPT path, AI render, ready_for_review output и upload metadata sidecar.

## Первый batch blocker и исправление

После slot 5 пользователь запустил:

```powershell
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Slot 6 cat sourcing собрал 6 источников, но cross-episode reuse gate обнаружил **5 уже использованных** Pexels source IDs и корректно остановил batch до highlight/render.

Примеры повторов:

```text
pexels:15769301
pexels:17536779
pexels:19306625
pexels:20420481
pexels:5335581
```

Старое поведение было безопасным, но недостаточно автономным: sourcing сначала переиспользовал старые top results, а post-gate только потом требовал ручной refresh.

### Automatic cat source refresh — IMPLEMENTED

Новый `src/vv_knopka/animal_audio_sources_v3.py` делает history-aware sourcing **до** финального reuse gate:

1. собирает identities из реально отрендеренных предыдущих cat episodes;
2. удаляет эти clips из текущего slot `sources.json`;
3. удаляет их из slot-local legacy `ai_materials.json` cache;
4. фильтрует те же IDs из новых Pexels/Pixabay candidate pools;
5. базовый source pipeline автоматически идёт глубже и пытается добрать свежие licensed/audible/near-9:16 clips;
6. финальный `source_history.py` gate остаётся как fail-closed страховка.

Локальные файлы старых источников не удаляются; они просто не допускаются в новый episode pool.

Текущий `vv` entrypoint идёт через `cli_v2`, а conveyor child processes через `pilot_conveyor_v2`, поэтому history-aware policy применяется и к прямому `render-animal`, и к `pilot-next`/`pilot-batch`.

## Cat production / YouTube CC

Первый production-safe YouTube CC источник:

```text
I_pdwiLlvuc | Kawaiipets
YouTube Creative Commons Attribution
2160x3840
Audio mean -14.8 dB
Full clean gate PASS 0.99
```

Не вводить обязательную YouTube quota. Clean YouTube pool может расти со временем; Pexels/Pixabay остаются safe fallback. Все rights / clean-footage / near-9:16 / audible-audio gates сохраняются.

Cat формат принят: generic numbered cats, Impact, real meow, без voiceover/BGM.

## Review-first conveyor

Команды:

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Поведение:

- strict manifest order;
- existing non-empty ready MP4 = completed/resumable slot;
- state: `runtime/conveyor/state.json`;
- AI: plan on demand + managed/check MPT + render;
- cats: licensed source acquisition + audio/aspect/clean/history gates + local FFmpeg render;
- stop on first failure;
- outputs only `runtime/ready_for_review`;
- no publishing;
- hard `$10` OpenAI budget.

MPT manager prefers local MPT `.venv/venv` Python and does not require `uv`; if MPT was already running, conveyor leaves it alone.

## Upload metadata

Successful new renders produce `.upload.json` with proposed title/description, language/pipeline/video path, required CC attribution, `review_required=true`, `auto_publish=false`, `publication_allowed_by_conveyor=false`.

Cat external title family: `Cats That Made My Day 😹 #NNN #shorts`; on-card identity remains `#NNN — Cats`. AI title is derived from the actual fact plan.

## CI

Latest code-head test job after automatic cat-source refresh:

```text
95 passed in 0.65s
Verify pilot lock: success
```

Windows-bootstrap for that exact head was still running at the time of the check; do not claim full workflow green without a new live check.

## Immediate next local step

Pull the auto-refresh patch and reinstall editable entrypoint:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

Expected test count around **95 passed**.

Then retry the same batch command:

```powershell
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Because slot 5 already exists, pending order should begin at slot 6. Slot 6 should now automatically exclude earlier cat source IDs and search deeper for fresh clips. If it still cannot reach the minimum fresh source count, fail closed and inspect `runtime/slots/06/animal_audio_sources.json`; do not weaken gates.

Draft PR #1 remains open/draft and unmerged.
