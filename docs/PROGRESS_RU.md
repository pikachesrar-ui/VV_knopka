# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- Последний локальный pytest: **95 passed in 0.63s**.
- Последний явно показанный OpenAI ledger: **$0.0887 / $10.00** до последних cat-source retries; не угадывать более новое значение.
- `auto_publish=false`; publication gate = `PASS`.
- Slot 1 RU AI = manual **QUALITY PASS**.
- Slot 2 RU cats = manual **QUALITY PASS**.
- Slot 3 EN AI facts = manual **QUALITY PASS**.
- Slot 4 EN cats = manual **QUALITY PASS**.
- Slot 5 EN AI = **первый успешный настоящий conveyor render**.

Slot 5 был создан полностью через `vv pilot-next`: plan-on-demand -> 8 curated stock materials -> MPT task -> `runtime/ready_for_review/slot-05-en-ai.mp4` + `.upload.json`.

## Slot 6 cat sourcing — реальный bottleneck

Первый batch после slot 5 остановился на 5 reused Pexels source IDs. History-aware v3 начал исключать старые IDs до render.

После pull пользователь подтвердил **95 passed in 0.63s** и повторил:

```powershell
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Новый history-aware sourcing уже не переиспользовал старую пятёрку, но fresh pool оказался слишком маленьким:

```text
RuntimeError: Vertical audible-source gate found only 2/5 usable cat clips.
See runtime/slots/06/animal_audio_sources.json.
```

Это полезный fail-closed: rights/audio/near-9:16/history gates не были ослаблены. Причина найдена в search depth: stock collectors в основном брали первую страницу популярных Pexels/Pixabay результатов, поэтому после исключения ранее использованных IDs пул быстро истощался.

## Deep fresh-stock sourcing — IMPLEMENTED

Новый `src/vv_knopka/animal_audio_sources_v4.py`:

1. исключает IDs предыдущих реально отрендеренных cat episodes **во время сбора**, а не после заполнения `max_candidates`;
2. пагинирует Pexels/Pixabay до **4 страниц на query**;
3. добавляет query diversity: `cat`, `kitten`, `cute cat`, `funny cat`, `cat playing`, `kitten playing`, `cat meowing`, `cat purring`, `house cat`, `pet cat`;
4. сохраняет прежние duration / near-9:16 / vision / audible-audio / license gates;
5. candidate cap не повышен бесконтрольно — задача пагинации в том, чтобы заполнить существующий cap **свежими** IDs вместо старых популярных результатов.

Audit получает `deep_stock_search` с параметрами поиска.

## Resume failed cat-source attempts — IMPLEMENTED

Новый `src/vv_knopka/animal_audio_sources_v5.py` решает вторую потерю эффективности.

При fail `2/5` базовый pipeline уже записал два успешно проверенных свежих источника в `runtime/slots/06/animal_audio_sources.json`, но из-за fail-closed ещё не создал финальный `sources.json` с ними.

На следующем retry v5:

- читает `selected_sources` предыдущего failed audit;
- восстанавливает только локально существующие `pexels` / `pixabay` файлы;
- не восстанавливает source IDs из предыдущих отрендеренных episodes;
- не восстанавливает YouTube через этот shortcut;
- кладёт эти свежие источники обратно в working source manifest;
- затем v4 ищет только недостающие свежие клипы.

Это уменьшает повторные downloads/vision review после безопасного fail.

Текущий `vv` entrypoint остаётся `cli_v2`, но теперь он подключает `animal_audio_sources_v5`.

## Cat production / YouTube CC

Первый production-safe YouTube CC источник остаётся `I_pdwiLlvuc` / Kawaiipets / Creative Commons Attribution / 2160×3840 / audio -14.8 dB / clean gate PASS 0.99.

Не вводить обязательную YouTube quota. Pexels/Pixabay остаются основным автоматически скачиваемым safe fallback. Все rights / clean-footage / near-9:16 / audible-audio gates сохраняются.

## Review-first conveyor

Команды:

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Поведение: strict manifest order; existing ready MP4 = resumable completion marker; state in `runtime/conveyor/state.json`; AI plan-on-demand + MPT; cats use fresh licensed source acquisition + all quality/history gates; stop on first failure; outputs only `runtime/ready_for_review`; no publishing; hard `$10` OpenAI guard.

MPT manager prefers local MPT `.venv/venv` Python and does not require `uv`; if MPT was already running, conveyor leaves it alone.

## Upload metadata

Successful new renders produce `.upload.json` with proposed title/description, language/pipeline/video path, required attribution, `review_required=true`, `auto_publish=false`, `publication_allowed_by_conveyor=false`.

Cat external title family: `Cats That Made My Day 😹 #NNN #shorts`; on-card identity remains `#NNN — Cats`. AI title is derived from the actual fact plan.

## CI

Latest code-head test job after paginated sourcing + failed-audit resume:

```text
99 passed in 0.65s
Verify pilot lock: success
```

Windows-bootstrap for that exact head was still running at the time of the check; do not claim full workflow green without a new live check.

## Immediate next local step

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Expected local tests around **99 passed**. Slot 6 should recover the two fresh sources from its previous failed audit, exclude every prior rendered cat source ID while collecting, and paginate deeper for the remaining clips.

If slot 6 still cannot reach 5 usable sources, inspect the new `runtime/slots/06/animal_audio_sources.json` diagnostics before changing policy. Do not weaken rights/audio/aspect/clean/history gates; next escalation would be smarter source-provider expansion or larger pagination/search caps, not heavy source reuse.

Draft PR #1 remains open/draft and unmerged.
