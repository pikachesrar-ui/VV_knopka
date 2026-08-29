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
- последний показанный OpenAI ledger: `$0.0281 / $10.00`;
- slot 1 octopus = manual QUALITY PASS;
- real user meow asset теперь успешно используется;
- audible-source gate slot 2 нашёл 6/6 usable Pexels clips с реальным signal audio.

## 3. AI short architecture

Terra plan -> Pexels/Pixabay -> Luna relevance gate -> local stock -> MPT -> Edge TTS/subtitles -> review.

Основные fixes: final `videos`, anchor cache, stock-friendly subjects, landscape blur-fill, Cyrillic subtitles, size 52 / position 74%, no per-clip fade.

## 4. Cat pipeline — текущий формат

Продуктовые решения:

- no voiceover;
- no BGM;
- real meow on cards;
- intro short (~0.9s);
- transitions more visible (~0.75s);
- end ~1.0s;
- intro + transitions repeat one `#NNN — title`;
- end = RU `Спасибо за просмотр` / EN `Thanks for watching`;
- cat clips clean, without overlay text;
- original clip audio retained/normalized;
- at least 5 unique audible licensed clips, target 6;
- long-run languages 80% EN / 20% RU without duplicate translations.

`Daily Dose of Cats` and close imitation must not be used.

## 5. Latest title-card failure and fix

После увеличения title и добавления badge пользователь увидел RU title как квадратные glyph boxes. `#001` рендерился нормально.

Root cause: decorative Windows fallback мог выбрать font без Cyrillic glyph coverage (например Arial Rounded/Impact-style choice).

Fix: в `config/pilot.toml` для Windows pilot pin:

```text
C:\Windows\Fonts\seguibl.ttf
```

Это **Segoe UI Black**. Microsoft Typography документирует у Segoe UI поддержку Cyrillic, а filename Black style = `seguibl.ttf`.

Current sizes:
- intro 84;
- transition 78;
- end 82;
- wrap ~18 chars;
- `#NNN` white badge;
- each title line centered separately.

На Linux CI Windows font path отсутствует и renderer использует system fallback.

## 6. Real meow resolver

Resolver поддерживает:

- `.env` `CAT_MEOW_FILE`;
- config `meow_file`;
- `.mp3/.wav/.m4a/.aac/.ogg/.flac/.opus`;
- friendly filenames `cat-transition-meow`, `cat-meow`, `meow`;
- любой audio file с `meow` в имени в `runtime/assets`.

Renderer печатает фактически выбранный path:

```text
Cat meow asset: ...
```

Пользователь подтвердил, что его звук теперь подставляется.

## 7. Audible stock gate — confirmed

Из user-provided `animal_audio_sources.json`:

- required minimum 5;
- target 6;
- selected 6;
- Pexels candidates 60;
- Luna approved 54;
- audio accepted 6;
- Pixabay 0;
- many files rejected as no audio/effectively silent;
- accepted signal mean roughly `-54.5..-12.2 dB`.

То есть source-audio gate работает, но все accepted sources = Pexels, поэтому footage всё ещё ощущается stock-like.

## 8. Current/viral cat discovery — НОВОЕ

Пользователь хочет больше актуального UGC / popular cat footage, а не только stock libraries.

Архитектура остаётся:

```text
trend discovery -> candidate queue -> rights/human gate -> controlled import -> Luna/audio/highlight gates -> renderer
```

Не делать raw TikTok/Instagram scraper default-путём.

### YouTube Creative Commons discovery реализован

Новый module:

```text
src/vv_knopka/trend_discovery.py
```

Новый console command:

```powershell
vv-cat-trends --days 30 --limit 30
```

Требует локальный `.env`:

```text
YOUTUBE_API_KEY=...
```

Search filters:

- `type=video`;
- `videoLicense=creativeCommon`;
- `videoDuration=short`;
- `publishedAfter` recent window;
- API search order `viewCount`;
- after video statistics fetch rank by `views/day` to favor fast recent growth.

Report:

```text
runtime/trends/youtube-cat-cc.json
```

Candidate metadata includes URL, video id, title, channel, published date, views, likes, duration, license, attribution-required flag and import status.

**No automatic download yet**. `auto_download=false`, `manual_review_required`.

Reasons:
- YouTube API exposes metadata, not media file;
- CC helps rights but requires attribution;
- YouTube reused-content policy is separate from copyright and expects substantive original transformation;
- broad TikTok Query Videos belongs to Research Tools for qualifying research; normal Display API reads authorized creator videos, not global trend search.

Next implementation after candidate quality review: controlled import of a user-approved/licensed local file into our provenance manifest. That file then passes the same audio + Luna + highlight checks as stock.

## 9. YouTube monetization constraint

YouTube explicitly treats minimally transformed compilations from other social websites as reused-content risk, even where permission exists. Therefore viral UGC must not become raw repost compilation. Keep meaningful editing/editorial identity and human review.

## 10. Next local checkpoint

Because `vv-cat-trends` is a new console entry point, run once:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

Expected log:

```text
Cat card font: C:\Windows\Fonts\seguibl.ttf
Cat meow asset: <real user asset>
```

Review:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

After confirming Cyrillic title, optionally configure YouTube Data API v3 key and test:

```powershell
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Then inspect `runtime/trends/youtube-cat-cc.json` before building any ingest/download step.
