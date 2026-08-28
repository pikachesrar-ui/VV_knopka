# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила остаются в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-28**.

## Уже подтверждено на ПК пользователя

- Windows bootstrap исправлен и успешно завершён.
- Project Python: `3.11.0`.
- `auto_publish = false`.
- publication gate: `PASS`.
- OpenAI API key настроен локально в `.env`.
- `vv plan 1` успешно создал `runtime/slots/01/plan.json`.
- Первый реальный OpenAI вызов стоил **$0.0051** из project budget **$10.00**.
- Slot 1: русский `ai_short` про изменение окраски осьминога во сне.
- Fact-check slot 1: PASS с оговоркой — не утверждать, что сновидения осьминогов доказаны.
- MoneyPrinterTurbo v1.3.5 установлен и API успешно запускается на `127.0.0.1:8080`.
- Pexels key настроен, Edge TTS успешно создал `audio.mp3`, Edge subtitles успешно создали `subtitle.srt`.
- Первый `vv render-ai 1` завершился и создал `runtime/ready_for_review/slot-01-ru-ai.mp4`.

## Результат первого визуального review slot 1

Первый MP4 **не принимается**.

Проблемы:

1. В скачанном `slot-01-ru-ai.mp4` нет звука.
2. Материалы нерелевантны: кроме осьминогов попали рыбы/кораллы, медузы, черепахи и даже человеческая кожа.

### Root cause звука — исправлен

MoneyPrinterTurbo корректно создал `audio.mp3`, `subtitle.srt`, промежуточный `combined-1.mp4` и финальный `final-1.mp4`.

Наш adapter ошибочно предпочитал `combined_videos` перед `videos`, поэтому скачивал промежуточную silent visual concat вместо финального файла.

Исправлено: `download_video()` теперь предпочитает `task["videos"]` и использует `combined_videos` только как fallback. Есть regression test.

### Root cause материалов

MPT получил 5 Pexels search terms, нашёл 19–20 кандидатов на каждый и автоматически выбрал 10 клипов. Pexels search semantics слишком широкая: запросы вроде `octopus skin texture macro` способны возвращать человеческую кожу, а reef/underwater terms — других морских животных.

Первый защитный фикс сделал URL/slug gate: кандидат проходил только если Pexels page slug явно содержал `octopus`. Он корректно не пропустил filler, но оказался слишком строгим.

## Второй material-gate run — FAIL CLOSED 2/8

На ПК пользователя после `8 passed` команда:

```powershell
.\.venv\Scripts\vv.exe render-ai 1
```

остановилась до MPT-render с:

```text
RuntimeError: Pexels relevance gate found only 2/8 usable clips whose source page explicitly matches visual anchor 'octopus'.
```

Это ожидаемый fail-closed, но показывает, что наличие слова `octopus` в URL имеет слишком низкий recall и не годится как основной критерий визуальной релевантности.

## Текущий material relevance design — Luna vision

URL slug теперь только слабый metadata signal. Основной gate:

1. VV_knopka делает Pexels search по anchored queries.
2. Собирает максимум **30** уникальных portrait-кандидатов длительностью >= 6 сек.
3. Берёт Pexels preview image каждого кандидата.
4. **GPT-5.6 Luna vision** через Responses API проверяет батчами по 10 превью, действительно ли обязательный visual anchor (`octopus`) ясно виден в кадре.
5. Отбрасываются unrelated animals, люди/человеческая кожа, scenery-only, drawings/text и неоднозначные close-ups.
6. Требуется `accepted=true` и confidence >= **0.72**.
7. Как только набрано 8 approved clips, только они скачиваются в MPT `storage/local_videos`.
8. Все решения и причины сохраняются в `runtime/slots/01/ai_materials.json`.
9. Если после максимум 30 preview не набрано 8 approved clips, pipeline снова FAILS CLOSED. В таком случае следующий шаг — второй бесплатный footage provider, а не ослабление visual gate вслепую.

Vision model: `gpt-5.6-luna`. Его фактический token usage записывается в тот же OpenAI budget ledger; project cap остаётся **$10**. Config резервирует максимум `$0.03` на один vision batch только как budget guard, фактическая стоимость считается по usage.

Также pacing остаётся **6 секунд на источник**.

Для будущих планов OpenAI structured output содержит `visual_anchor`, и каждый footage search term обязан включать этот anchor. Для старого slot 1 anchor автоматически выводится как `octopus`, поэтому регенерировать plan не нужно.

## Дополнительный фикс MPT config

`configure-mpt-windows.ps1` раньше писал `config.toml` через Windows PowerShell UTF-8 с BOM. MPT успешно делал compatibility retry, но показывал TOML warning. Теперь файл записывается UTF-8 **без BOM**.

## Точная следующая точка

MPT API можно оставить запущенным. В другом PowerShell из `D:\KiraS\VV_knopka`:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-ai 1
```

Повторно запускать `vv plan 1` **не нужно**.

Новый `render-ai 1` сначала потратит небольшое количество OpenAI API budget на Luna vision. При успехе появится:

```text
Curated Pexels materials: 8
Material audit: ...\runtime\slots\01\ai_materials.json
MPT task: ...
```

После завершения проверить новый:

```text
runtime/ready_for_review/slot-01-ru-ai.mp4
```

Ожидания для PASS:

- слышна русская озвучка;
- есть субтитры;
- кадры показывают осьминога как реальный видимый основной объект;
- нет человеческой кожи, случайных рыб, медуз, черепах и другого filler footage;
- смена кадров менее дёрганая, чем в первом 4-sec варианте.

Если новый vision gate не сможет найти 8 клипов, прислать полный текст ошибки и `runtime/slots/01/ai_materials.json`. Тогда добавлять второй бесплатный footage source.

## Дальше

Только после ручного PASS исправленного slot 1 переходить к slot 2 — русской animal compilation. Автопубликация по-прежнему выключена.
