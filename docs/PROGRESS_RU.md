# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-29**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний локальный test run: **36 passed**.
- Последний показанный OpenAI ledger: **$0.0340 / $10.00**.
- Slot 1 Russian AI Short («Почему осьминог меняет цвет во сне») — manual QUALITY PASS.
- Cat/animal pipeline рендерится локально через FFmpeg; MoneyPrinterTurbo нужен только для `ai_short`.
- Пользовательский real meow успешно подхватывается.
- **Impact title-card style принят пользователем; шрифт больше не менять без новой причины.**

## Slot 2 cats — audible sourcing подтверждён

Пользователь прислал `animal_audio_sources.json`:

- target = 6;
- selected = **6**;
- Pexels candidates = 60;
- Luna vision-approved = 54;
- audible accepted = 6;
- Pixabay не понадобился;
- accepted mean volume примерно `-54.5..-12.2 dB`.

Audio-source gate работает, но все 6 accepted clips = Pexels, поэтому footage выглядит stock-like.

## Title card — принятый стиль

Windows pilot:

```text
C:\Windows\Fonts\impact.ttf
```

- intro title 84;
- transition title 78;
- end 82;
- wrap ~18 chars;
- `#NNN` — white badge;
- строки центрируются отдельно;
- real meow на intro / transitions / end;
- no voiceover;
- no BGM.

## Current/viral cat discovery — реализовано

CLI:

```powershell
vv-cat-trends --days 30 --limit 30
```

Нужен `.env`:

```text
YOUTUBE_API_KEY=...
```

Discovery v2:

- YouTube Data API;
- query default `cat|kitten`;
- topic `Pets` (`/m/068hy`);
- `videoLicense=creativeCommon`;
- `videoDuration=short`;
- recent `publishedAfter` window;
- API sort by `viewCount`, затем локальная сортировка по **views/day**;
- report: `runtime/trends/youtube-cat-cc.json`;
- CLI печатает top-10 с номерами `[01]`, `[02]`, ...;
- каждый candidate содержит creator/channel, publish time, views, likes, duration, CC rights metadata и attribution requirement.

## Controlled UGC import — реализовано

Новый CLI:

```powershell
vv-cat-import 2 --candidate 3 --file "D:\Downloads\cat.mp4" --confirm-match
```

Почему local-file step намеренный: YouTube Data API даёт metadata, а не media; default workflow не превращается в social downloader/scraper.

Import делает:

- требует explicit `--confirm-match`, что local file = именно выбранный candidate;
- пока auto-rights mapping принимает только YouTube Creative Commons Attribution candidates из нашего report;
- проверяет minimum clip duration;
- проверяет реальную audible audio дорожку тем же gate (`volumedetect`);
- SHA-256 файла;
- копирует в `runtime/imports/slot-XX/`;
- сохраняет title, creator, source URL, CC BY license, views/views-per-day-at-discovery;
- ставит `ugc=true`, `human_approved=true`, `attribution_required=true`;
- генерирует attribution string/report;
- prepends imported UGC в `runtime/slots/XX/sources.json`, поэтому он имеет приоритет над старым Pexels;
- stock source logic затем только дозаполняет оставшиеся места до target 6;
- изменение `sources.json` автоматически инвалидирует старый `highlights.json`, поэтому Luna выберет highlight заново для нового набора.

Attribution report:

```text
runtime/slots/02/attribution.json
```

## Rights / monetization policy

Discovery и ingest разделены намеренно.

- YouTube Creative Commons = attribution required.
- CC license помогает с copyright rights, но reused-content policy отдельна.
- Минимально изменённые compilations / social reposts остаются monetization risk.
- Поэтому `auto_download=false`, human review остаётся обязательным, а imported UGC должен проходить наш монтаж/highlight/audio pipeline.
- TikTok/Instagram не становились default auto-ingest: официальный broad TikTok search не подходит как обычный production API.

## Языки

- без RU/EN дублей;
- long-run animal cadence: `en, en, en, en, ru`;
- frozen pilot: slot 2 RU, остальные animal slots EN.

## Текущий blocker / следующая точка на ПК

Локальная установка entry points и тесты уже подтверждены:

```text
36 passed
publication gate: PASS
OpenAI spent: $0.0340 / $10.00
```

Первый `vv-cat-trends` остановился только потому, что **`YOUTUBE_API_KEY` ещё не настроен**.

Следующий шаг:

1. В Google Cloud создать/выбрать project.
2. Enable **YouTube Data API v3**.
3. Создать standard API key и ограничить его этой API.
4. Добавить в локальный `.env`:

```text
YOUTUBE_API_KEY=...
```

Секрет не коммитить и не присылать в чат.

После этого:

```powershell
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Если quality выдачи нормальная, выбрать candidate, получить именно этот CC source file локально и импортировать:

```powershell
.\.venv\Scripts\vv-cat-import.exe 2 --candidate 3 --file "D:\path\cat.mp4" --confirm-match
.\.venv\Scripts\vv.exe render-animal 2
```

После первого report/import проверить candidate quality, attribution и насколько UGC реально убирает ощущение Pexels-stock. Никаких новых платных media providers без explicit решения пользователя.
