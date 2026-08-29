# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл хранит продуктовые решения и точку продолжения.

Последнее содержательное обновление: **2026-08-29**.

## 1. Frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.
Рабочая ветка: `mvp/pilot-scaffold`.
Draft PR #1 открыт, не merge без отдельного решения пользователя.

Pilot:
- 15 Shorts;
- 8 × `ai_short`;
- 7 × `animal_compilation`;
- slot 1 = RU AI Short;
- slot 2 = RU cat compilation test;
- остальные 13 = EN;
- one YouTube channel;
- OpenAI hard budget `$10`;
- `auto_publish=false`, human review required;
- outputs only `runtime/ready_for_review`.

## 2. Локально подтверждено

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- OpenAI/Pexels/Pixabay keys local `.env`;
- MPT only for `ai_short`; cat renderer local FFmpeg;
- latest local tests before no-key backend edit: **36 passed**;
- publication gate **PASS**;
- latest shown OpenAI ledger **$0.0340 / $10.00**;
- slot 1 octopus manual QUALITY PASS;
- user real meow works;
- slot 2 audible gate found 6/6 Pexels clips with real audio;
- **Impact title-card style approved**.

## 3. AI short architecture

Terra plan -> Pexels/Pixabay -> Luna relevance gate -> local stock -> MPT -> Edge TTS/subtitles -> review.

Important fixes: final MPT `videos`, anchor cache, stock-friendly subjects, landscape blur-fill, Cyrillic subtitles size 52 / position 74%, no per-clip fade.

## 4. Cat format — approved checkpoint

- no voiceover;
- no BGM;
- real meow on black cards;
- intro ~0.9s;
- transitions ~0.75s;
- end ~1.0s;
- intro + transitions repeat one `#NNN — title`;
- localized `Спасибо за просмотр` / `Thanks for watching` end card;
- cat clips clean, no overlay text;
- source audio retained/normalized;
- minimum 5 unique audible licensed clips, target 6;
- long-run languages `en,en,en,en,ru` = 80/20 originals, no RU/EN duplicate publication.

Never use `Daily Dose of Cats` or close imitation.

### Card style

Windows pin:

```text
C:\Windows\Fonts\impact.ttf
```

Sizes: intro 84, transition 78, end 82, wrap ~18 chars, white `#NNN` badge. User said Impact is acceptable; do not restart font experiments without explicit reason.

## 5. Why UGC/trend sourcing was added

Pexels audible gate works, but accepted slot 2 material still feels stock-like. User wants current/popular cat clips closer to TikTok/Shorts/UGC aesthetics.

Architecture:

```text
trend discovery -> candidate queue -> rights/human gate -> controlled local import -> audio/Luna/highlight gates -> renderer
```

Do NOT default to raw social scraper/repost.

## 6. Google Cloud rejected by user

Initial `vv-cat-trends` used YouTube Data API and required `YOUTUBE_API_KEY`.

User ran:

```text
36 passed
OpenAI spent: $0.0340 / $10.00
auto_publish: False
publication gate: PASS
```

Then discovery stopped at missing `YOUTUBE_API_KEY`.

User attempted Google Cloud Console but it asked for address/card. User explicitly said this does not suit them.

**Decision: Google Cloud/API key is no longer required or the default path. Do not tell the user to add billing/card/address.**

## 7. No-key trend discovery — current implementation

`pyproject.toml` now includes:

```text
yt-dlp>=2026.1,<2027
```

CLI remains:

```powershell
vv-cat-trends --days 30 --limit 30
```

New option:

```text
--backend auto|ytdlp|api
```

Default `auto` behavior:

- if `YOUTUBE_API_KEY` exists, API backend may be used;
- otherwise automatically `yt-dlp` no-key backend;
- no Google Cloud;
- no card/address;
- no OAuth;
- no YouTube account login;
- no media download during discovery.

No-key discovery uses `ytsearchdateN:<query>` and scans more results than final limit, then filters:

- published inside requested lookback;
- duration 5..180 sec;
- rank by views/day, then total views;
- stores title, creator/channel, publish time, views, likes if present, duration, URL, optional license metadata.

Report remains:

```text
runtime/trends/youtube-cat-cc.json
```

### Rights handling is fail-closed

`yt-dlp` metadata field `license` is optional.

- explicit Creative Commons metadata -> `creative_commons_attribution_required`;
- missing/unknown license -> `license_unverified`;
- unverified item is trend-reference-only, not permission to use.

CLI top-10 shows `[CC]` or `[rights?]`.

If YouTube changes extraction and yt-dlp search fails, error asks to update environment/retry and specifically says not to log a personal YouTube account into this workflow.

Potential later fallback: Reddit RSS discovery (no API key), if YouTube no-key search proves too unstable.

## 8. Controlled UGC import — current implementation

CLI:

```powershell
vv-cat-import 2 --candidate N --file "D:\path\cat.mp4" --confirm-match
```

Still no auto social downloader.

Import behavior:

1. exact local file/candidate confirmation required;
2. YouTube candidates only for current automatic rights path;
3. if discovery already has explicit CC metadata, use it;
4. if candidate is `license_unverified`, import performs a full yt-dlp metadata lookup of the selected URL with `download=False`;
5. if license still cannot be verified as Creative Commons, import refuses;
6. if CC verified, check local duration + audible audio;
7. compute SHA-256;
8. copy to `runtime/imports/slot-XX/`;
9. save source title/creator/URL/license/metrics/provenance;
10. generate attribution string/report;
11. prepend UGC into `sources.json`; Pexels only fills remaining target slots;
12. changed source manifest invalidates old highlight signature so Luna reselects highlights.

Attribution report:

```text
runtime/slots/02/attribution.json
```

## 9. Rights / monetization constraint

Creative Commons/permission does not automatically solve YouTube reused-content monetization. Minimal social compilations remain risky, so keep substantive montage/editorial identity, provenance and human review.

## 10. Next local checkpoint

Because yt-dlp was added as dependency, user should run:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Expected first line from discovery without any key:

```text
Trend backend: yt-dlp (no Google Cloud, no API key, no account login)
```

Ask user to send the top-10 output. Goal: see whether no-key YouTube results materially reduce the Pexels-stock feel. If runtime extraction fails, debug exact yt-dlp output before adding another provider.

Do not merge Draft PR #1 until relevant pilot quality checkpoint is explicitly approved.
