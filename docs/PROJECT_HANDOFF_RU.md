# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл — для продуктовых решений и точки продолжения.

Последнее содержательное обновление: **2026-08-29**.

## 1. Frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.

Цель: review-first pipeline для 15 YouTube Shorts в нише **Animals / Nature Curiosities**.

Зафиксировано:

- 15 Shorts;
- 8 × `ai_short`;
- 7 × `animal_compilation`;
- slot 1 = русский AI Short;
- slot 2 = русская cat compilation;
- остальные 13 = English;
- пока один YouTube-канал;
- OpenAI hard budget = **$10**;
- `auto_publish=false`;
- human review обязателен;
- outputs только в `runtime/ready_for_review`;
- не добавлять новые платные providers без отдельного решения пользователя;
- animal cuts: никакого loud bass/drop/impact/boom;
- provenance/source/license обязательны;
- raw social repost pipeline не является default.

## 2. Git workflow

- default branch: `main`;
- рабочая ветка: `mvp/pilot-scaffold`;
- draft PR #1: `MVP: review-first 15-Short pilot scaffold`;
- PR не merge без отдельного решения пользователя;
- новый чат сначала читает `AGENT.md`, этот файл и `docs/PROGRESS_RU.md`, затем проверяет live GitHub state/CI.

## 3. Локальная среда пользователя

Путь: `D:\KiraS\VV_knopka`.

- Python `3.11.0`;
- OpenAI/Pexels/Pixabay keys в локальном `.env`;
- MoneyPrinterTurbo v1.3.5 в ignored `MoneyPrinterTurbo`;
- MPT API `127.0.0.1:8080`;
- последний известный OpenAI ledger после cat-plan/vision: **$0.0268 / $10.00**.

## 4. AI Short architecture

Terra structured plan -> stock-friendly visual anchor -> Pexels/Pixabay -> GPT-5.6 Luna visual relevance -> local approved stock -> MPT local-material render -> Edge TTS/subtitles -> review MP4.

Quality/safety fixes:

- final MPT `videos` preferred over silent `combined_videos`;
- visual anchor required;
- visual confidence >= 0.72;
- duration-based fallback for narrow topics;
- curated mode can reuse non-overlapping segments of long approved sources;
- landscape stock -> 9:16 blur-fill;
- Russian subtitles -> local Windows Cyrillic font;
- subtitle size/position = `52 / 74%`;
- per-segment MPT FadeIn disabled;
- material cache tied to visual anchor;
- automatic topics restricted to broad stock-friendly animals after `superb lyrebird` stock failure.

## 5. Slot 1 — Russian AI Short: MANUAL QUALITY PASS

Тема: «Почему осьминог меняет цвет во сне».

Реальные fixes прошли через несколько review cycles: silent final download, unrelated stock, narrow stock availability, CJK font, black bars, per-clip fade. Пользователь после последней версии сказал: **«Этот результат мне нравится»**.

Slot 1 считается QUALITY PASS.

## 6. Slot 2 — Russian cats: current priority

Пользователь решил пока остановиться на котиках и не продолжать English slot, пока cat format не станет интереснее.

### v1 result

Команды:

```powershell
.\.venv\Scripts\vv.exe plan 2 --topic cats
.\.venv\Scripts\vv.exe render-animal 2
```

v1 успешно нашёл 6 licensed/vision-approved cat clips и отрендерил 30 sec montage.

Пользовательский review:

- звука практически нет;
- просто случайные моменты;
- хотелось более интересную нарезку;
- вместо неприятного bass transition пользователь хочет приятный **meow**.

Лог подтвердил: большинство stock videos вообще не имели audio stream. Renderer подставлял `anullsrc`, поэтому AAC track существовал, но был почти silent.

### Cat montage v2 design

Используем уже существующий `runtime/slots/02/sources.json`; заново stock не ищем.

Pipeline:

