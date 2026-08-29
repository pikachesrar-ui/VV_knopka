# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл хранит продуктовые решения и точку продолжения.

Последнее содержательное обновление: **2026-08-30**.

## 1. Frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.
Рабочая ветка: `mvp/pilot-scaffold`.
Draft PR #1 открыт, не merge без отдельного решения пользователя.

Pilot: 15 Shorts; 8 × `ai_short`; 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cat test, остальные 13 EN; one channel; OpenAI hard budget `$10`; `auto_publish=false`; human review; outputs only `runtime/ready_for_review`.

## 2. Локально подтверждено

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- OpenAI/Pexels/Pixabay keys local `.env`;
- MPT only for `ai_short`; cats = local FFmpeg;
- latest user test: **39 passed**;
- publication gate **PASS**;
- latest OpenAI ledger **$0.0340 / $10.00**;
- slot 1 octopus manual QUALITY PASS;
- real user meow works;
- slot 2 audible gate found 6/6 Pexels clips with real audio;
- **Impact title-card style approved**.

## 3. Cat format — approved checkpoint

- no voiceover / no BGM;
- real meow on black cards;
- intro ~0.9s, transitions ~0.75s, end ~1.0s;
- intro + transitions repeat one `#NNN — title`;
- localized thanks end card;
- clean cat clips, original source audio retained/normalized;
- minimum 5 unique audible licensed clips, target 6;
- long-run `en,en,en,en,ru` = 80/20 originals, no translated duplicates;
- Windows card font pinned to `C:\Windows\Fonts\impact.ttf`, sizes 84/78/82;
- never use `Daily Dose of Cats` or close imitation.

## 4. Why UGC/trend sourcing exists

Pexels audible gate works, but footage still looks stock-like. User wants current/popular cat clips closer to TikTok/Shorts/UGC aesthetics.

Architecture:

```text
trend discovery -> candidate queue -> rights/human gate -> controlled local import -> audio/Luna/highlight gates -> renderer
```

Do NOT default to raw social scraper/repost.

## 5. Google Cloud rejected by user

Initial discovery required `YOUTUBE_API_KEY`. User tried Google Cloud but it asked for address/card and explicitly said this does not suit them.

Decision: **Google Cloud/API key is not required/default. Do not tell user to add billing/card/address.**

Dependency:

```text
yt-dlp>=2026.1,<2027
```

CLI:

```powershell
vv-cat-trends --days 30 --limit 30
```

`--backend auto|ytdlp|api`; `auto` uses API only if key already exists, otherwise yt-dlp no-key; no OAuth/account login/media download.

## 6. No-key discovery runtime history

### Compatibility incident: `ytsearchdate`

First no-key run failed with:

```text
Unsupported url scheme: "ytsearchdate90"
```

Current yt-dlp removed `ytsearchdate`; fixed to ordinary `ytsearchN:`. Regression test prevents return of `ytsearchdate`.

### Zero-candidate incident after compatibility fix

User then ran:

```text
39 passed in 0.59s
OpenAI spent: $0.0340 / $10.00
auto_publish: False
publication gate: PASS
Trend backend: yt-dlp (no Google Cloud, no API key, no account login)
YouTube cat trend candidates: 0 (CC already identified: 0)
```

This was not a YouTube/network error. Root cause: no-key search used `extract_flat="in_playlist"`, and flat search entries often omit `timestamp/upload_date`. Our fail-closed recency filter rejects entries without a trusted date, so all candidates disappeared.

## 7. Current no-key discovery implementation — HYDRATED v4

`discover_ytdlp_cats()` now has two stages:

1. **Flat discovery** — ordinary `ytsearchN:` collects IDs/URLs cheaply, no media download.
2. **Full metadata hydration** — up to 50 unique candidate URLs get `yt-dlp extract_info(..., download=False)` so we can reliably inspect date/duration/views/license.

Default query family (when CLI query left default), generated with current year:

```text
cat shorts 2026
funny cat shorts 2026
kitten shorts 2026
viral cat shorts 2026
cat shorts
```

Reason: ordinary YouTube search is relevance-oriented, so one generic query can mostly return old viral content; current-year variants improve recall before local recency filtering.

After hydration:

- require publication inside requested lookback (`--days`, default 30);
- duration 5..180 sec;
- compute views/day from full metadata;
- rank views/day then total views;
- store title, creator/channel, date, views, likes, duration, URL and optional license;
- explicit Creative Commons -> `[CC]`;
- missing/unknown license -> `[rights?]`, trend-reference-only;
- unknown license is never permission to use.

CLI prints before hydration:

```text
Scanning YouTube search results and hydrating metadata; this can take a minute...
```

No media is downloaded by discovery.

Report remains:

```text
runtime/trends/youtube-cat-cc.json
```

Two new regression tests cover:

- multi-query current-year default discovery;
- conversion of flat YouTube video ID into a watch URL suitable for full metadata hydration.

Expected next local test count after pull: **41 passed**.

## 8. Controlled UGC import

CLI:

```powershell
vv-cat-import 2 --candidate N --file "D:\path\cat.mp4" --confirm-match
```

No auto social downloader.

Import behavior:

1. exact local file/candidate confirmation required;
2. if report has explicit CC, continue;
3. if `license_unverified`, full yt-dlp metadata lookup of selected URL with `download=False`;
4. if CC still unverified -> refuse;
5. if verified -> duration + audible audio gate;
6. SHA-256, provenance and attribution saved;
7. copy to `runtime/imports/slot-XX/`;
8. prepend UGC to `sources.json`, Pexels fills remaining slots;
9. source manifest change invalidates highlights, so Luna reselects.

Attribution report: `runtime/slots/02/attribution.json`.

## 9. Rights / monetization constraint

Creative Commons/permission does not solve YouTube reused-content monetization by itself. Minimal social compilations remain risky, so keep substantive montage/editorial identity, provenance and human review.

## 10. Next local checkpoint

Run:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Expected test count: around **41 passed**.

Expected discovery start:

```text
Trend backend: yt-dlp (no Google Cloud, no API key, no account login)
Scanning YouTube search results and hydrating metadata; this can take a minute...
```

Ask user for top-10 output or exact error. If hydrated YouTube still gives no useful recent candidates, next fallback should be a separate community/trend discovery source (e.g. Reddit no-key feed/search), while keeping rights import fail-closed. Do not merge Draft PR #1 until explicit pilot quality approval.
