# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-29**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний показанный OpenAI ledger: **$0.0281 / $10.00**.
- Slot 1 Russian AI Short («Почему осьминог меняет цвет во сне») — manual QUALITY PASS.
- Cat/animal pipeline рендерится локально через FFmpeg; MoneyPrinterTurbo нужен только для `ai_short`.
- Пользовательский real meow теперь успешно подхватывается.
- **Impact title-card style принят пользователем; шрифт больше не менять без новой причины.**

## Slot 2 cats — audible sourcing подтверждён

Пользователь прислал `animal_audio_sources.json`:

- target = 6;
- selected = **6**;
- Pexels candidates = 60;
- Luna vision-approved = 54;
- audible accepted = 6;
- Pixabay не понадобился;
- десятки файлов reject как no audio / effectively silent;
- accepted mean volume примерно `-54.5..-12.2 dB`.

Audio-source gate работает как задумано.

## Title card — текущий принятый стиль

После экспериментов со шрифтами пользователь одобрил вариант с **Impact**.

Для Windows pilot закреплён:

```text
C:\Windows\Fonts\impact.ttf
```

Текущие card settings:

- intro title size 84;
- transition title 78;
- end 82;
- wrap ~18 chars;
- `#NNN` — отдельный white badge;
- строки центрируются отдельно;
- real meow используется на intro / transitions / end;
- no voiceover;
- no BGM.

Этот визуальный стиль считается принятым checkpoint; не возвращаться к Segoe/Arial Rounded без новой причины.

## Current/viral cat discovery — первый практический слой реализован

Добавлен `src/vv_knopka/trend_discovery.py` и CLI:

```powershell
vv-cat-trends --days 30 --limit 30
```

Нужен локальный `.env` key:

```text
YOUTUBE_API_KEY=...
```

Что делает discovery:

- YouTube Data API;
- только `type=video`;
- только `videoLicense=creativeCommon`;
- только `videoDuration=short`;
- только recent window (`publishedAfter`);
- search order = `viewCount`;
- после получения stats пересортировывает по **views/day**, чтобы свежий быстро растущий ролик поднимался выше;
- сохраняет author/channel, title, published_at, views, likes, duration, license и rights metadata;
- output: `runtime/trends/youtube-cat-cc.json`.

Важно: это пока **discovery only**. Auto-download = false, import_status = manual_review_required. Причины:

1. YouTube API даёт metadata, не media file;
2. Creative Commons помогает с source rights, но attribution обязателен;
3. YouTube reused-content policy отдельно требует substantive original editing/value;
4. TikTok global public search не подходит как обычный production API: Display API работает с authorized creator, broad Query Videos относится к Research Tools.

Следующий этап после просмотра списка candidates — сделать controlled `trend import`: выбранный/разрешённый файл добавляется в source manifest с attribution/provenance и затем проходит Luna/audio/highlight gates. Не делать raw social scraper default-путём.

## Языки

- без RU/EN дублей;
- long-run animal cadence: `en, en, en, en, ru`;
- frozen pilot: slot 2 RU, остальные animal slots EN.

## Следующая точка на ПК

Текущий визуальный стиль уже принят, поэтому следующий продуктовый этап — **актуальные/UGC коты**.

Если новый console entry point ещё не установлен локально:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
```

Если `YOUTUBE_API_KEY` уже есть:

```powershell
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Report:

```text
runtime/trends/youtube-cat-cc.json
```

После просмотра candidate quality решить controlled import. Никаких новых платных media providers в pilot без explicit решения пользователя.
