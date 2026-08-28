# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл — для продуктовых решений и точки продолжения.

Последнее содержательное обновление: **2026-08-28**.

## 1. Frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.

Цель: review-first pipeline для 15 YouTube Shorts в нише **Animals / Nature Curiosities**.

Зафиксировано:

- 15 Shorts;
- 8 × `ai_short`;
- 7 × `animal_compilation`;
- slot 1 = русский AI Short;
- slot 2 = русская animal compilation;
- остальные 13 = English;
- пока один канал;
- OpenAI hard project budget = **$10**;
- `auto_publish=false`;
- human review обязателен;
- output только в `runtime/ready_for_review`;
- не добавлять новые платные providers без отдельного решения пользователя.

Animal compilations: никакого loud bass/drop/impact/boom; source/provenance и commercial-use eligibility обязательны; raw social repost pipeline запрещён как default.

## 2. Git workflow

- default branch: `main`;
- рабочая ветка: `mvp/pilot-scaffold`;
- draft PR #1;
- PR не merge без отдельного решения пользователя;
- новый чат сначала полностью читает `AGENT.md`, этот файл и `docs/PROGRESS_RU.md`, затем проверяет live GitHub state/CI.

## 3. Подтверждённая локальная среда

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- bootstrap PASS;
- publication gate PASS;
- OpenAI/Pexels/Pixabay keys локально в `.env`;
- MoneyPrinterTurbo v1.3.5 установлен в ignored `MoneyPrinterTurbo`;
- MPT API работает на `127.0.0.1:8080`;
- перед cat-highlight v2 последний локальный pytest пользователя: **19 passed in 0.17s**.

## 4. AI short architecture

Terra structured plan -> Pexels/Pixabay candidate search -> GPT-5.6 Luna image relevance gate -> approved local stock -> MPT local-material render -> Edge TTS/subtitles -> review output.

Quality/safety:

- final MPT `videos` вместо silent intermediate `combined_videos`;
- visual anchor обязателен, confidence >=0.72;
- narrow topics: минимум 3 approved sources + >=36 sec reusable footage;
- landscape -> 1080x1920 blur-fill;
- Russian subtitle font = local Windows Cyrillic font;
- актуальные AI subtitles: size 52, position 74%, stroke 2.2;
- MPT per-segment FadeIn выключен;
- material cache anchor-aware;
- auto-selected AI topics ограничены broad stock-friendly animals, чтобы не повторять ситуацию `superb lyrebird` 2/8.

## 5. Slot 1 — Russian AI Short: MANUAL QUALITY PASS

Тема: **«Почему осьминог меняет цвет во сне»**.

Исправлялись: silent final copy, unrelated stock, low source count, bad CJK Russian font, black bars, fade-from-black.

После финального просмотра пользователь сообщил: **«Этот результат мне нравится»**. Slot 1 = QUALITY PASS.

## 6. Slot 2 — Russian cats compilation: первый render REVIEW FAIL

Пользователь выполнил:

```powershell
.\.venv\Scripts\vv.exe plan 2 --topic cats
.\.venv\Scripts\vv.exe render-animal 2
```

Получено 6 релевантных licensed cat clips из Pexels/Pixabay. Visual aspect handling приемлем.

Human review выявил:

1. **практически нет звука**;
2. видео ощущается как random moments / первые 5 sec каждого source;
3. пользователь ожидал более интересную нарезку;
4. пользователь предложил приятный `meow` на переходах вместо раздражающего bass-impact.

Лог подтвердил audio root cause: большинство stock clips вообще не имеют audio stream. Старый renderer подставлял `anullsrc`, поэтому final AAC существовал технически, но почти весь был silence (около 2 kb/s audio bitrate).

## 7. Cat compilation v2 — текущая архитектура

### Highlight selection

Добавлен `src/vv_knopka/animal_highlights.py`.

`render-animal` теперь перед FFmpeg assembly:

- переиспользует уже найденный `sources.json`;
- для каждого source рассматривает до 4 time windows по всей длине;
- на каждый window локально делает 3-frame contact sheet;
- один GPT-5.6 Luna vision call выбирает наиболее cute/funny/action-focused ~5 sec segment каждого clip;
- Luna переставляет clips так, чтобы strongest hook был первым и дальше было разнообразие;
- Luna пишет короткую caption <=5 слов на языке slot, связанную с реально видимым моментом;
- результат кэшируется в `runtime/slots/02/highlights.json`;
- при неизменном `sources.json` повторный render не должен снова платить за highlight review.

Highlight review использует существующий `$10` ledger; max estimated one-call reservation = `$0.05`.

### Video edit

Animal renderer теперь:

- использует выбранный `start` timestamp, а не первые 5 sec;
- использует порядок из `highlights.json`;
- burning captions локально через Cyrillic-capable system font;
- сохраняет 9:16 blur-fill + sharp full foreground;
- tiny fades остаются только мягкими, без black/bass impacts.

### Sound design

Final animal audio теперь должен быть слышимым даже если stock немой:

- source audio сохраняется/нормализуется там, где существует;
- VV_knopka процедурно генерирует локальный тихий bell-like playful BGM;
- на каждом cut процедурно генерируется мягкий synthetic **meow**; чередуются 3 pitch variants;
- procedural audio полностью локален, не скачивает внешние assets и не создаёт copyright/licensing зависимости;
- final mix = source + BGM + meow timeline -> FFmpeg `amix` -> limiter -> AAC 192k;
- bass/drop/impact/boom по-прежнему запрещены.

Актуальный animal config:

- 6 clips, минимум 5 unique;
- 5 sec/clip;
- caption size 58, y=76%;
- source audio volume 0.75;
- BGM volume 0.55;
- meow volume 0.75;
- `transition_sfx = "soft_meow"`.

Если procedural meow human review не понравится, следующий шаг — заменить его одним реальным лицензированным meow sample, не меняя архитектуру.

## 8. Tests added for cat v2

Добавлены/обновлены tests:

- candidate starts покрывают beginning/middle/end, а не только t=0;
- short clip -> start 0 fallback;
- generated BGM is non-silent stereo 48k;
- generated meow timeline is non-silent stereo 48k;
- `sources.json` сохраняет source duration.

Точный итог pytest после этих новых commits ещё должен подтвердить пользователь/GitHub CI.

## 9. Slot 3 — English AI Short

Пока **на паузе по просьбе пользователя**, пока доводится cats pipeline.

Первый старый plan выбрал `superb lyrebird` и fail-closed 2/8. Planner уже исправлен на broad stock-friendly anchors и anchor-aware stale cache, но сейчас не продолжать English render до нового решения пользователя.

## 10. Точная текущая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

Важно:

- `plan 2` повторно НЕ нужен;
- `sources.json` НЕ удалять;
- первый cat v2 render создаст `highlight_previews/` + `highlights.json`, поэтому сделает один новый Luna highlight call;
- следующие rerenders с тем же source manifest должны переиспользовать highlight cache.

Ожидаемый output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

Human review:

- BGM слышен, но не давит;
- source sound слышен там, где он существует;
- meow приятный, короткий, не басовый;
- выбранные моменты лучше случайного начала;
- clip order ощущается намеренным;
- captions соответствуют действию и не мешают картинке.

Auto-publish остаётся OFF.

## 11. Отложено

До quality PASS cats v2 не продолжать: English slot 3, automatic publish, analytics feedback loop, trend hunter, social scraper, mass batch, expensive text-to-video.
