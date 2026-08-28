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

### Root cause звука

MoneyPrinterTurbo корректно создал:

- `audio.mp3`;
- `subtitle.srt`;
- промежуточный `combined-1.mp4`;
- финальный `final-1.mp4`.

Наш adapter ошибочно предпочитал `combined_videos` перед `videos`, поэтому скачивал промежуточную silent visual concat вместо финального файла.

Исправлено: `download_video()` теперь предпочитает `task["videos"]` и использует `combined_videos` только как fallback. Добавлены regression tests.

### Root cause материалов

MPT получил 5 Pexels search terms, нашёл 19–20 кандидатов на каждый и автоматически выбрал 10 клипов. Pexels search semantics слишком широкая: запросы вроде `octopus skin texture macro` способны возвращать человеческую кожу, а reef/underwater terms — других морских животных.

Исправление в VV_knopka:

- больше не доверяем автоматическому Pexels selection внутри MPT для `ai_short`;
- перед рендером VV_knopka сам запрашивает Pexels;
- из плана берётся/выводится обязательный `visual_anchor` (для текущего slot 1 это `octopus`);
- кандидат проходит только если Pexels page slug явно содержит visual anchor;
- нерелевантные `skin`, fish/coral, turtle/jellyfish clips блокируются до скачивания;
- выбираются 8 уникальных portrait clips;
- provenance сохраняется в `runtime/slots/01/ai_materials.json`;
- выбранные клипы скачиваются в MPT `storage/local_videos` и передаются MPT как explicit local materials;
- если 8 релевантных клипов не найдено, pipeline FAILS CLOSED вместо filler footage.

Также pacing изменён с 4 до **6 секунд на источник**: на 25–45 секунд теперь достаточно максимум ~8 клипов вместо 10–12 быстрых смен.

Для будущих планов OpenAI structured output теперь содержит `visual_anchor`, и каждый footage search term обязан включать этот anchor.

## Дополнительный фикс MPT config

`configure-mpt-windows.ps1` раньше писал `config.toml` через Windows PowerShell UTF-8 с BOM. MPT успешно делал compatibility retry, но показывал TOML warning. Теперь файл записывается UTF-8 **без BOM**.

## Точная следующая точка

MPT API можно оставить запущенным. В другом PowerShell из `D:\KiraS\VV_knopka`:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe render-ai 1
```

Повторно запускать `vv plan 1` **не нужно**: текущий plan сохраняется, для него visual anchor автоматически выводится как `octopus`.

Новый `render-ai 1` должен сначала вывести примерно:

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
- все/практически все кадры действительно показывают осьминога;
- нет человеческой кожи, случайных рыб, медуз, черепах и другого filler footage;
- смена кадров менее дёрганая (6 сек вместо 4).

Если relevance gate не сможет найти 8 клипов, прислать полный текст ошибки и `runtime/slots/01/ai_materials.json`; не ослаблять gate вслепую.

## Дальше

Только после ручного PASS исправленного slot 1 переходить к slot 2 — русской animal compilation. Автопубликация по-прежнему выключена.
