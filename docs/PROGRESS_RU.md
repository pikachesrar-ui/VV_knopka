# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила остаются в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-28**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish = false`, publication gate = `PASS`.
- OpenAI/Pexels/Pixabay keys настроены локально в `.env`.
- MoneyPrinterTurbo v1.3.5 установлен, API работает на `127.0.0.1:8080`.
- До cat-highlight v2 последний локальный pytest пользователя: **19 passed in 0.17s**.

## Slot 1 — Russian AI Short: QUALITY PASS

Тема: «Почему осьминог меняет цвет во сне».

Исправлено: final video вместо silent intermediate, Pexels+Pixabay+Luna relevance gate, duration fallback, нормальный Cyrillic font, landscape blur-fill, no per-clip FadeIn.

После просмотра пользователь сообщил: **«Этот результат мне нравится»**.

Актуальные subtitles для AI Shorts:

- font size **52**;
- vertical position **74%**;
- stroke 2.2;
- Windows Cyrillic local font для RU.

## Slot 2 — первый cats montage: REVIEW FAIL

Пользователь успешно сделал `plan 2 --topic cats` и `render-animal 2`.

Первый результат:

- cats действительно релевантны;
- 6 licensed Pexels/Pixabay источников собраны;
- 9:16 layout выглядит приемлемо;
- но ролик практически **без звука**;
- монтаж выглядит как случайные первые 5 секунд каждого source, а не как отобранные highlights.

Лог подтвердил причину тишины: большинство stock videos не имеют audio stream. Renderer создавал `anullsrc`, поэтому final MP4 технически содержал AAC stream, но почти весь он был silence (final audio bitrate около 2 kb/s).

Пользователь попросил:

- добавить нормальный звук;
- сделать выбор моментов интереснее;
- вместо неприятного bass-impact использовать приятный **meow** на переходах.

## Cat compilation v2 — текущий фикс

Добавлен `animal_highlights.py`.

Новый workflow при `render-animal 2`:

1. Уже найденные licensed cat sources можно переиспользовать; заново искать котов не требуется.
2. Из каждого исходника локально делаются до 4 candidate windows по всей длине клипа, а не только с начала.
3. Каждый candidate представлен 3-frame contact sheet.
4. Один GPT-5.6 Luna vision call выбирает для каждого source наиболее cute/funny/action-focused ~5 sec window.
5. Luna также:
   - переставляет 6 clips, чтобы strongest hook был первым;
   - пишет короткую RU caption (<=5 слов) именно по выбранному видимому моменту.
6. Результат кэшируется в `runtime/slots/02/highlights.json`; повторный render с тем же `sources.json` не должен снова платить за highlight review.
7. FFmpeg renderer использует выбранные `start` timestamps и порядок из `highlights.json`.
8. Captions burn-in поверх видео локальным Cyrillic-capable system font.

### Sound design v2

- source audio сохраняется и нормализуется там, где он реально есть;
- silent stock больше не означает silent final video;
- VV_knopka локально процедурно генерирует тихий playful bell-like background bed;
- на каждом cut локально генерируется короткий мягкий **synthetic meow**, причём чередуются 3 pitch variants;
- никакие внешние audio assets не скачиваются и copyright/provenance для этих synthetic sounds не нужен;
- никаких bass/drop/impact/boom частотных ударов;
- final audio = source audio + quiet BGM + meow transition timeline через FFmpeg `amix` + limiter.

Текущие config values:

- animal clip = 5 sec;
- 6 clips, минимум 5 unique;
- caption size = 58, y = 76%;
- source audio volume = 0.75;
- procedural BGM volume = 0.55;
- meow volume = 0.75;
- highlight vision max estimated call = $0.05 внутри общего hard cap $10.

Добавлены tests на:

- highlight candidate starts covering beginning/middle/end;
- short clip fallback;
- procedural BGM/meow WAV действительно non-silent stereo 48 kHz;
- sources manifest сохраняет duration.

## Slot 3 — English AI Short

Пока **поставлен на паузу по просьбе пользователя**, пока доводим cats pipeline.

Первый старый plan выбрал stock-poor `superb lyrebird`; planner уже исправлен на stock-friendly broad animals + anchor-aware stale cache. Но новый English render пока не является текущим приоритетом.

## Точная следующая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

`plan 2` повторно запускать НЕ нужно.
`sources.json` удалять НЕ нужно.

Первый v2 render создаст:

- `runtime/slots/02/highlight_previews/*.jpg`;
- `runtime/slots/02/highlights.json`;
- procedural audio внутри `runtime/tmp/slot-02-ru-animals/`;
- итог `runtime/ready_for_review/slot-02-ru-animals.mp4`.

Проверить руками:

- слышно тихую музыку даже на silent stock;
- source sound слышен там, где он есть;
- meow на cuts приятный и не слишком громкий/частый;
- выбранные моменты действительно содержат action/reaction, а не случайное начало;
- порядок clips ощущается намеренным;
- captions относятся к происходящему и не мешают просмотру.

Только после ручного quality review решать, что ещё менять. Auto-publish остаётся OFF.