1. Для каждого cat source берём до 4 candidate windows по всей длине, а не только начало.
2. Для каждого candidate делаем компактный 3-frame contact sheet.
3. GPT-5.6 Luna vision выбирает cutest/funniest/action moment.
4. Luna пишет short RU caption (<=5 words).
5. Luna/heuristic ordering ставит сильнейший moment первым.
6. Renderer starts each clip at chosen timestamp.
7. Original source audio сохраняется/нормализуется, если stream есть.
8. Silent sources получают silent bed, чтобы FFmpeg не падал.
9. Поверх всего видео генерируется локальный quiet playful BGM.
10. На каждом cut добавляется локальный procedural soft meow; три pitch variants.
11. Никакого bass/drop/impact/boom.
12. Captions рисуются локальным system font.
13. 9:16 blur-fill сохраняется.

Процедурные BGM/meow генерируются локально кодом и не используют внешний copyrighted asset.

### Первый v2 запуск — реальные ошибки

Пользователь получил:

```text
1 failed, 21 passed
publication gate: FAIL
OpenAI spent: $0.0268 / $10.00
HTTP 403 Forbidden https://api.openai.com/v1/responses
```

#### Publication gate bug

Причина: `[audio].transition_sfx` ошибочно был переключён с `none` на `soft_meow`, а frozen publication gate требует global transition SFX = none.

Исправлено без ослабления gate:

```toml
[audio]
transition_sfx = "none"

[animal]
transition_sfx = "soft_meow"
```

То есть общий safety invariant остаётся прежним, meow scoped only to animal pipeline.

#### Highlight vision HTTP 403

До этого тот же OpenAI key и GPT-5.6 Luna успешно работали для stock thumbnail vision. Новый 403 появился на одном большом request с множеством локальных Base64 contact sheets.

Актуальная OpenAI docs (2026-08-29) подтверждает:

- Responses API поддерживает `input_image`;
- Base64 data URL разрешён;
- multiple images разрешены;
- GPT-5.6 Luna поддерживает image input.

Поэтому формат сам по себе не запрещён.

Implemented recovery:

- contact sheets уменьшены, чтобы payload был легче;
- сначала пробуем общий request;
- если именно HTTP 403, автоматически fallback на **one clip per request**, максимум 4 images/request;
- usage каждого успешного fallback-call идёт в тот же $10 ledger;
- если даже маленький request получает 403, приложение выводит безопасные OpenAI `message/type/code/param`, не API key;
- failed 403 не записывается как успешный usage record;
- `highlights.json` cache version поднят, чтобы старый incomplete state не считался готовым.

## 7. Slot 3 — English AI Short: paused

Первый английский plan выбрал `superb lyrebird`; stock gate нашёл только 2 approved sources и fail-closed.

После этого:

- planner ограничен broad stock-friendly animals для automatic topics;
- stale material cache стал anchor-aware;
- старый lyrebird audit не блокирует новую тему.

Но пользователь сейчас явно решил **сначала довести котиков**, поэтому slot 3 пока не трогать.

## 8. Точная следующая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

Важно:

- `vv plan 2 --topic cats` повторно НЕ запускать;
- `runtime/slots/02/sources.json` НЕ удалять;
- заново stock search не нужен.

При успехе:

```powershell
.\.venv\Scripts\vv.exe status
Get-Content .\runtime\slots\02\highlights.json -Raw
```

Review output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

Human review criteria:

- highlights действительно интереснее первых 5 секунд;
- captions не мешают;
- BGM не слишком громкий;
- procedural meow звучит приятно, не как электронный писк;
- original source audio слышен там, где он существует;
- cuts не содержат bass hits.

Если synthetic meow не понравится — заменить только SFX на один лицензированный real-cat sample; остальная architecture остаётся.

## 9. Отложено

До quality-pass cat v2 не делать:

- English slot 3 continuation;
- auto publish;
- analytics feedback loop;
- trend hunter;
- social scraper;
- mass batch;
- expensive text-to-video.
