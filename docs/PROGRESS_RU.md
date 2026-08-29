# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-29**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний локальный test run до текущей редактуры: **25 passed**.
- Последний показанный OpenAI ledger: **$0.0281 / $10.00**.
- Slot 1 Russian AI Short («Почему осьминог меняет цвет во сне») — manual QUALITY PASS.
- MoneyPrinterTurbo нужен для `ai_short`, но **не нужен для cat/animal pipeline**: котики рендерятся локально через FFmpeg.

## Slot 2 cats — результаты review

### v1

Случайные первые куски stock clips, почти полная тишина.

### v2

Luna стала выбирать интересные windows, добавились музыка и procedural meow. Стало лучше.

### v3 test

Добавили black title cards и Edge-TTS intro. Пользователь отметил новые проблемы:

- длинное название не помещалось по ширине;
- голос в начале не нужен;
- opening black card слишком длинный;
- synthetic meow хочется заменить реальным;
- transition cards должны повторять название выпуска, а не Luna-caption;
- финальная card должна говорить `Спасибо за просмотр` / `Thanks for watching`;
- transition black card нужна заметнее/дольше;
- нужно искать именно stock videos с настоящим source audio;
- background music нужно убрать.

## Cat format — текущая редактура

Реализовано в рабочей ветке:

- **без voiceover**;
- **без BGM**;
- intro black card: ~`0.9s`;
- inter-clip black card: ~`0.75s`;
- end card: ~`1.0s`;
- intro и все inter-clip cards показывают одно и то же `#NNN — <episode title>`;
- end card: RU `Спасибо за просмотр`, EN `Thanks for watching`;
- длинный title автоматически переносится на строки; номер отделяется на собственную строку;
- renderer использует UTF-8 `textfile` для FFmpeg drawtext, поэтому длинный кириллический текст больше не должен вылезать за 1080px;
- text с cat clips убран — клип остаётся чистым;
- исходный звук клипов нормализуется и сохраняется;
- animal pipeline требует **audible** source audio: наличие audio stream + проверка `volumedetect`; практически немые дорожки reject;
- поиск audio stock идёт глубже по Pexels/Pixabay и добавляет запросы `cat meowing`, `cat purring`, `cat playing`, `cat vocalizing`;
- минимум для рендера: 5 unique audible licensed clips, target: 6;
- если stock providers не дают 5 подходящих клипов, pipeline fail-closed вместо silent filler;
- audit: `runtime/slots/02/animal_audio_sources.json`.

### Реальный meow

Renderer теперь предпочитает один постоянный пользовательский/лицензированный meow asset:

```text
runtime/assets/cat-transition-meow.mp3
```

или путь из `.env`:

```text
CAT_MEOW_FILE=D:\path\to\meow.mp3
```

Если файла пока нет, остаётся старый procedural sound только как fallback, чтобы renderer не падал.

Найдены подходящие источники для выбора реального ~1s meow: Mixkit `Sweet kitty meow` и Pixabay `Cat Meow`; пользователь должен выбрать звук на слух и сохранить один файл локально.

## Языки

- никакого RU/EN дубля одного и того же ролика;
- long-run cadence: `en, en, en, en, ru` = 80/20;
- frozen pilot: slot 2 RU, остальные animal slots EN.

## Следующая точка на ПК

После завершения CI:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
```

Перед render желательно положить выбранный реальный meow в:

```text
runtime/assets/cat-transition-meow.mp3
```

Затем:

```powershell
.\.venv\Scripts\vv.exe render-animal 2
```

Важно: этот запуск может потратить немного Luna budget, потому что старые silent sources будут отброшены и потребуется найти/проверить новые audio-bearing clips. Если подходящих stock clips <5, не ослаблять gate автоматически — сначала обсудить новый источник footage или локальные пользовательские clips.

Review output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

После просмотра проверить: fit title, длительность intro/transition/end cards, реальный meow, source audio и общий темп. Auto-publish остаётся запрещён.
