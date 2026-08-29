# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-30**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний локальный test run: **40 passed**.
- Последний показанный OpenAI ledger: **$0.0340 / $10.00**.
- Slot 1 RU AI Short — manual QUALITY PASS.
- Cat pipeline = local FFmpeg; MPT нужен только `ai_short`.
- Real user meow успешно подхватывается.
- **Impact title-card style принят пользователем; шрифт не менять без новой причины.**

## Slot 2 cats

Audible-source gate подтверждён: 6/6 usable Pexels clips с настоящим signal audio, но footage выглядит stock-like. Текущий фокус = более живой UGC/trend sourcing.

Принятый cat format:

- Impact `C:\Windows\Fonts\impact.ttf`;
- intro ~0.9s, transitions ~0.75s, end ~1.0s;
- one `#NNN — title` on intro/transitions;
- localized thanks end card;
- real meow;
- no voiceover, no BGM;
- original clip audio retained/normalized;
- long-run languages 80% EN / 20% RU, no duplicate translations.

## Google Cloud не использовать

Пользователю не подходит Google Cloud с адресом/картой. `YOUTUBE_API_KEY` не обязателен. Default YouTube discovery = `yt-dlp` no-key, без OAuth/account login/media download.

## YouTube no-key discovery — работает, но quality слабая

История fixes:

1. `ytsearchdate` удалён upstream -> заменён обычным `ytsearchN:`.
2. flat search давал 0 из-за отсутствующих дат -> добавлена full metadata hydration без media download.
3. default search расширен current-year запросами (`cat/funny cat/kitten/viral cat shorts 2026`).

Последний реальный запуск пользователя:

```text
40 passed in 0.81s
OpenAI spent: $0.0340 / $10.00
publication gate: PASS
YouTube cat trend candidates: 5 (CC already identified: 0)
```

Top выдача:

- один кандидат ~55k views / ~6.9k views/day;
- остальные 4 имеют 23 / 7 / 5 / 2 views;
- **0/5 Creative Commons confirmed**;
- все кандидаты `rights?`, то есть trend-reference-only.

Вывод: технически YouTube no-key backend работает, но как единственный источник актуальных котов недостаточно качественный. Не тратить время на бесконечный tuning одного `ytsearch`.

Report:

```text
runtime/trends/youtube-cat-cc.json
```

## Reddit/community trend discovery — ДОБАВЛЕНО

Новый CLI:

```powershell
vv-cat-community --days 30 --limit 30
```

Module:

```text
src/vv_knopka/reddit_trend_discovery.py
```

Default communities:

- `r/cats`;
- `r/WhatsWrongWithYourCat`;
- `r/OneOrangeBraincell`;
- `r/CatsAreAssholes`;
- `r/Catculations`;
- `r/Catswithjobs`.

Discovery:

- public Reddit RSS only;
- no Reddit API key;
- no account login;
- `top/week` + `hot` feeds;
- `www.reddit.com` with `old.reddit.com` fallback;
- public feed rank + recency -> `community_score`;
- duplicate post seen in several feeds accumulates signal;
- extracts obvious media links/hints (`v.redd.it`, mp4/webm, YouTube, Imgur/i.redd.it) when RSS contains them;
- writes `runtime/trends/reddit-cat-trends.json`;
- failed/rate-limited feeds are stored in `diagnostics` instead of killing whole discovery.

Rights are intentionally fail-closed:

```text
rights_status = author_permission_required
import_status = trend_reference_only_until_author_permission
```

Public Reddit post **не означает** разрешение на reuse. Этот слой нужен, чтобы понять, какие cat themes/scenes/memes реально актуальны, и затем искать/получать footage с понятными правами.

Новый entry point в `pyproject.toml`:

```text
vv-cat-community
```

Добавлены 3 tests на RSS URL, Atom parsing/media hint и old-entry filtering. После pull ожидается около **43 passed**.

## Controlled UGC import

`vv-cat-import` пока принимает только YouTube-кандидаты, где Creative Commons реально подтверждён. Unverified -> full yt-dlp license check -> refuse если CC не доказан. Reddit автоматически в import не пускается без отдельного permission workflow.

## Следующая точка на ПК

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-community.exe --days 30 --limit 30
```

Прислать top community references и `Feed warnings`, если они будут. Goal: проверить, даёт ли Reddit заметно более живые/current cat ideas, чем YouTube no-key. После этого решать, как связывать trend reference с legally usable footage.
