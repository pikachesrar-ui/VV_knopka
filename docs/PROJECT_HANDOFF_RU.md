# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя.

## Pilot — завершён и принят

Frozen pilot: 15 Shorts, 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные EN.

Пользователь завершил все 15 ready outputs и после просмотра сообщил, что всё нормально. Pilot не надо перегенерировать ради последующих metadata refinements.

Последний явно показанный локальный статус после полного pilot:

```text
OpenAI spent: $0.1786 / $10.00
auto_publish: False
publication gate: PASS
```

## Текущая фаза — long-run local validation

После успешного pilot пользователь дал команду переходить к постоянной генерации.

Long-run реализован отдельно от конечного pilot manifest, но сохраняет глобальную slot-нумерацию. Первый post-pilot slot = 16.

Текущий deterministic schedule:

```text
16 cats EN  -> cat episode #008
17 facts EN
18 cats EN  -> #009
19 facts EN
20 cats EN  -> #010
21 facts EN
22 cats EN  -> #011
23 facts EN
24 cats RU  -> #012
...
```

Pipeline cycle configurable через `[long_run].pipeline_cycle`, сейчас `animal_compilation, ai_short`. AI language сейчас EN. Cat long-run language cycle начинает новый цикл после pilot: `en,en,en,en,ru`.

## Новые команды

```powershell
.\.venv\Scripts\vv.exe longrun-next --dry-run
.\.venv\Scripts\vv.exe longrun-next
.\.venv\Scripts\vv.exe longrun-batch --count 3
```

`longrun-next/batch`:

- используют тот же `$10` hard budget guard;
- сохраняют `auto_publish=false` / human review;
- AI slot: plan-on-demand -> MPT -> ready output;
- cat slot: history-aware licensed sourcing -> gates -> FFmpeg -> ready output;
- stop on first failure;
- existing non-empty MP4 = resume marker;
- attempt history: `runtime/long_run/state.json`;
- child CLI остаётся `cli_v2`, поэтому актуальная cat-source v5 policy сохраняется.

## Fact subject cooldown

`openai_client.recent_visual_anchors()` читает `plan.json` предыдущих AI slots в обратном порядке.

Config:

```toml
[long_run]
fact_subject_cooldown = 6
```

Автоматический planner исключает последние 6 distinct `visual_anchor` из доступного stock-friendly subject list. Это не вечный ban: старое животное снова становится доступно после выхода из cooldown window. Explicit `--topic` пользователя по-прежнему имеет приоритет.

## Cat numbering / language / description

- Pilot cat episodes остаются #001–#007.
- Long-run начинается с #008.
- Episode numbering больше не зависит от того, что slot находится в конечном `content.animal_slots`.
- Long-run cat language вычисляется детерминированно по отдельному long-run cat ordinal.
- Pilot descriptions остаются byte-stable.
- Long-run cat descriptions выбираются детерминированно из небольшого безопасного набора вариантов, чтобы не создавать сотни одинаковых описаний.

## Cat source history теперь unbounded

`source_history.py` больше не ограничивает prior history списком pilot animal slots. Он обнаруживает реально существующие:

```text
runtime/ready_for_review/slot-*-*-animals.mp4
```

и читает соответствующие `runtime/slots/XX/sources.json`. Поэтому источники из slot 16+ также блокируются от тяжёлого повторного reuse.

Все существующие quality gates сохраняются: provenance/commercial use, near-9:16, audible audio, Luna relevance, minimum 5 unique clips, final max-one-incidental-repeat gate.

## YouTube / acquisition wording

YouTube Data API = discovery/reference/license metadata, не media-download endpoint. Uploader-declared CC не доказывает chain-of-title и не разрешает любой способ acquisition. Технический clean/geometry/audio PASS не называть доказательством platform compliance.

Long-run automated production должен предпочитать Pexels/Pixabay, owned/creator-supplied или independently authorized downloadable files. yt-dlp capability != official YouTube/API permission.

## CI

Первый CI после переименования cooldown helper поймал только старый test-import; test обновлён.

Последний завершённый code test-job после long-run implementation:

```text
108 passed in 0.55s
OpenAI spent in CI: $0.0000 / $10.00
auto_publish: False
publication gate: PASS
long_run: True
```

CI workflow также обновлён, чтобы запускать `vv longrun-next --dry-run` на Ubuntu и Windows. После docs commits HEAD двигается; всегда recheck live перед утверждением полного workflow status.

## Immediate local continuation

После того как пользователь подтянет branch:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe longrun-next --dry-run
```

Ожидаемый dry-run:

```text
slot 16: animal_compilation / en -> ...slot-16-en-animals.mp4
```

Если dry-run правильный, следующий тест — **ровно один** реальный:

```powershell
.\.venv\Scripts\vv.exe longrun-next
```

Проверить slot 16 визуально и sidecar. Только после успешного реального long-run slot переходить к Windows Task Scheduler. YouTube uploader/OAuth остаётся отдельной фазой; публикация пока ручная.

## Git

PR #1 остаётся draft/open/unmerged. Название PR обновлено под pilot + long-run phase. Не merge без отдельного решения пользователя.
