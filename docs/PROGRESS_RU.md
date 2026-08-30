# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний показанный OpenAI ledger: **$0.0340 / $10.00**.
- Slot 1 RU AI Short = manual QUALITY PASS.
- Cat renderer = local FFmpeg; real meow + Impact; no voiceover/BGM.
- Generic slot 2 `#001 — Котики` пользователь оценил как нормальный.
- Vertical gate локально подтверждён: 6/6 selected Pexels sources = **720x1280 / aspect 0.5625**.

## YouTube Creative Commons — текущий путь

Pexels работает, но footage может выглядеть слишком stock-like. Текущая цель — найти более живых/смешных котов через YouTube Creative Commons и оставить Pexels/Pixabay fallback.

Старые no-key попытки через optional yt-dlp `license` дали 0 кандидатов даже на 6000 дней; этот путь больше не является основным.

### Google Cloud / YouTube Data API — ТЕПЕРЬ ДОСТУПЕН

Пользователь смог:

- войти в Google Cloud Console;
- выбрать проект `VV Knopka`;
- включить YouTube Data API v3;
- создать API key без необходимости OAuth/channel login;
- сохранить ключ локально в `.env` как `YOUTUBE_API_KEY`.

Ключ никогда не коммитить и не просить вставлять в чат.

## `vv-cat-youtube` v3 — официальный API preferred

`pyproject.toml` теперь маршрутизирует:

```text
vv-cat-youtube = vv_knopka.youtube_cat_source_v3:main
```

Если `YOUTUBE_API_KEY` присутствует, `cc-search` автоматически использует официальный YouTube Data API:

```text
search.list with videoLicense=creativeCommon
-> videos.list details
-> status.license == creativeCommon
-> ranked CC candidates
-> runtime/trends/youtube-cat-cc-official.json
```

Команда:

```powershell
vv-cat-youtube cc-search
```

Defaults: 6000 days, scan-per-query 30 (API max capped at 50), limit 15, default query `cat|kitten`.

Это публичные metadata-запросы; OAuth/channel access не нужен. Если ключ отсутствует или указать `--no-key`, остаётся no-key YouTube CC-filter fallback.

### Safe official import

После выбора кандидата:

```powershell
vv-cat-youtube cc-import 2 --candidate N
```

Для official API report импорт перед download ещё раз вызывает `videos.list` и требует текущий:

```text
status.license == creativeCommon
```

Только после этого:

```text
yt-dlp download
-> near-9:16 ffprobe gate
-> duration >= clip_seconds
-> audible audio gate
-> production sources.json
-> attribution.json
```

Rights metadata сохраняет `rights_verified=true`, `rights_verification_method=youtube_data_api_status_license`, attribution и `api_status_license=creativeCommon`.

## Test-only ordinary YouTube остаётся изолированным

Стандартные/unverified YouTube clips не становятся production-safe. Уже локальный exact file можно использовать только через:

```powershell
vv-cat-youtube test-add 2 --url "https://youtube..." --file "D:\path\cat.mp4" --confirm-match
vv-cat-youtube test-render 2
```

Storage only `runtime/test_only/slot-02/`; обязательны `do_not_publish=true`, `publication_allowed=false`, `commercial_use_allowed=false`, `rights_verified=false`.

## Tests / CI

Official API v3 добавил regression coverage для:

- API discovery/dedupe;
- official `creativeCommon` evidence in report;
- report provenance gate;
- API key required for recheck before import.

GitHub CI `test` job on code head `042ae76...`: **62 passed in 0.41s**, `Verify pilot lock` = success. Windows bootstrap выполнялся отдельно на последней проверке.

## Следующая точка на ПК

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-youtube.exe cc-search
```

Ожидаемый console prefix при корректно подхваченном ключе:

```text
YouTube CC search: official YouTube Data API (videoLicense=creativeCommon)
Public metadata only; no OAuth, no channel login, no media download
```

Если API вернёт кандидатов — прислать top list и выбрать N. Если ошибка 403/400 — прислать текст ошибки без ключа.

Draft PR #1 не merge без отдельного решения после visual review.
