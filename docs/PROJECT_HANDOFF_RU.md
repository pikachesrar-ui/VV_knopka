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

После нескольких safe sourcing failures slot 16 EN cats / cat episode #008 успешно завершён на ПК пользователя:

```text
D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.mp4
Upload metadata: D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.upload.json
Long-run conveyor outputs:
D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.mp4
```

Это подтверждает post-pilot resume, rolling cat cooldown и cooled local-history fallback в реальном запуске.

Следующий deterministic target теперь:

```text
17 facts EN
```

Дальше schedule:

```text
18 cats EN  -> #009
19 facts EN
20 cats EN  -> #010
21 facts EN
22 cats EN  -> #011
23 facts EN
24 cats RU  -> #012
...
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
- Retry после minimum-count failure восстанавливает уже принятые local files из failed audit и не обязан повторять тот же remote discovery pass.
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

## Windows Task Scheduler — IMPLEMENTED, local install pending

Добавлены:

```text
scripts/run-longrun-task.ps1
scripts/install-longrun-task.ps1
```

`run-longrun-task.ps1`:

- запускает ровно один `longrun-next`;
- сначала выполняет `vv status`;
- пишет лог в `runtime/scheduler/longrun-task.log`;
- использует exclusive file lock, чтобы два scheduled run не рендерили одновременно;
- при ошибке возвращает nonzero и оставляет resume на том же missing slot;
- не делает `git pull`;
- не обновляет код;
- не публикует;
- `-DryRun` вызывает только `longrun-next --dry-run`.

`install-longrun-task.ps1`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1 -At "HH:mm"
```

- создаёт один DAILY task;
- работает под текущим interactive Windows user без запроса/хранения пароля;
- `StartWhenAvailable`;
- `MultipleInstances=IgnoreNew`;
- execution limit 4 hours;
- разрешён запуск на батарее и не останавливается при переходе на батарею;
- `-DryRun` ничего не регистрирует.

Не выбирать время за пользователя: перед реальной установкой он должен назвать желаемое локальное время.

## Tests / CI

Scheduler code checkpoint `1844ddf3c5f39734989b99cf5c3a05df04ae33d6`:

```text
114 passed
publication gate: PASS
long_run: True
```

Workflow run `33325562523` завершён `success`:

- Ubuntu test green;
- Windows bootstrap green;
- Windows scheduler runner dry-run green;
- Windows scheduler installer dry-run green.

Docs commits после этого checkpoint двигают branch HEAD; exact CI выше относится к указанному scheduler code commit.

## YouTube / acquisition wording

YouTube Data API = discovery/reference/license metadata, не media-download endpoint. Uploader-declared CC не доказывает chain-of-title и не разрешает любой способ acquisition. Технический clean/geometry/audio PASS не называть доказательством platform compliance.

Long-run automated production должен предпочитать Pexels/Pixabay, owned/creator-supplied или independently authorized downloadable files. yt-dlp capability != official YouTube/API permission.

## Immediate local continuation

После pull scheduler-кода:

```powershell
cd D:\KiraS\VV_knopka
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\run-longrun-task.ps1 -DryRun
```

Ожидание: safety status PASS и dry-run target = **slot 17 ai_short / en**. Рендериться в dry-run ничего не должно.

После этого пользователь выбирает время ежедневного запуска. Реальная установка:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1 -At "HH:mm"
```

Publishing остаётся manual/review-first; uploader/OAuth не добавлены.

## Git

PR #1 остаётся draft/open/unmerged. Не merge без отдельного решения пользователя.
