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
- один YouTube channel;
- OpenAI hard budget = `$10`;
- `auto_publish=false`, human review обязателен;
- outputs только в `runtime/ready_for_review`.

## 2. Локальная среда / подтверждено

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- OpenAI/Pexels/Pixabay keys локально в `.env`;
- MPT используется для `ai_short`, но **не для cat pipeline**;
- cat renderer = local FFmpeg;
- последний подтверждённый local test run: **36 passed**;
- publication gate = **PASS**;
- последний показанный OpenAI ledger: **$0.0340 / $10.00**;
- slot 1 octopus = manual QUALITY PASS;
- real user meow asset успешно используется;
- audible-source gate slot 2 нашёл 6/6 usable Pexels clips с real signal audio;
- **Impact title-card style одобрен пользователем и считается принятым checkpoint**.

## 3. AI short architecture

Terra plan -> Pexels/Pixabay -> Luna relevance gate -> local stock -> MPT -> Edge TTS/subtitles -> review.

Основные fixes: final `videos`, anchor cache, stock-friendly subjects, landscape blur-fill, Cyrillic subtitles, size 52 / position 74%, no per-clip fade.

## 4. Cat pipeline — текущий формат

Продуктовые решения:

- no voiceover;
- no BGM;
- real meow on cards;
- intro short (~0.9s);
- transitions ~0.75s;
- end ~1.0s;
- intro + transitions repeat one `#NNN — title`;
- end = RU `Спасибо за просмотр` / EN `Thanks for watching`;
- cat clips clean, without overlay text;
- original clip audio retained/normalized;
- at least 5 unique audible licensed clips, target 6;
- long-run languages 80% EN / 20% RU without duplicate translations.

`Daily Dose of Cats` and close imitation must not be used.

## 5. Title-card style — APPROVED

Windows pilot pin:

```text
C:\Windows\Fonts\impact.ttf
```

Current sizes:
- intro 84;
- transition 78;
- end 82;
- wrap ~18 chars;
- `#NNN` white badge;
- each title line centered separately.

Impact визуально принят пользователем. Не возвращаться к font experiments без новой явной причины.

## 6. Real meow resolver

Resolver поддерживает `.env` `CAT_MEOW_FILE`, config `meow_file`, несколько audio extensions и friendly meow filenames в `runtime/assets`.

Renderer печатает:

```text
Cat meow asset: ...
```

Пользователь подтвердил, что его реальный звук теперь подставляется.

## 7. Audible stock gate — confirmed

Из user-provided `animal_audio_sources.json`:

- required minimum 5;
- target 6;
- selected 6;
- Pexels candidates 60;
- Luna approved 54;
- audio accepted 6;
- Pixabay 0;
- accepted signal mean roughly `-54.5..-12.2 dB`.

Gate работает, но все accepted = Pexels, поэтому footage всё ещё stock-like.

## 8. Current/viral cat discovery — IMPLEMENTED

Архитектура:

```text
trend discovery -> candidate queue -> human/rights gate -> controlled local import -> audio/Luna/highlight gates -> renderer
```

### YouTube Creative Commons discovery

Module:

```text
src/vv_knopka/trend_discovery.py
```

CLI:

```powershell
vv-cat-trends --days 30 --limit 30
```

Requires:

```text
YOUTUBE_API_KEY=...
```

Discovery v2:

- YouTube Data API;
- default query `cat|kitten`;
- topic `Pets` (`/m/068hy`);
- `videoLicense=creativeCommon`;
- `videoDuration=short`;
- recent `publishedAfter`;
- API order `viewCount`;
- then local sort by **views/day**;
- output `runtime/trends/youtube-cat-cc.json`;
- CLI prints top-10 ranked candidates `[01]`, `[02]`, etc.;
- candidate metadata: URL, video id, title, channel, publish time, views, likes, duration, CC attribution status.

No media auto-download.

## 9. Controlled UGC import — IMPLEMENTED

Module:

```text
src/vv_knopka/trend_import.py
```

CLI example:

```powershell
vv-cat-import 2 --candidate 3 --file "D:\Downloads\cat.mp4" --confirm-match
```

Behavior:

- `--candidate` = 1-based rank from latest `youtube-cat-cc.json`;
- explicit `--confirm-match` is mandatory: human confirms local file is exactly selected source;
- automatic rights mapping currently only for report candidates marked YouTube Creative Commons Attribution;
- verifies local file exists;
- verifies duration >= configured cat clip duration;
- verifies real audible audio using same `volumedetect` gate;
- computes SHA-256;
- copies into `runtime/imports/slot-XX/`;
- writes provider/source/title/creator/CC BY license/metrics-at-discovery;
- flags `ugc=true`, `human_approved=true`, `attribution_required=true`;
- creates attribution string;
- prepends UGC source into `runtime/slots/XX/sources.json` so UGC gets priority over Pexels;
- creates `runtime/slots/XX/attribution.json`;
- next `render-animal` reuses imported UGC first and stock only fills remaining positions to target 6;
- source manifest change invalidates old highlight signature, so Luna reselects highlights for the new mix.

New console entry point in `pyproject.toml`:

```text
vv-cat-import
```

## 10. Rights / monetization constraint

Keep discovery separate from ingest.

- YouTube Creative Commons upload = Creative Commons Attribution / CC BY-style reuse with attribution required.
- CC rights do **not** solve YouTube reused-content monetization policy by themselves.
- Minimal compilations / social reposts remain monetization risk even with permission.
- Current workflow therefore keeps `auto_download=false`, explicit human match confirmation, provenance, attribution and substantive editing/highlight selection.
- Do not make raw TikTok/Instagram scraper a default source. Broad TikTok query is not a normal production API path.

## 11. Current blocker / next local checkpoint

User already ran after the new UGC tools:

```text
36 passed
OpenAI spent: $0.0340 / $10.00
auto_publish: False
publication gate: PASS
```

First discovery attempt produced only:

```text
YOUTUBE_API_KEY is not set. Add a YouTube Data API v3 key to .env before running trend discovery.
```

So current blocker is **only missing YouTube Data API v3 key**.

Next steps:

1. Google Cloud: create/select project.
2. Enable **YouTube Data API v3**.
3. Create standard API key and restrict the key to YouTube Data API v3.
4. Add locally to `.env`:

```text
YOUTUBE_API_KEY=...
```

Never paste the key into chat or commit `.env`.

Then run:

```powershell
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Inspect terminal top-10 and/or:

```text
runtime/trends/youtube-cat-cc.json
```

If candidate N is actually useful, obtain exactly that CC source file locally and:

```powershell
.\.venv\Scripts\vv-cat-import.exe 2 --candidate N --file "D:\path\cat.mp4" --confirm-match
.\.venv\Scripts\vv.exe render-animal 2
```

Then inspect:

```text
runtime/slots/02/sources.json
runtime/slots/02/attribution.json
runtime/slots/02/highlights.json
runtime/ready_for_review/slot-02-ru-animals.mp4
```

Goal of next review: determine whether current/UGC candidate quality materially removes the Pexels-stock feel while preserving rights/provenance and source audio. Do not merge Draft PR #1 until relevant pilot quality checkpoint is explicitly approved.
