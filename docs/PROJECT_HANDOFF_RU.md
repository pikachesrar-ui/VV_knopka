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
- slot 2 = русский cat compilation test;
- остальные 13 = English;
- пока один YouTube channel;
- OpenAI hard budget = **$10**;
- `auto_publish=false`;
- human review обязателен;
- output только в `runtime/ready_for_review`;
- не добавлять новые платные providers без отдельного решения пользователя.

## 2. Git workflow

- default branch: `main`;
- рабочая ветка: `mvp/pilot-scaffold`;
- draft PR #1 открыт и не merge без отдельного решения пользователя;
- новый чат сначала читает `AGENT.md`, этот файл и `docs/PROGRESS_RU.md`, затем проверяет live GitHub state/CI.

## 3. Подтверждённая локальная среда

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- OpenAI/Pexels/Pixabay keys локально в `.env`;
- MoneyPrinterTurbo v1.3.5 установлен отдельно;
- MPT API работает на `127.0.0.1:8080`;
- последний показанный OpenAI ledger: `$0.0268 / $10.00` до Cat v3.

После Cat v3 в `pyproject.toml` добавлен `edge-tts>=7,<8`; после следующего `git pull` пользователь должен один раз выполнить:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## 4. AI short architecture

Terra plan -> Pexels/Pixabay -> GPT-5.6 Luna relevance gate -> local approved stock -> MPT local render -> Edge TTS/subtitles -> review output.

Ключевые fixes:

- скачивать final MPT `videos`, а не silent `combined_videos`;
- anchor-aware stock cache;
- Luna visual relevance gate;
- duration fallback для narrow stock topics;
- landscape blur-fill;
- Russian Windows Cyrillic font;
- subtitles size 52 / position 74%;
- per-segment FadeIn disabled;
- automatic AI topics ограничены stock-friendly animals.

Slot 1 («Почему осьминог меняет цвет во сне») получил manual QUALITY PASS.

## 5. Cat compilation history

### v1

6 stock clips × первые ~5 секунд. Почти без звука, потому что большинство Pexels clips не имели audio stream. Результат выглядел случайной нарезкой.

### v2

Добавлено:

- Luna выбирает лучший window внутри каждого source video;
- клипы сортируются по интересности;
- короткие подписи;
- source audio where available;
- procedural BGM;
- procedural meow transitions.

Стало лучше, но пользователь попросил более заметный и узнаваемый формат.

## 6. Cat v3 — АКТУАЛЬНЫЙ дизайн

Пользователь подтвердил:

- **НЕ использовать `Daily Dose of Cats`** и близкие имитации;
- постоянное название серии пока не нужно;
- каждый выпуск имеет уникальный номер и название: `#001 — <episode title>`;
- opening: чёрный фон + быстрый мяу + название + короткий voice intro;
- между каждым clip: чёрная mini-card + короткий текст + быстрый мяу;
- intro voice включён для теста;
- тематика выпусков должна быть более связной, а не «random cats».

### Языковая политика

Не делать один и тот же ролик в двух языковых версиях.

Long-run production cadence:

```text
en, en, en, en, ru
```

то есть 80% EN / 20% RU originals.

Frozen pilot сохраняется: среди 7 animal slots один RU (slot 2) и шесть EN, что является ближайшим целым приближением к 80/20 для семи выпусков.

### Cat v3 implementation

`src/vv_knopka/animal_episode.py`:

- stable episode numbering по animal slots;
- display title `#NNN — title`;
- если planner вдруг вернёт `Daily Dose of Cats`, title автоматически заменяется (`Cat Chaos` / `Кото-хаос`);
- intro line из plan hook с ограничением длины;
- transition card text берётся из Luna-selected captions;
- production language cycle 4 EN : 1 RU.

`src/vv_knopka/animal_v3.py`:

- Edge TTS intro voice (`+8%` rate);
- intro black card ~1.8s, автоматически удлиняется если voice длиннее;
- procedural quick meow ~0.30s (старый был ~0.58s);
- transition black card ~0.35s;
- title font ~72, transition text ~64;
- clips остаются 9:16 blur-fill + sharp foreground;
- text убран с самих cat clips, чтобы картинка была чище;
- source audio normalized/kept where present;
- silent clips получают silence, но общий BGM и card meows обеспечивают ненулевой звук;
- quiet procedural BGM mixed over full timeline;
- никаких bass/drop/impact/boom.

`config/pilot.toml` содержит Cat v3 timings/volumes и language cycle.

### Planner для будущих cat episodes

При `vv plan <animal-slot> --topic cats` planner должен:

- visual_anchor=`cat`;
- выбрать **одну** coherent stock-friendly тему выпуска (toys, boxes, sleepy, reactions, jumps, dramatic stares, playful hunting и т.п.);
- все search terms отражают эту тему;
- short original title 2-5 words;
- hook короткий и voice-friendly;
- запрещена фраза `Daily Dose of Cats` и близкая имитация.

## 7. OpenAI highlight 403 history

На первом Cat v2 highlight request был 403. Исправлено:

- preview images уменьшены;
- общий запрос при 403 автоматически fallback на one-clip-at-a-time (до 4 images/request);
- provider error теперь показывается без API key;
- global publication gate снова требует `[audio] transition_sfx="none"`; animal meow живёт отдельно под `[animal]`.

Пользователь после fixes сообщил, что Cat v2 уже лучше, поэтому highlight selection/cache считается рабочим.

## 8. Точная текущая точка

Цель: **перерендерить slot 2 в Cat v3**, не тратясь повторно на plan/source search/highlight selection.

На ПК:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

Не запускать `plan 2` заново перед этим тестом.

Expected extra runtime file:

```text
runtime/slots/02/episode.json
```

Review output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

После render проверить:

- intro title/card читается ли на телефоне;
- voice intro не слишком длинный/громкий;
- quick meow приятнее ли старого;
- black mini-card 0.35s достаточно ли заметна;
- transition text полезен или мешает;
- BGM/source audio balance;
- нужен ли следующий новый themed cat episode сделать уже English.

До этого review не заниматься auto-publish/analytics/trend hunter/mass batch.
