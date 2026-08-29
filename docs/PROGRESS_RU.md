# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила — в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-29**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish = false`; publication gate должен оставаться `PASS`.
- OpenAI / Pexels / Pixabay keys настроены локально.
- MoneyPrinterTurbo v1.3.5 работает локально на `127.0.0.1:8080`.
- Slot 1 Russian AI Short — manual QUALITY PASS.
- Последний показанный OpenAI ledger: `$0.0268 / $10.00` до Cat v3.

## Slot 1 — Russian AI Short: QUALITY PASS

Тема: «Почему осьминог меняет цвет во сне».

Исправлено: silent intermediate, unrelated stock, узкий stock pool, русский CJK font, black bars, per-clip FadeIn. Финальные subtitle settings: size 52, position 74%.

## Slot 2 — cats: v1/v2 review

Первый montage был слишком случайным и почти немым. Логи показали, что большинство stock clips не имели audio stream, поэтому старый renderer подставлял silence.

Cat v2 добавил Luna highlight selection, source audio where available, procedural BGM и soft meow. Пользователь сообщил, что стало лучше, но попросил заметнее оформить формат.

## Cat v3 — текущий формат для теста

Продуктовые решения пользователя:

- не использовать `Daily Dose of Cats` — считается слишком близким к чужому формату;
- постоянного названия серии пока нет;
- каждый выпуск имеет **уникальный номер + своё название**: `#001 — <title>`;
- начало: **чёрная плашка + быстрый мяу + название + короткий Edge-TTS voice intro**;
- между клипами: **чёрная mini-card ~0.35 сек + короткий текст + быстрый мяу**;
- procedural meow сокращён примерно с 0.58 до **0.30 сек** и не содержит bass hit;
- текст больше не обязан висеть поверх самого cat clip — mini-card несёт editorial text;
- Luna по-прежнему выбирает лучший 5-секундный момент внутри каждого источника;
- тихая procedural BGM остаётся поверх ролика; оригинальный source audio сохраняется, если существует;
- сильные клипы идут раньше по highlight score;
- будущий cat planner выбирает **одну coherent stock-friendly theme на выпуск**: toys / boxes / sleepy / reactions / jumps / dramatic stares / playful hunting и т.п.;
- planner явно запрещён использовать `Daily Dose of Cats` или близкую имитацию.

### Языки

Никакого дублирования одного и того же ролика на RU и EN.

Long-run policy: **80% EN / 20% RU** через цикл:

```text
en, en, en, en, ru
```

Frozen pilot остаётся как был: slot 2 RU, остальные 6 animal slots EN. Для выборки из 7 это 6/1 и является ближайшим целым приближением к 80/20.

## Новые Cat v3 файлы

- `src/vv_knopka/animal_episode.py` — episode numbering, unique title, intro line, transition-card metadata, 80/20 production cadence.
- `src/vv_knopka/animal_v3.py` — Edge TTS intro, black cards, quick meows, highlight clip render, final BGM mix.
- `runtime/slots/02/episode.json` — создаётся при render.

`edge-tts>=7,<8` добавлен как dependency самого VV_knopka.

## Следующая точка на ПК

После pull нужно один раз синхронизировать dependencies, потому что добавлен `edge-tts`:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

**Не запускать `plan 2` заново для первого Cat v3 теста.** Используем уже существующие `plan.json`, `sources.json` и cached highlight edit, чтобы проверить именно новый формат без ненужного stock/API расхода.

При render создастся/обновится:

```text
runtime/slots/02/episode.json
runtime/ready_for_review/slot-02-ru-animals.mp4
```

После просмотра оценить:

1. длительность intro-card;
2. качество/громкость Edge TTS intro;
3. достаточно ли заметны 0.35s black mini-cards;
4. нравится ли более быстрый 0.30s meow;
5. BGM/source-audio balance;
6. нужно ли затем сделать следующий новый themed cat episode на английском.

До human review Cat v3 не переходить к auto-publish.
