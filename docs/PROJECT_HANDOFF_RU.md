# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл хранит продуктовые решения и точку продолжения.

Последнее содержательное обновление: **2026-08-29**.

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
- latest user test before compatibility fix: **38 passed**;
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

`pyproject.toml` now includes:

```text
yt-dlp>=2026.1,<2027
```

CLI:

```powershell
vv-cat-trends --days 30 --limit 30
```

`--backend auto|ytdlp|api`; `auto` uses API only if key already exists, otherwise yt-dlp no-key; no OAuth/account login/media download.

## 6. No-key discovery compatibility incident

First no-key run on user's current yt-dlp failed with:

```text
Unsupported url scheme: "ytsearchdate90"
```

Root cause verified from current upstream yt-dlp: `ytsearchdate` support was removed in Feb 2026 because it was broken. `ytsearchN:` remains supported.

Fix committed:

- new helper `_ytdlp_search_target()` returns `ytsearchN:<query>`;
- no-key discovery now scans ordinary search results and locally filters requested recency using `timestamp/upload_date`;
- duration 5..180 sec;
- rank by views/day, then total views;
- regression test asserts `ytsearchdate` is never generated.

Expected next local test count: **39 passed**.

Report:

```text
runtime/trends/youtube-cat-cc.json
```

Top-10 labels `[CC]` or `[rights?]`.

Rights fail closed:

- explicit Creative Commons metadata -> `creative_commons_attribution_required`;
- missing/unknown license -> `license_unverified`, trend-reference-only;
- unknown license is never permission to use.

## 7. Controlled UGC import

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

## 8. Rights / monetization constraint

Creative Commons/permission does not solve YouTube reused-content monetization by itself. Minimal social compilations remain risky, so keep substantive montage/editorial identity, provenance and human review.

## 9. Next local checkpoint

Run:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Expected backend line:

```text
Trend backend: yt-dlp (no Google Cloud, no API key, no account login)
```

Ask user for top-10 output. If ordinary `ytsearch` also fails, debug exact yt-dlp output first; fallback candidate is Reddit RSS no-key discovery. Do not merge Draft PR #1 until explicit pilot quality approval.
