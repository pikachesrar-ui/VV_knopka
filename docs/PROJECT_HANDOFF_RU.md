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

## Реальный slot 16 — два safe failures

На ПК пользователя long-run CLI/schedule подтверждены локально. Последний показанный retry:

```text
111 passed in 1.23s
vv longrun-next --dry-run -> slot 16 animal_compilation / en
vv longrun-next -> Vertical audible-source gate found only 1/5 usable cat clips
```

Rolling cooldown уже был активен, поэтому второй `1/5` уточнил root cause: просто разрешить старые IDs недостаточно. Pexels/Pixabay current search не обязан снова вернуть именно те старые IDs, которые уже использовались в ранних episodes.

Не удалять `runtime/slots/16`: там уже есть failed audit и один принятый fresh local clip.

## Long-run cat source policy — текущий fix

Config:

```toml
[long_run]
cat_source_cooldown_episodes = 5
```

Политика:

- Frozen pilot сохраняет all-history protection.
- Long-run блокирует source IDs из последних 5 rendered cat episodes.
- Более старый source становится eligible fallback; после reuse его cooldown начинается заново.
- Never-used remote stock ищется/ранжируется первым.
- Если fresh remote pass реально не достигает minimum count, система может использовать **локальные Pexels/Pixabay файлы из rendered episodes, вышедших из cooldown**.
- Исторический local file не считается автоматически годным: base pipeline повторно проверяет текущие near-9:16 и audible-audio gates.
- На retry после уже записанного minimum-count failure accepted clips восстанавливаются из `animal_audio_sources.json`, а cooled local history подмешивается сразу, чтобы не оплачивать бессмысленное повторение того же fresh discovery pass.
- На первом fresh failure fallback происходит в том же invocation: recover accepted -> seed cooled local -> rerun validators.
- YouTube/другие providers не подмешиваются этим fallback; только Pexels/Pixabay.
- Final reuse audit продолжает блокировать protected recent overlap и отдельно показывает cooled-down reuse.

Для slot 16 / cat #008 protected episodes = cat #003–#007; local files из cat #001/#002 могут использоваться как fallback. Один fresh clip slot16 остаётся первым кандидатом.

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

Code-head `91e2932e2d9e3e2868288584664fabb6f84bc3d9` после local-history fallback:

```text
114 passed in 0.69s
publication gate: PASS
long_run: True
vv longrun-next --dry-run -> slot 16 EN cats
```

Ubuntu test job green. На момент фиксации Windows bootstrap этого run ещё выполнялся; recheck live перед утверждением полного workflow success. Docs commits после code-head двигают branch HEAD.

Regression coverage дополнительно проверяет:

- cooled local history берётся только вне protected recent window;
- retry с existing `1/5` audit сначала сохраняет fresh clip, затем добавляет cooled local stock;
- первый fresh minimum failure может перейти к local-history fallback в том же invocation.

## Immediate local continuation

После pull не удалять `runtime/slots/16`.

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe longrun-next --dry-run
```

Ожидание: около **114 passed**, dry-run всё ещё slot 16 EN cats.

Затем:

```powershell
.\.venv\Scripts\vv.exe longrun-next
```

Для текущего slot16 retry система должна использовать existing failed audit, восстановить fresh local source, добавить cooled local Pexels/Pixabay из ранних episodes и повторно проверить их перед render.

Если slot 16 SUCCESS, проверить MP4 + `source_reuse_audit.json`; затем можно переходить к Windows Task Scheduler. YouTube uploader/OAuth остаётся отдельной фазой; публикация пока manual/review-first.

## Git

PR #1 остаётся draft/open/unmerged. Не merge без отдельного решения пользователя.
