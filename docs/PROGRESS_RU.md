# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-29**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний локальный test run: **38 passed**.
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

Пользователь сообщил, что Google Cloud Console требует адрес/карту; такой путь ему не подходит.

Поэтому `YOUTUBE_API_KEY` **не обязателен**.

### `vv-cat-trends` no-key backend

Default `--backend auto`:

- если `YOUTUBE_API_KEY` уже есть — можно использовать официальный API backend;
- если ключа нет — автоматически используется **yt-dlp no-key discovery**;
- не нужен Google Cloud, карта, адрес, OAuth или login в YouTube account;
- media не скачивается;
- обычный `ytsearchN:<query>`, затем local recent/duration filtering и rank by views/day;
- candidate metadata: title, creator/channel, publish time, views, duration, optional `license` metadata;
- report: `runtime/trends/youtube-cat-cc.json`.

### Runtime incident 2026-08-29

Первый no-key запуск упал:

```text
Unsupported url scheme: "ytsearchdate90"
```

Причина подтверждена по актуальному upstream yt-dlp: `ytsearchdate` был удалён как сломанный в феврале 2026. Обычный `ytsearch` остаётся поддерживаемым.

Fix в ветке:

- `ytsearchdateN:` -> `ytsearchN:`;
- свежесть больше не зависит от search extractor: даты фильтруются локально по `timestamp/upload_date`;
- добавлен regression-test, запрещающий `ytsearchdate`.

Следующий локальный pytest после `git pull` ожидается **39 passed** (до фикса пользователь подтвердил 38 passed).

No-key rights policy fail-closed:

- explicit Creative Commons -> `creative_commons_attribution_required`;
- license отсутствует/неясна -> `license_unverified`, только trend reference;
- неизвестная лицензия не считается разрешением на монтаж.

Dependency:

```text
yt-dlp>=2026.1,<2027
```

## Controlled UGC import

`vv-cat-import` работает с no-key report.

При import:

1. пользователь подтверждает exact file/candidate через `--confirm-match`;
2. если report не доказал CC, yt-dlp повторно делает full metadata lookup выбранного URL без download;
3. import разрешён только если license реально определяется как Creative Commons;
4. затем проверяются duration + audible audio;
5. SHA-256/provenance/attribution сохраняются;
6. UGC prepends `sources.json`, Pexels только дозаполняет remaining slots;
7. highlights автоматически invalidated by manifest change.

Никакого автоматического скачивания arbitrary social videos по умолчанию.

## Следующая точка на ПК

Google Cloud больше не настраивать.

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Ожидаемый backend:

```text
Trend backend: yt-dlp (no Google Cloud, no API key, no account login)
```

Затем прислать top-10 output. Если обычный `ytsearch` тоже окажется нестабилен, следующий fallback — отдельный Reddit RSS trend discovery без API key.
