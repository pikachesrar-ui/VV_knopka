# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл хранит продуктовые решения и точку продолжения.

Последнее содержательное обновление: **2026-08-29**.

## 1. Frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.
Рабочая ветка: `mvp/pilot-scaffold`.
Draft PR #1 открыт, не merge без отдельного решения пользователя.

Pilot:
- 15 Shorts;
- 8 × `ai_short`;
- 7 × `animal_compilation`;
- slot 1 = RU AI Short;
- slot 2 = RU cat compilation test;
- остальные 13 = EN;
- один YouTube channel;
- OpenAI hard budget = `$10`;
- `auto_publish=false`, human review обязателен;
- outputs только в `runtime/ready_for_review`.

## 2. Подтверждённая локальная среда

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- OpenAI/Pexels/Pixabay keys локально в `.env`;
- MoneyPrinterTurbo v1.3.5 установлен отдельно;
- MPT API работает, но **animal/cat renderer MPT не использует**;
- cat videos рендерятся локально через FFmpeg;
- последний локальный test run перед текущими изменениями: `25 passed`;
- последний показанный OpenAI ledger: `$0.0281 / $10.00`;
- slot 1 («Почему осьминог меняет цвет во сне») — manual QUALITY PASS.

## 3. AI short architecture

Terra plan -> Pexels/Pixabay -> GPT-5.6 Luna relevance gate -> local stock -> MPT local render -> Edge TTS/subtitles -> review output.

Ключевые fixes: final MPT `videos`, anchor-aware cache, Luna visual relevance, stock-friendly topic picker, landscape blur-fill, Cyrillic font, subtitle size 52 / position 74%, no per-clip FadeIn.

## 4. Cat pipeline history

### v1

6 stock clips, первые куски, почти без звука. Большинство Pexels/Pixabay файлов вообще не имели audio stream.

### v2

Luna выбирала лучший 5s window, добавлены source audio where available, procedural BGM и procedural meow. Пользователь: стало лучше, но всё ещё слишком похоже на случайную нарезку.

### v3 test

Добавлены black cards + unique numbered title + Edge-TTS intro. Пользователь после просмотра попросил новую редактуру:

1. голос убрать;
2. opening black screen заметно сократить;
3. длинный title не помещался — нужен safe wrap;
4. transition black screen сделать длиннее;
5. на intro и каждом transition показывать **одно и то же название short**, а не отдельные captions;
6. в конце отдельная `Спасибо за просмотр` / `Thanks for watching` card;
7. synthetic meow заменить одним реальным постоянным sample;
8. искать footage именно с настоящим source audio;
9. BGM убрать полностью.

## 5. Cat format — АКТУАЛЬНАЯ реализация

### Cards / montage

`src/vv_knopka/animal_v3.py` теперь:

- **без voiceover**;
- **без background music**;
- intro card ~`0.9s`;
- transition card ~`0.75s`;
- end card ~`1.0s`;
- intro + все inter-clip cards: `#NNN — <episode title>`;
- end RU: `Спасибо за просмотр`;
- end EN: `Thanks for watching`;
- title text автоматически wrap по словам; episode number выносится на отдельную строку;
- drawtext читает UTF-8 `textfile`, а не вставляет длинную строку inline;
- cat clips без overlay text;
- clip audio нормализуется и остаётся единственным постоянным звуковым слоем между transitions.

`src/vv_knopka/animal_episode.py` version 2:

- stable episode number;
- unique display title;
- blocked `Daily Dose of Cats` / close exact phrase;
- transition card metadata повторяет display title;
- localized end text;
- `intro_voice` удалён.

### Real meow asset

Renderer ищет в порядке:

1. `.env` `CAT_MEOW_FILE=<absolute-or-relative-path>`;
2. config default:
   `runtime/assets/cat-transition-meow.mp3`;
3. только если файла нет — procedural ~0.30s fallback.

Цель: пользователь один раз выбирает приятный реальный meow и дальше один и тот же файл используется во всех cat episodes.

Найдены бесплатные варианты для выбора на слух:
- Mixkit `Sweet kitty meow` (~1s), Mixkit разрешает sound effects в YouTube и коммерческих проектах;
- Pixabay `Cat Meow` (~1s), free under Pixabay Content License.

Не commit binary sound file в repo. Хранить локально в ignored runtime или указывать через `.env`.

## 6. Audible stock gate — НОВОЕ

`src/vv_knopka/animal_audio_sources.py` добавляет отдельную политику для animal pipeline.

При `vv render-animal <slot>` теперь до highlight selection:

- повторно проверяются уже скачанные sources и `ai_materials.json`;
- source обязан иметь audio stream;
- FFmpeg `volumedetect` проверяет, что дорожка не фактически silent;
- threshold default: mean volume > `-55 dB`;
- старые silent sources reject;
- затем поиск идёт глубже по Pexels и Pixabay;
- дополнительные sound-oriented queries: `cat meowing`, `cat purring`, `cat playing`, `cat vocalizing`;
- Luna всё равно проверяет визуальную релевантность;
- target = 6 unique clips, hard minimum = 5;
- если <5 audible licensed relevant clips, pipeline **fail-closed**, не собирает silent filler.

Audit:

```text
runtime/slots/02/animal_audio_sources.json
```

Новый `sources.json` содержит только accepted audible clips и `mean_volume_db` metadata.

Важно: stock libraries часто распространяют video без original audio. Первый запуск нового gate может не найти 5 файлов. В таком случае не ослаблять gate без решения пользователя; варианты дальше: другой licensed provider или user-supplied/local cat footage.

## 7. Cat titles / language policy

- Не использовать `Daily Dose of Cats`.
- Постоянного series name пока нет.
- Каждый выпуск: unique `#NNN — title`.
- Future cat planner: 2-4 word original title, одна coherent stock-friendly theme на episode.
- Дубли RU/EN запрещены.
- Long-run cadence: `en, en, en, en, ru` (80/20 originals).
- Frozen pilot: slot 2 RU, остальные animal slots EN.

## 8. MoneyPrinterTurbo note

Если пользователь говорит, что MPT/браузер были закрыты, но cat video всё равно отрендерился — это **ожидаемо**. `render-animal` = local FFmpeg pipeline. MPT API нужен только для `render-ai`.

## 9. Следующая точка

После текущего CI пользователь должен:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
```

Для реального meow создать, например:

```powershell
New-Item -ItemType Directory -Force .\runtime\assets
```

и положить выбранный MP3 как:

```text
runtime\assets\cat-transition-meow.mp3
```

Затем:

```powershell
.\.venv\Scripts\vv.exe render-animal 2
```

Этот render может потратить немного Luna budget на новые audio-bearing sources/highlights. `plan 2` заново не нужен.

Expected:

```text
runtime/slots/02/animal_audio_sources.json
runtime/slots/02/highlights.json
runtime/slots/02/episode.json
runtime/ready_for_review/slot-02-ru-animals.mp4
```

После просмотра оценить только формат: title fit, timings, real meow, source audio, clip quality. Auto-publish остаётся запрещён.
