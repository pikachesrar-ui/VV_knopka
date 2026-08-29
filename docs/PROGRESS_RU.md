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

## Последний визуальный review

Новый badge `#001` выглядит нормально, но русская строка превратилась в квадраты. Причина: предыдущий decorative font fallback выбрал font без Cyrillic glyphs.

### Fix в ветке

Для Windows pilot теперь явно закреплён:

```text
C:\Windows\Fonts\seguibl.ttf
```

Это **Segoe UI Black**; Microsoft документирует у Segoe UI поддержку Cyrillic. На Linux CI этого пути нет, поэтому renderer использует системный fallback.

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

Из-за нового console entry point один раз переустановить editable package:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

Проверить в логе:

```text
Cat card font: C:\Windows\Fonts\seguibl.ttf
Cat meow asset: <реальный файл пользователя>
```

Review output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

После подтверждения текста можно включать trend discovery. Если `YOUTUBE_API_KEY` уже есть:

```powershell
.\.venv\Scripts\vv-cat-trends.exe --days 30 --limit 30
```

Если ключа нет — сначала создать обычный YouTube Data API v3 key в Google Cloud; никаких новых платных media providers в pilot не добавлять.
