# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила остаются в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-28**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish = false`, publication gate = `PASS`.
- OpenAI/Pexels/Pixabay keys настроены локально в `.env`.
- MoneyPrinterTurbo v1.3.5 установлен, API работает на `127.0.0.1:8080`.
- `vv plan 1` создан: русский Short «Почему осьминог меняет цвет во сне».
- Первый plan-вызов OpenAI стоил `$0.0051`; общий hard cap пилота `$10`.
- После Pexels + Pixabay vision review общий ledger: **`$0.0104 / $10.00`**.
- Локальные тесты после multi-source версии: **`10 passed in 0.10s`**.

## Первый render slot 1 — review FAIL

Первый MPT render создал видео, но пользователь увидел две проблемы:

1. review-файл был без звука;
2. Pexels подмешал нерелевантные кадры: fish/jellyfish/turtle/human skin.

Sound root cause исправлен: adapter раньше скачивал `combined_videos` (visual-only), теперь сначала берёт MPT `videos` (final output с TTS/subtitles).

Pacing изменён с 4 до 6 секунд на сегмент.

## Material relevance — реальные результаты

### 1. Strict Pexels slug gate

Требование `octopus` в Pexels URL безопасно остановило filler, но нашло только `2/8`. Критерий признан слишком жёстким.

### 2. GPT-5.6 Luna visual gate на Pexels

Просмотрено 30 preview images, принято только `2/8`. Вывод: проблема уже не в фильтре, а в бедности каталога Pexels по узкой теме.

### 3. Pexels + Pixabay

Добавлен Pixabay Video API и тот же Luna visual gate `accepted=true`, confidence >= `0.72`.

Фактический локальный прогон пользователя:

```text
RuntimeError: Multi-source visual relevance gate found only 3/8 usable clips for visible anchor 'octopus' after Pexels + Pixabay.
OpenAI spent: $0.0104 / $10.00
10 passed in 0.10s
```

Это снова корректный fail-closed: нерелевантный filler не пропущен. Но требование **8 отдельных исходных файлов** признано продуктово неправильным для узких тем.

## Текущий фикс: quality by duration, а не 8 unique files

Проверен актуальный MoneyPrinterTurbo `combine_videos()`:

- в `sequential` mode он берёт только первый segment каждого source;
- в `random` mode он режет длинные source videos на несколько непересекающихся сегментов, сначала приоритизирует по одному segment от каждого unique source, затем использует следующие segments как fallback до покрытия narration.

Поэтому для уже vision-approved local footage теперь вводится fallback:

- предпочтение всё ещё 8 unique clips;
- minimum unique approved sources = **3**;
- reusable segment size = **6 sec**;
- максимум **4 сегмента на один source** при подсчёте quality gate;
- minimum reusable approved footage = **36 sec**;
- confidence threshold не снижается (`>=0.72`);
- human skin/random animals/scenery всё ещё запрещены;
- если cached approved material удовлетворяет duration-gate, новых Pexels/Pixabay/Luna запросов не делается;
- если оба provider pool уже исчерпаны и cached material недостаточен, команда останавливается **без повторной траты OpenAI**.

MPT adapter для curated local footage теперь использует `video_concat_mode=random`, чтобы брать разные непересекающиеся части длинных approved sources вместо повторения одного и того же первого кадра.

Добавлены regression tests для duration fallback и curated MPT concat mode.

## Точная следующая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-ai 1
```

`vv plan 1` повторно НЕ запускать.

Ожидаемый успешный cached path начинается примерно так:

```text
Reusing approved stock: 3 unique sources, XX.Xs reusable footage
Curated stock materials: 3
Material audit: D:\KiraS\VV_knopka\runtime\slots\01\ai_materials.json
MPT task: ...
```

Этот запуск в идеале **не должен увеличивать OpenAI spend**, потому что использует уже проверенные 3 источника.

Если cached 3 sources дают меньше 36 секунд reusable footage, команда остановится с точным количеством секунд без повторного vision bill. Тогда следующий вариант — добавить relevant still-image fallback/Ken Burns или ещё один источник, но не снижать visual relevance.

После успешного render проверить `runtime/ready_for_review/slot-01-ru-ai.mp4`:

- русская озвучка слышна;
- субтитры есть;
- все использованные segments содержат осьминога;
- нет human skin / random fish / jellyfish / turtle filler;
- повторное использование разных частей одного source не выглядит очевидным/навязчивым.

Только после ручного PASS slot 1 переходить к slot 2. Автопубликация остаётся выключена.
