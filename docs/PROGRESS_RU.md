# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний показанный OpenAI ledger: **$0.0340 / $10.00**.
- Slot 1 RU AI Short = manual QUALITY PASS.
- Cat renderer = local FFmpeg; real meow + Impact; no voiceover/BGM.
- Generic slot 2 `#001 — Котики` пользователь оценил как **нормальный**.
- Vertical gate локально подтверждён: 6/6 selected Pexels sources = **720x1280 / aspect 0.5625**.

## Старый CC discovery — исчерпан

Пользователь дважды запустил старый metadata-only CC search:

```text
vv-cat-youtube cc-search
Verified CC cat candidates: 0

vv-cat-youtube cc-search --days 6000 --limit 15 --scan-per-query 20
Verified CC cat candidates: 0
```

Вывод: расширение окна не помогает. Причина архитектурная: поле `license` у yt-dlp необязательное, поэтому отсутствие поля нельзя трактовать как доказательство Standard license.

## YouTube CC search v2 — IMPLEMENTED

Новый production entry point всё ещё:

```powershell
vv-cat-youtube
```

но `pyproject.toml` теперь маршрутизирует его в:

```text
src/vv_knopka/youtube_cat_source_v2.py
```

### `cc-search` v2

Использует **YouTube Creative Commons advanced-search filter** через настоящий YouTube search URL (`sp=`), который поддерживается `YoutubeSearchURLIE` в актуальном yt-dlp.

Flow:

```text
YouTube CC search filter
-> filtered video IDs
-> full yt-dlp metadata hydration
-> explicit Standard license => reject
-> direct CC license => accept (metadata+filter evidence)
-> empty license field => accept only because candidate came from YouTube CC filter
-> report
```

Команда:

```powershell
vv-cat-youtube cc-search
```

Defaults: 6000 days, 20 scan/query, top 15; queries include funny cat shorts / cats being cats / funny kittens shorts / cat fails shorts.

Report:

```text
runtime/trends/youtube-cat-cc-filtered.json
```

Report diagnostics per query:

- `filtered_results`
- `hydrated`
- `accepted`
- exact `search_url`

Это позволит понять причину даже если результат снова `0`.

### `cc-import`

Импорт теперь предпочтительно идёт **по rank из сохранённого CC-filter report**, а не по произвольному URL:

```powershell
vv-cat-youtube cc-import 2 --candidate N
```

Перед download снова проверяются video ID и текущие metadata. Если текущие metadata явно говорят Standard/non-CC, импорт fail-closed даже при старом filter evidence.

Успешный candidate далее проходит:

```text
yt-dlp download
-> near-9:16 ffprobe gate
-> duration gate
-> audible-audio gate
-> production sources.json
-> attribution.json
```

Pexels/Pixabay затем могут заполнить оставшиеся позиции до target 6.

Строгий старый URL mode `vv-cat-youtube cc 2 --url ...` сохранён для случаев, когда yt-dlp прямо сообщает CC license.

## Ordinary YouTube — test-only path остаётся

Обычные/unverified YouTube clips автоматически не считаются разрешёнными. Уже локальный exact file можно добавить только в изолированный pool:

```powershell
vv-cat-youtube test-add 2 --url "https://youtube..." --file "D:\path\cat.mp4" --confirm-match
vv-cat-youtube test-render 2
```

Storage/output только under `runtime/test_only/slot-02/`; `do_not_publish=true`, `publication_allowed=false`, `commercial_use_allowed=false`, `rights_verified=false`. Не попадает в production sources или `ready_for_review`.

## Tests / CI

Новый v2 добавил regression tests на:

- наличие YouTube CC filter в search URL;
- пустой yt-dlp `license` допускается только при CC-filter provenance;
- explicit Standard license reject;
- CC report provenance обязателен;
- import recheck rejects current explicit non-CC.

GitHub CI `test` job на code head `2e56412...`: **58 passed in 0.49s**, `Verify pilot lock` = success. Windows bootstrap на последней проверке ещё выполнялся отдельно.

## Следующая точка на ПК

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-youtube.exe cc-search
```

Ожидаемый local test count: **58 passed**.

Если кандидаты есть — прислать top list и выбрать `N`, затем:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate N
```

Если снова `0`, прислать:

```powershell
Get-Content .\runtime\trends\youtube-cat-cc-filtered.json -Raw
```

Нельзя merge Draft PR #1 без отдельного решения после визуального review.
