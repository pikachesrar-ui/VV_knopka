# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- Frozen pilot полностью отрендерен: **15/15**.
- Пользователь после просмотра сообщил, что всё нормально; conveyor quality считается принятой для перехода к long-run validation.
- Финальный явно показанный pilot ledger:

```text
OpenAI spent: $0.1786 / $10.00
auto_publish: False
publication gate: PASS
```

## Long-run — IMPLEMENTED, ещё не запускался реально на ПК пользователя

Long-run не расширяет конечный pilot manifest. После slot 15 `resolve_slot()` детерминированно вычисляет post-pilot slots без верхней границы.

Current schedule config:

```toml
[long_run]
enabled = true
pipeline_cycle = ["animal_compilation", "ai_short"]
ai_language = "en"
fact_subject_cooldown = 6
```

Cat cycle:

```toml
language_cycle = ["en", "en", "en", "en", "ru"]
```

Long-run cat cycle стартует заново после pilot, поэтому первые будущие targets:

```text
16 cats EN (#008)
17 AI EN
18 cats EN (#009)
19 AI EN
20 cats EN (#010)
21 AI EN
22 cats EN (#011)
23 AI EN
24 cats RU (#012)
```

## New CLI

```powershell
.\.venv\Scripts\vv.exe longrun-next --dry-run
.\.venv\Scripts\vv.exe longrun-next
.\.venv\Scripts\vv.exe longrun-batch --count N
```

`long_run_conveyor.py` использует те же review-first locks и `pilot_conveyor` render primitives, но имеет отдельный attempt state:

```text
runtime/long_run/state.json
```

Existing non-empty long-run ready MP4 = resume marker. Batch всегда выбирает первые missing deterministic long-run slots и stop-on-first-failure.

## AI subject cooldown — IMPLEMENTED

`recent_visual_anchors()` идёт назад по `runtime/slots/XX/plan.json` и возвращает последние distinct AI subjects. Planner исключает последние 6 anchors из stock-friendly subject list.

Это решает замеченное в metadata review слишком быстрое возвращение одного животного, но не создаёт вечный blacklist: после выхода из окна subject снова доступен.

## Cat metadata variation — IMPLEMENTED

Pilot sidecars не меняются. Для slot 16+:

- title numbering продолжается после pilot (#008+);
- EN/RU title family сохраняется;
- description детерминированно выбирается из нескольких коротких вариантов;
- `review_required=true`, `auto_publish=false`, `publication_allowed_by_conveyor=false` сохраняются.

## Cat source history — IMPLEMENTED beyond slot 15

Prior cat history теперь определяется по реальным `ready_for_review/slot-*-*-animals.mp4`, а не конечному списку pilot animal slots. Поэтому source IDs из будущих episodes тоже входят в history exclusion/reuse audit.

Core gates не ослаблены: provenance/commercial-use, near-9:16, audible-source, vision relevance, minimum 5 unique, final heavy-reuse fail-closed.

## YouTube acquisition wording

YouTube API metadata/CC declaration и clean-footage gate являются discovery/technical evidence, а не доказательством chain-of-title или platform-compliant acquisition. Long-run automated acquisition должна предпочитать Pexels/Pixabay или independently authorized downloadable files. Не называть yt-dlp official/API-compliant download path.

## Tests / CI

При первом CI старый `test_openai_planner.py` импортировал удалённое internal имя `_previous_visual_anchors`; test обновлён на `recent_visual_anchors`.

Последний завершённый code test-job:

```text
108 passed in 0.55s
publication gate: PASS
long_run: True
```

CI теперь дополнительно запускает:

```text
vv longrun-next --dry-run
```

и на Ubuntu, и в Windows bootstrap job. Recheck exact latest HEAD workflow before claiming both jobs green after docs-only commits.

## Immediate next local validation

Не ставить Scheduler пока не проверен хотя бы один реальный long-run slot.

Пользователю выполнить:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe longrun-next --dry-run
```

Ожидание:

```text
slot 16: animal_compilation / en -> D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.mp4
```

Если именно так:

```powershell
.\.venv\Scripts\vv.exe longrun-next
```

После успешного slot 16: визуально проверить MP4 + `.upload.json`; затем можно реализовывать/настраивать Windows Task Scheduler. Publication остаётся manual/review-first.

Draft PR #1 remains open/draft/unmerged.
