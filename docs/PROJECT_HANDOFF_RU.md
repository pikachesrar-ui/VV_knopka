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

## Текущая фаза — long-run local validation

Long-run реализован отдельно от конечного pilot manifest, но сохраняет глобальную slot-нумерацию. Первый post-pilot slot = 16.

Current schedule:

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

## Первый реальный long-run запуск

На ПК пользователя после pull/install/tests:

```text
108 passed in 0.99s
OpenAI spent: $0.1786 / $10.00
auto_publish: False
publication gate: PASS
long_run: True
slot 16: animal_compilation / en -> ...slot-16-en-animals.mp4
```

Реальный `vv longrun-next` корректно начал slot 16, но sourcing остановился fail-closed:

```text
Vertical audible-source gate found only 1/5 usable cat clips
```

Это не CLI/renderer bug. Причина — старое правило source history навсегда исключало все IDs из семи pilot cat episodes. Для бесконечного режима finite Pexels/Pixabay vertical+audible pool при таком правиле неизбежно истощается.

## Long-run cat source cooldown — текущий fix

Новая политика не ослабляет license/audio/aspect/vision/minimum-count gates.

- Frozen pilot сохраняет исходную all-history защиту.
- Long-run: source блокируется, если он использовался в **любом из последних 5 rendered cat episodes**.
- После выхода из этого окна source снова eligible как fallback.
- Если его снова используют, cooldown начинается заново автоматически, потому что новый ready episode попадает в artifact history.
- Never-used stock имеет приоритет над cooled-down reuse.
- Последние 5 cat episodes остаются полностью защищены на этапе sourcing.
- Final reuse audit проверяет protected recent window и отдельно записывает `reused_cooled_down_sources`.

Для slot 16 / cat #008 это означает: источники cat #003–#007 защищены; достаточно старые sources из #001/#002 могут вернуться только если свежего stock не хватает.

Config:

```toml
[long_run]
cat_source_cooldown_episodes = 5
```

`animal_audio_sources_v4.py` теперь разделяет remote candidates на never-used и cooled-down historical. Сначала сканирует/ранжирует fresh; cooled-down stock заполняет остаток candidate pool только как fallback. Confirmed-silent remote media по-прежнему отбрасывается до Luna.

`animal_audio_sources_v5.py` recovery также использует active protected window, поэтому валидированный local stock из failed attempt можно восстановить, если он не является recent-blocked.

## Остальной long-run функционал

Commands:

```powershell
.\.venv\Scripts\vv.exe longrun-next --dry-run
.\.venv\Scripts\vv.exe longrun-next
.\.venv\Scripts\vv.exe longrun-batch --count 3
```

- тот же `$10` hard budget guard;
- `auto_publish=false` / human review;
- AI slot: plan-on-demand -> MPT -> ready output;
- cat slot: licensed sourcing -> gates -> FFmpeg -> ready output;
- stop on first failure;
- existing non-empty MP4 = resume marker;
- attempt history: `runtime/long_run/state.json`.

AI fact subject cooldown = последние 6 distinct visual anchors. Long-run cat descriptions имеют deterministic safe variation. Cat numbering продолжается с #008.

## YouTube / acquisition wording

YouTube Data API = discovery/reference/license metadata, не media-download endpoint. Uploader-declared CC не доказывает chain-of-title и не разрешает любой способ acquisition. Технический clean/geometry/audio PASS не называть доказательством platform compliance.

Long-run automated production должен предпочитать Pexels/Pixabay, owned/creator-supplied или independently authorized downloadable files. yt-dlp capability != official YouTube/API permission.

## Tests / CI

Code-head `487ccd6946c2a3e5ed405f6619f904e02d3dd7bf` полностью прошёл CI:

```text
111 passed in 0.70s
publication gate: PASS
long_run: True
vv longrun-next --dry-run -> slot 16 EN cats
```

Workflow run `33323215094` завершён `success`, включая Ubuntu test и Windows bootstrap. Docs commits после code-head двигают branch HEAD, поэтому этот exact CI относится к указанному code commit.

## Immediate local continuation

На ПК пользователя не удалять `runtime/slots/16`: один уже найденный fresh clip из failed audit полезен для recovery.

После pull:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe longrun-next --dry-run
```

Ожидание: около **111 passed**, dry-run всё ещё slot 16 EN cats.

Затем retry одного slot:

```powershell
.\.venv\Scripts\vv.exe longrun-next
```

Если slot 16 SUCCESS, проверить MP4 + `source_reuse_audit.json`; затем можно переходить к Windows Task Scheduler. YouTube uploader/OAuth остаётся отдельной фазой; публикация пока manual/review-first.

## Git

PR #1 остаётся draft/open/unmerged. Не merge без отдельного решения пользователя.
