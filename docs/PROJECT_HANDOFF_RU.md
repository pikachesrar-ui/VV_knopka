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

Animal compilations: никакого loud bass/drop/impact/boom SFX; source/provenance и commercial-use eligibility обязательны; raw social repost pipeline запрещён как default.

## 2. Git workflow

- default branch: `main`;
- рабочая ветка: `mvp/pilot-scaffold`;
- draft PR #1: `MVP: review-first 15-Short pilot scaffold`;
- PR не merge до ручного PASS первых двух видео;
- новый чат сначала полностью читает `AGENT.md`, этот файл и `docs/PROGRESS_RU.md`, затем проверяет live GitHub state/CI.

## 3. Подтверждённая локальная среда

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- bootstrap PASS;
- publication gate PASS;
- OpenAI/Pexels/Pixabay keys локально в `.env`;
- MoneyPrinterTurbo v1.3.5 установлен в ignored `MoneyPrinterTurbo`;
- MPT API работает на `127.0.0.1:8080`;
- последний известный OpenAI ledger перед slots 2-3: **$0.0104 / $10.00**.

## 4. Реализованная архитектура

### AI short

Terra structured plan -> Pexels/Pixabay candidate search -> GPT-5.6 Luna image relevance gate -> downloaded local approved stock -> MPT local-material render -> Edge TTS/subtitles -> review output.

Ключевые quality fixes:

- MPT final `videos` скачивается раньше silent `combined_videos`;
- visual anchor обязателен;
- visual confidence threshold >= `0.72`;
- narrow topics могут использовать минимум 3 unique approved sources при >=36 sec reusable footage;
- MPT curated mode использует непересекающиеся segments длинных approved sources;
- landscape material превращается в 1080x1920 blur-fill;
- Russian subtitles используют локальный Windows Cyrillic font, не committed binary;
- MPT per-segment FadeIn отключён.

### Animal compilation

Local FFmpeg assembly остаётся отдельной веткой.

Актуальный pilot flow умеет автоматически построить `sources.json` из vision-approved Pexels/Pixabay stock, сохраняя:

- provider;
- provider id;
- creator;
- source URL;
- license name;
- `commercial_use_allowed=true` только для поддерживаемых stock providers;
- vision confidence/reason.

Renderer:

- target сейчас 6 unique clips × ~5 sec ≈30 sec;
- minimum unique clips = 5;
- no transition SFX;
- tiny visual/audio fades only;
- source audio loudness normalization;
- missing source audio получает silent stereo track вместо render failure;
- all source aspect ratios получают 1080x1920 blur-fill + sharp complete foreground.

Pexels/Pixabay license basis перепроверен 2026-08-28; third-party trademark/privacy/IP restrictions всё равно остаются отдельным риском, поэтому provenance хранится.

## 5. Slot 1 — Russian AI Short: MANUAL QUALITY PASS

Тема: **«Почему осьминог меняет цвет во сне»**.

Первый plan вызов стоил `$0.0051`. После material vision общий ledger был `$0.0104`.

История реальных проблем и исправлений:

1. Первый review MP4 был silent — VV adapter скачивал MPT intermediate `combined_videos`. Исправлено на final `videos` first.
2. Blind Pexels selection включал fish/coral/jellyfish/turtle/human skin. Добавлен Pexels+Pixabay Luna visual gate.
3. 8 unique clips оказалось слишком жёстким для octopus. Добавлен duration-based approved footage fallback.
4. Русский CJK font дал плохое spacing/wrap. Заменён локальным Windows Cyrillic font.
5. Landscape Pixabay clip имел black bars. Добавлен local 9:16 blur-fill.
6. `FadeIn` затемнял каждый segment. Отключён.

После последнего quality render пользователь сообщил: **«Этот результат мне нравится»**. Slot 1 теперь считается **QUALITY PASS**.

## 6. Текущий запрос пользователя

Пользователь хочет теперь одновременно попробовать:

1. видео с котиками;
2. видео на английском.

Это естественно соответствует frozen pilot:

- **slot 2** = Russian `animal_compilation`, сейчас специально cats;
- **slot 3** = English `ai_short`.

## 7. Slot 2 — cats design

Новый CLI topic override:

```powershell
.\.venv\Scripts\vv.exe plan 2 --topic cats
```

Для cat topic planner обязан вернуть `visual_anchor="cat"` и cat-specific stock queries.

Затем:

```powershell
.\.venv\Scripts\vv.exe render-animal 2
```

Если `runtime/slots/02/sources.json` отсутствует, команда автоматически:

1. запускает тот же Pexels+Pixabay stock curator;
2. Luna принимает только clearly visible cat candidates;
3. требует минимум 5 unique licensed cat clips;
4. выбирает до 6;
5. пишет source/provenance/license manifest;
6. рендерит FFmpeg compilation.

Output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

Это первый montage-style test. Перед реальной публикацией всё равно оценить, хватает ли editorial transformation; при необходимости следующим этапом добавить voiceover/on-screen running joke.

## 8. Slot 3 — first English AI Short

Команды:

```powershell
.\.venv\Scripts\vv.exe plan 3
.\.venv\Scripts\vv.exe render-ai 3
```

Output:

```text
runtime/ready_for_review/slot-03-en-ai.mp4
```

Использует proven slot-1 quality stack, но English TTS/font.

## 9. Точная текущая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status

.\.venv\Scripts\vv.exe plan 2 --topic cats
.\.venv\Scripts\vv.exe render-animal 2

.\.venv\Scripts\vv.exe plan 3
.\.venv\Scripts\vv.exe render-ai 3

.\.venv\Scripts\vv.exe status
```

Не публиковать автоматически. После двух renders — human review и style adjustments.

## 10. Отложено

До review slots 2-3 не делать: automatic publish, analytics feedback loop, trend hunter, social scraper, mass batch, expensive text-to-video.
