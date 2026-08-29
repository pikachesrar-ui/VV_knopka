# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила — в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-29**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish = false`.
- OpenAI / Pexels / Pixabay keys настроены локально.
- MoneyPrinterTurbo v1.3.5 работает локально на `127.0.0.1:8080`.
- Slot 1 Russian AI Short — manual QUALITY PASS.
- После Cat v3 pull пользователь получил **25 passed in 0.77s**.
- Последний показанный OpenAI ledger: **$0.0281 / $10.00**.
- Publication gate: **PASS**.

## Slot 1 — Russian AI Short: QUALITY PASS

Тема: «Почему осьминог меняет цвет во сне».

Исправлено: silent intermediate, unrelated stock, узкий stock pool, русский CJK font, black bars, per-clip FadeIn. Финальные subtitle settings: size 52, position 74%.

## Slot 2 — cats: v1/v2 review

Первый montage был слишком случайным и почти немым. Логи показали, что большинство stock clips не имели audio stream, поэтому старый renderer подставлял silence.

Cat v2 добавил Luna highlight selection, source audio where available, procedural BGM и soft meow. Пользователь сообщил, что стало лучше, но попросил заметнее оформить формат.

## Cat v3 — текущий формат для теста

Продуктовые решения пользователя:

- не использовать `Daily Dose of Cats` — слишком близко к чужому формату;
- постоянного названия серии пока нет;
- каждый выпуск имеет **уникальный номер + своё название**: `#001 — <title>`;
- начало: **чёрная плашка + быстрый мяу + название + короткий Edge-TTS voice intro**;
- между клипами: **чёрная mini-card ~0.35 сек + короткий текст + быстрый мяу**;
- procedural meow сокращён примерно с 0.58 до **0.30 сек** и не содержит bass hit;
- editorial text переносится на black mini-cards вместо постоянного текста поверх cat clip;
- Luna выбирает лучший 5-секундный момент внутри каждого источника;
- тихая procedural BGM остаётся; оригинальный source audio сохраняется, если существует;
- сильные клипы идут раньше по highlight score;
- будущий cat planner выбирает одну coherent stock-friendly theme на выпуск: toys / boxes / sleepy / reactions / jumps / dramatic stares / playful hunting и т.п.;
- planner явно запрещён использовать `Daily Dose of Cats` или близкую имитацию.

### Языки

Никакого дублирования одного и того же ролика на RU и EN.

Long-run policy: **80% EN / 20% RU** через цикл:

```text
en, en, en, en, ru
```

Frozen pilot: slot 2 RU, остальные 6 animal slots EN. Для 7 выпусков это 6/1.

## Cat v3 runtime incident: Edge voice ID

Пользователь успешно дошёл до:

```text
Highlight edit: runtime/slots/02/highlights.json
Cat episode: #001 — Кошки и их важные маленькие миссии
Intro voice: У каждой кошки есть дело. Даже если никто не понимает какое.
```

Затем рендер остановился до FFmpeg assembly:

```text
ValueError: Invalid voice 'ru-RU-SvetlanaNeural-Female'.
RuntimeError: Edge TTS could not synthesize cat intro voice
```

Причина: `edge-tts` принимает канонический voice ID `ru-RU-SvetlanaNeural`; суффикс `-Female` относится к человекочитаемым/MPT display labels и библиотекой отвергается. Английский `en-US-AriaNeural-Female` имел тот же потенциальный дефект.

Исправлено в `config/pilot.toml`:

```text
edge_voice_ru = "ru-RU-SvetlanaNeural"
edge_voice_en = "en-US-AriaNeural"
```

Добавлен regression test, который запрещает возвращение `-Female/-Male` в pilot Edge IDs.

Важно: `episode.json`, plan, sources и highlight selection уже существуют. **Не перегенерировать их** и не тратить OpenAI повторно.

## Следующая точка на ПК

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

Повторный `pip install` не нужен, если `edge-tts` уже установлен предыдущей командой.

Не запускать `plan 2` и не удалять `episode.json`, `sources.json`, `highlights.json`.

Ожидаемый output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

После просмотра оценить:

1. длительность intro-card;
2. качество/громкость Edge TTS intro;
3. заметность 0.35s black mini-cards;
4. быстрый 0.30s meow;
5. BGM/source-audio balance;
6. общий темп;
7. стоит ли следующим делать новый themed cat episode на английском.

До human review Cat v3 не переходить к auto-publish.
