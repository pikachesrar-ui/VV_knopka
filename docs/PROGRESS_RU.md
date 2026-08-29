# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-29**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний локальный test run: **36 passed**.
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

Поэтому `YOUTUBE_API_KEY` теперь **не обязателен**.

### `vv-cat-trends` backend v3

Default `--backend auto`:

- если `YOUTUBE_API_KEY` уже есть — можно использовать официальный API backend;
- если ключа нет — автоматически используется **yt-dlp no-key discovery**;
- не нужен Google Cloud, карта, адрес, OAuth или login в YouTube account;
- media не скачивается;
- search = `ytsearchdate...`, затем local recent/duration filtering и rank by views/day;
- candidate metadata: title, creator/channel, publish time, views, duration, optional `license` metadata;
- report: `runtime/trends/youtube-cat-cc.json`.

No-key rights policy fail-closed:

- если yt-dlp metadata явно говорит Creative Commons -> candidate `creative_commons_attribution_required`;
- если license отсутствует/неясна -> `license_unverified` и candidate только trend reference;
- неизвестная лицензия **не считается разрешением на монтаж**.

Dependency added:

```text
yt-dlp>=2026.1,<2027
```

## Controlled UGC import

`vv-cat-import` теперь может работать с no-key report.

При import:

1. пользователь подтверждает exact file/candidate через `--confirm-match`;
2. если report не доказал CC, yt-dlp повторно делает full metadata lookup выбранного YouTube URL без download;
3. import разрешён только если license реально определяется как Creative Commons;
4. затем проверяются duration + audible audio;
5. SHA-256/provenance/attribution сохраняются;
6. UGC prepends `sources.json`, Pexels только дозаполняет remaining slots;
7. highlights автоматически invalidated by manifest change.

Никакого автоматического скачивания arbitrary social videos по умолчанию.

## Rights / monetization

Creative Commons помогает с copyright rights, но YouTube reused-content policy остаётся отдельной. Minimal repost compilations остаются monetization risk, поэтому human review + montage/editorial identity сохраняются.

## Следующая точка на ПК

Google Cloud больше не настраивать.

После pull нужен reinstall, потому что добавлен `yt-dlp` dependency:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Ожидаемый старт:

```text
Trend backend: yt-dlp (no Google Cloud, no API key, no account login)
```

Затем прислать top-10 output. Если no-key YouTube search окажется нестабилен/заблокирован, следующий fallback — отдельный Reddit RSS trend discovery (RSS работает без API key), но сначала тестируем YouTube yt-dlp.
