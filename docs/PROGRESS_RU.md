# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-30**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний локальный test run: **39 passed**.
- Последний показанный OpenAI ledger: **$0.0340 / $10.00**.
- Slot 1 RU AI Short — manual QUALITY PASS.
- Cat pipeline = local FFmpeg; MPT нужен только `ai_short`.
- Real user meow успешно подхватывается.
- **Impact title-card style принят пользователем; шрифт не менять без новой причины.**

## Slot 2 cats

Audible-source gate подтверждён: 6/6 usable Pexels clips с настоящим signal audio, но все они stock, поэтому текущий фокус = более живой UGC/trend sourcing.

Принятый cat format:

- Impact `C:\Windows\Fonts\impact.ttf`;
- intro ~0.9s, transitions ~0.75s, end ~1.0s;
- one `#NNN — title` on intro/transitions;
- localized thanks end card;
- real meow;
- no voiceover, no BGM;
- original clip audio retained/normalized;
- long-run languages 80% EN / 20% RU, no duplicate translations.

## Google Cloud больше НЕ blocker

Пользователю не подходит Google Cloud с адресом/картой. `YOUTUBE_API_KEY` не обязателен. Default no-key backend = `yt-dlp`; без OAuth/account login/media download.

## No-key trend discovery — runtime incidents и текущий fix

### Incident 1: удалённый `ytsearchdate`

Первый no-key запуск упал:

```text
Unsupported url scheme: "ytsearchdate90"
```

Актуальный yt-dlp удалил `ytsearchdate`; исправлено на обычный `ytsearchN:` + локальный recent filter.

### Incident 2: ordinary `ytsearch` дал 0 candidates

После первого compatibility fix пользователь подтвердил:

```text
39 passed
OpenAI spent: $0.0340 / $10.00
auto_publish: False
publication gate: PASS
Trend backend: yt-dlp (no Google Cloud, no API key, no account login)
YouTube cat trend candidates: 0 (CC already identified: 0)
```

Причина: search использовал `extract_flat="in_playlist"`. Плоские YouTube search entries часто не содержат `timestamp/upload_date`; `_candidate_from_ytdlp_entry` fail-closed отбрасывал entries без даты, поэтому поиск сам работал, но все результаты исчезали на локальном фильтре.

Текущий fix:

1. flat `ytsearch` используется только для быстрого сбора ID/URL;
2. затем до 50 уникальных кандидатов получают **full yt-dlp metadata lookup без download**;
3. только после hydration применяются date/duration/views/license checks;
4. default discovery расширен несколькими запросами с текущим годом:
   - `cat shorts 2026`;
   - `funny cat shorts 2026`;
   - `kitten shorts 2026`;
   - `viral cat shorts 2026`;
   - `cat shorts`;
5. recency = локальный `timestamp/upload_date` filter;
6. duration = 5..180 sec;
7. rank = views/day, затем total views;
8. rights остаются fail-closed: explicit CC -> `[CC]`, unknown -> `[rights?]` trend-reference-only.

Добавлены regression tests на multi-query current-year search и hydration URL из flat video id. Следующий local pytest после pull ожидается **41 passed**.

Report остаётся:

```text
runtime/trends/youtube-cat-cc.json
```

## Controlled UGC import

`vv-cat-import` работает с no-key report. Unverified candidate при import получает full yt-dlp license lookup; если Creative Commons всё ещё не подтверждён — import refuses. Затем duration/audio/SHA-256/provenance/attribution gates; UGC prepends `sources.json`, Pexels только дозаполняет remaining slots; highlights invalidated automatically.

## Следующая точка на ПК

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Discovery теперь печатает:

```text
Scanning YouTube search results and hydrating metadata; this can take a minute...
```

Это нормально: metadata hydration делает дополнительные read-only YouTube requests, но media не скачивает. После запуска прислать top-10 или exact error. Если и hydrated YouTube search не даст полезной выдачи, следующий fallback — Reddit/community discovery без Google Cloud.
