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
- latest user test: **40 passed**;
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

Architecture intent:

```text
trend discovery -> candidate/reference queue -> rights/human gate -> controlled usable footage -> audio/Luna/highlight gates -> renderer
```

Do NOT default to raw social scraper/repost.

## 5. Google Cloud rejected by user

Initial discovery required `YOUTUBE_API_KEY`. User tried Google Cloud but it asked for address/card and explicitly said this does not suit them.

Decision: **Google Cloud/API key is not required/default. Do not tell user to add billing/card/address.**

## 6. YouTube no-key discovery — runtime history and verdict

Dependency:

```text
yt-dlp>=2026.1,<2027
```

CLI:

```powershell
vv-cat-trends --days 30 --limit 30
```

Backend is yt-dlp no-key by default when no API key exists; no OAuth/account login/media download.

Runtime fixes already made:

1. upstream removed broken `ytsearchdate` -> use ordinary `ytsearchN:`.
2. flat entries often lacked date -> two-stage discovery: flat ID/URL collection then full metadata hydration (`download=False`).
3. default query family includes current year:
   - `cat shorts 2026`;
   - `funny cat shorts 2026`;
   - `kitten shorts 2026`;
   - `viral cat shorts 2026`;
   - `cat shorts`.
4. local filters: requested recency, 5..180 sec, ranking by views/day then total views.
5. rights fail closed: explicit CC -> `[CC]`; missing/unknown -> `[rights?]` trend-reference-only.

Latest actual user output:

```text
40 passed in 0.81s
OpenAI spent: $0.0340 / $10.00
publication gate: PASS
YouTube cat trend candidates: 5 (CC already identified: 0)
```

Candidates:

1. `Where are the viral cats now?😭💔` — 55,255 views, ~6,956 views/day;
2. 23 views;
3. 7 views;
4. 5 views;
5. 2 views.

**0/5 Creative Commons confirmed.** Therefore YouTube no-key discovery technically works but quality is too weak as the only current-cat source. Do not waste time repeatedly tuning only ytsearch unless a concrete new idea appears.

Report:

```text
runtime/trends/youtube-cat-cc.json
```

## 7. Reddit/community trend discovery — IMPLEMENTED

Reason: use a different community signal for what cat content is actually current/popular, without Google Cloud/API keys.

New module:

```text
src/vv_knopka/reddit_trend_discovery.py
```

New CLI:

```powershell
vv-cat-community --days 30 --limit 30
```

Default communities:

```text
cats
WhatsWrongWithYourCat
OneOrangeBraincell
CatsAreAssholes
Catculations
Catswithjobs
```

Mechanics:

- reads public Reddit RSS only;
- no Reddit API key;
- no Reddit account login;
- scans both `top/week` and `hot` feeds;
- `www.reddit.com` first, `old.reddit.com` fallback;
- parses Atom with Python stdlib;
- filters by max age;
- `community_score` = feed rank signal × recency, accumulated if same post appears in multiple feeds;
- extracts obvious media links/hints when feed HTML exposes them (`v.redd.it`, mp4/webm, YouTube, Imgur/i.redd.it);
- individual feed errors/rate limits become `diagnostics`, not total failure;
- report:

```text
runtime/trends/reddit-cat-trends.json
```

Rights policy is deliberately closed:

```text
rights_status = author_permission_required
import_status = trend_reference_only_until_author_permission
auto_download = false
```

A public Reddit post is **not** treated as licensed reusable media. Reddit is currently an inspiration/trend/reference layer only.

Entry point added to `pyproject.toml`:

```text
vv-cat-community
```

Three new tests cover:

- public top/week RSS URL;
- Atom parsing + video media hint + permission-only rights;
- recency filtering.

Given previous 40 tests, expected local count after pull is around **43 passed**.

## 8. Controlled UGC import

CLI:

```powershell
vv-cat-import 2 --candidate N --file "D:\path\cat.mp4" --confirm-match
```

Current automatic import path remains YouTube-only and requires Creative Commons verification. Unverified YouTube candidate gets full yt-dlp metadata check; if CC still unverified -> refuse. Reddit candidates are **not** automatically importable; a separate creator-permission/provenance path would be needed before using their media.

## 9. Rights / monetization constraint

Creative Commons/permission does not solve YouTube reused-content monetization by itself. Minimal social compilations remain risky, so keep substantive montage/editorial identity, provenance and human review.

## 10. Next local checkpoint

Run:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-community.exe --days 30 --limit 30
```

Expected CLI start:

```text
Community backend: Reddit public RSS (no API key, no account login)
```

Ask user to send top community references and any `Feed warnings`. Goal: determine whether community trends are substantially more interesting/current than the weak YouTube no-key output. Then choose how to convert trend themes into footage with safe rights/provenance. Do not merge Draft PR #1 until explicit pilot quality approval.
