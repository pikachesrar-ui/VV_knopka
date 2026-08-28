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
- после последнего pull локальный pytest пользователя: **16 passed in 0.15s**.

## 4. Реализованная архитектура

### AI short

Terra structured plan -> Pexels/Pixabay candidate search -> GPT-5.6 Luna image relevance gate -> downloaded local approved stock -> MPT local-material render -> Edge TTS/subtitles -> review output.

Quality/safety behavior:

- MPT final `videos` скачивается раньше silent `combined_videos`;
- visual anchor обязателен;
- visual confidence threshold >= `0.72`;
- narrow topics могут использовать минимум 3 unique approved sources при >=36 sec reusable footage;
- MPT curated mode использует непересекающиеся segments длинных approved sources;
- landscape material превращается в 1080x1920 blur-fill;
- Russian subtitles используют локальный Windows Cyrillic font, не committed binary;
- subtitle size/position после последнего human review: **52 / 74%**;
- MPT per-segment FadeIn отключён;
- stock cache теперь anchor-aware: audit от старого topic не может переиспользоваться после replan.

### Automatic topic stockability

Выяснилось, что хороший factual topic может быть непригоден для бесплатного stock workflow. Реальный пример: slot 3 выбрал `superb lyrebird`, но Pexels+Pixabay+Luna дали только 2 approved sources.

Поэтому для AI slots **без explicit `--topic`** planner теперь ограничен broad stock-friendly anchors:

`cat, dog, octopus, bee, ant, penguin, dolphin, elephant, horse, rabbit, fox, owl, parrot, turtle, snake, butterfly, spider, frog, duck, chicken`.

Дополнительные правила:

- не сужать anchor до rare species/subspecies/breed/scientific name;
- факт должен действительно относиться к broad chosen animal;
- нельзя рассказывать rare-species fact поверх generic animal footage;
- visual anchors из предыдущих slot plans исключаются, пока остаются другие stock-friendly варианты;
- explicit user topic override остаётся разрешён и имеет приоритет.

### Animal compilation

Local FFmpeg assembly остаётся отдельной веткой.

Актуальный pilot flow умеет автоматически построить `sources.json` из vision-approved Pexels/Pixabay stock, сохраняя provider/provider id/creator/source URL/license/commercial flag/vision evidence.

Renderer:

- target сейчас 6 unique clips × ~5 sec ≈30 sec;
- minimum unique clips = 5;
- no transition SFX;
- tiny visual/audio fades only;
- source audio loudness normalization;
- missing source audio получает silent stereo track вместо render failure;
- all source aspect ratios получают 1080x1920 blur-fill + sharp complete foreground.

## 5. Slot 1 — Russian AI Short: MANUAL QUALITY PASS

Тема: **«Почему осьминог меняет цвет во сне»**.

История проблем: silent intermediate -> final video fix; unrelated Pexels filler -> Pexels+Pixabay+Luna; 8 unique clips -> duration fallback; bad CJK Russian font -> Windows Cyrillic; black bars -> blur-fill; per-clip black FadeIn -> disabled.

Пользователь сообщил: **«Этот результат мне нравится»**. Slot 1 считается QUALITY PASS.

После дополнительного кадра пользователь попросил сделать subtitles немного больше и ниже. Зафиксировано:

- font size `52`;
- custom position `74%`.

## 6. Slot 2 — Russian cats compilation

Пользователь хочет тест с котиками.

Команды:

```powershell
.\.venv\Scripts\vv.exe plan 2 --topic cats
.\.venv\Scripts\vv.exe render-animal 2
```

Planner при `--topic cats` обязан вернуть `visual_anchor="cat"`. Затем auto-curator ищет licensed Pexels/Pixabay clips, Luna принимает clearly visible cats, provenance сохраняется, FFmpeg собирает review montage.

Output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

Это review-only montage test; до публикации отдельно оценить editorial transformation/reused-content risk.

## 7. Slot 3 — English AI Short: first attempt STOCK FAIL

Пользователь выполнил:

```text
vv plan 3
vv render-ai 3
```

Первый plan выбрал `visual_anchor="superb lyrebird"`.

Рендер fail-closed:

```text
Multi-source visual relevance gate found only 2/8 usable clips for visible anchor 'superb lyrebird'
Only 2 vision-approved unique sources are cached; need at least 3.
```

Это стало основанием для stock-friendly planner constraint выше.

Важный cache fix: если `plan 3` теперь перегенерировать с другим anchor, старый `ai_materials.json` (`superb lyrebird`) не считается reusable/exhausted для нового animal. Новый stock search должен стартовать автоматически; вручную удалять audit не нужно.

## 8. Точная текущая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
```

Для slot 3 старый lyrebird plan намеренно заменить:

```powershell
.\.venv\Scripts\vv.exe plan 3
Get-Content .\runtime\slots\03\plan.json -Raw
.\.venv\Scripts\vv.exe render-ai 3
```

Для slot 2 независимо:

```powershell
.\.venv\Scripts\vv.exe plan 2 --topic cats
.\.venv\Scripts\vv.exe render-animal 2
```

Ожидаемые outputs:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
runtime/ready_for_review/slot-03-en-ai.mp4
```

Не публиковать автоматически. После обоих renders — human review и style adjustments.

## 9. Отложено

До review slots 2-3 не делать: automatic publish, analytics feedback loop, trend hunter, social scraper, mass batch, expensive text-to-video.
