# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя.

## Pilot — завершён и принят

Frozen pilot: 15 Shorts, 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные EN.

Пользователь завершил все 15 ready outputs и после просмотра сообщил, что всё нормально. Pilot не надо перегенерировать ради последующих metadata refinements.

Финальный явно показанный pilot status:

```text
OpenAI spent: $0.1786 / $10.00
auto_publish: False
publication gate: PASS
```

## Long-run — первый реальный slot SUCCESS

Slot 16 EN cats / cat episode #008 успешно завершён на ПК пользователя:

```text
D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.mp4
Upload metadata: D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.upload.json
Long-run conveyor outputs:
D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.mp4
```

Следующий deterministic target = slot 17 `ai_short` / EN.

После scheduler runner dry-run пользователь показал:

```text
OpenAI spent: $0.1885 / $10.00
auto_publish: False
publication gate: PASS
long_run: True
slot 17: ai_short / en -> ...slot-17-en-ai.mp4
SUCCESS: scheduled longrun-next completed.
```

## Long-run cat source policy

Config:

```toml
[long_run]
cat_source_cooldown_episodes = 5
```

Политика:

- Frozen pilot сохраняет all-history protection.
- Long-run блокирует IDs последних 5 rendered cat episodes.
- Never-used remote stock ищется/ранжируется первым.
- Более старый source допустим как fallback; после reuse его cooldown начинается заново.
- Если fresh remote pass не достигает minimum count, система может seed локальные Pexels/Pixabay files из rendered episodes вне cooldown.
- Исторические local files заново проходят текущие near-9:16 и audible-audio gates.
- Retry после minimum-count failure восстанавливает уже принятые local files из failed audit.
- YouTube/прочие providers local-history fallback не импортирует.
- Final reuse audit отдельно показывает cooled-down historical reuse.

Все quality/safety gates остаются: provenance/commercial-use, near-9:16, audible source audio, Luna relevance, minimum 5 unique clips, fail-closed behavior.

## Long-run commands

```powershell
.\.venv\Scripts\vv.exe longrun-next --dry-run
.\.venv\Scripts\vv.exe longrun-next
.\.venv\Scripts\vv.exe longrun-batch --count 3
```

- `$10` hard OpenAI budget guard;
- `auto_publish=false` / human review;
- AI slot: plan-on-demand -> MPT -> ready output;
- cat slot: licensed sourcing -> gates -> FFmpeg -> ready output;
- stop on first failure;
- existing non-empty MP4 = resume marker;
- attempt history: `runtime/long_run/state.json`.

AI fact subject cooldown = последние 6 distinct visual anchors. Long-run cat descriptions имеют deterministic variation. Cat numbering продолжается с #008.

## Windows Task Scheduler — approved 3/night test

Пользователь хочет недельный тест с несколькими роликами и одобрил **до 3 generated videos/night**.

Chosen Moscow-time schedule:

```text
01:30 MSK
03:30 MSK
05:30 MSK
```

`run-longrun-task.ps1`:

- запускает ровно один `longrun-next` за каждый trigger;
- сначала выполняет `vv status`;
- пишет лог в `runtime/scheduler/longrun-task.log`;
- использует exclusive file lock;
- при ошибке возвращает nonzero и следующий trigger resume того же missing slot;
- не делает `git pull`, не обновляет код, не публикует;
- `-DryRun` вызывает только `longrun-next --dry-run`.

`install-longrun-task.ps1` теперь поддерживает **одну Windows Scheduled Task с несколькими daily triggers**.

Default install без `-At` = approved schedule 01:30,03:30,05:30:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1
```

Также сохраняется custom usage:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1 -At "12:00"
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1 -At "01:00,03:00,05:00"
```

Task behavior:

- current interactive Windows user, password not requested/stored;
- `StartWhenAvailable`;
- `MultipleInstances=IgnoreNew`;
- execution limit 4h;
- battery run allowed;
- because overlap is ignored, schedule means **up to 3 videos/day**, not forced parallel renders.

For a 7-day test maximum = 21 generated videos. Based on observed pilot/long-run OpenAI spend, planning estimate is roughly **$0.25–0.50 for the week**, while hard project cap remains $10.

## Tests / CI

Multi-trigger scheduler code commits:

```text
92145209f9bc68eba3fcbe5e7a2e27725cd2f036  installer
6838930aeba02441176d5fabd6bb9653697be48f  CI coverage
```

Ubuntu job for this checkpoint passed:

```text
114 passed in 0.64s
publication gate: PASS
long_run: True
```

Windows job includes dry-run validation for both the default 3-trigger plan and the legacy/custom single-trigger plan. Recheck workflow run `33326252717` live before claiming Windows completion.

## YouTube / acquisition wording

YouTube Data API = discovery/reference/license metadata, не media-download endpoint. Uploader-declared CC не доказывает chain-of-title и не разрешает любой способ acquisition. Технический clean/geometry/audio PASS не называть доказательством platform compliance.

Long-run automated production должен предпочитать Pexels/Pixabay, owned/creator-supplied или independently authorized downloadable files. yt-dlp capability != official YouTube/API permission.

## Immediate local continuation

Подтянуть latest scheduler installer:

```powershell
cd D:\KiraS\VV_knopka
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1 -DryRun
```

Dry-run должен показать три времени: `01:30, 03:30, 05:30` и ничего не зарегистрировать.

Если всё верно, реальная установка одной task с тремя triggers:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1
```

После установки проверить `Registered`, `State`, `Triggers: 3`, `Next run`, затем после первой ночи смотреть `runtime/scheduler/longrun-task.log` и новые files в `runtime/ready_for_review`.

Publishing остаётся manual/review-first; uploader/OAuth не добавлены.

## Git

PR #1 остаётся draft/open/unmerged. Не merge без отдельного решения пользователя.
