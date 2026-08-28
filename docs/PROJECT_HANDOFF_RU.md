# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст проекта для продолжения работы в новом чате. GitHub является source of truth для кода/commit/CI, этот файл — для продуктовых решений и точки продолжения.

Последнее содержательное обновление: **2026-08-28**.

## 1. Цель и frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.

Проект — review-first надстройка над MoneyPrinterTurbo и локальными инструментами для YouTube Shorts.

Пилот зафиксирован:

- 15 Shorts всего;
- 8 × `ai_short`;
- 7 × `animal_compilation`;
- slot 1 = русский AI Short;
- slot 2 = русская animal compilation;
- остальные 13 = English;
- пока один YouTube-канал;
- ниша: **Animals / Nature Curiosities**;
- OpenAI project-side hard budget = **$10**;
- `auto_publish=false`;
- human review обязателен;
- результат только в `runtime/ready_for_review`;
- не добавлять новые платные providers без отдельного решения пользователя.

Animal compilations: никакого loud bass/drop/impact/boom transition SFX; только мягкие fades/естественный звук/тишина. Нельзя строить default workflow как raw TikTok/Shorts reupload; source/provenance и commercial-use eligibility обязательны.

## 2. Git workflow

- default branch: `main`;
- рабочая ветка: `mvp/pilot-scaffold`;
- draft PR #1: `MVP: review-first 15-Short pilot scaffold`;
- PR не merge до ручного PASS первых двух роликов;
- новый чат должен прочитать `AGENT.md`, этот файл и `docs/PROGRESS_RU.md`, затем проверить live GitHub state/CI.

## 3. Что реализовано

- deterministic 15-slot manifest;
- OpenAI Responses API structured planner;
- token/cost budget ledger;
- duplicate/script similarity/publication gates;
- MoneyPrinterTurbo `/api/v1` adapter;
- Windows bootstrap для VV_knopka;
- Windows setup/config/start scripts для MoneyPrinterTurbo;
- Pexels footage provider;
- Edge TTS + Edge subtitles;
- FFmpeg animal compilation pipeline;
- provenance/commercial-use gate для animal clips;
- review staging;
- context persistence: `AGENT.md`, `PROJECT_HANDOFF_RU.md`, `PROGRESS_RU.md`.

## 4. Подтверждённая локальная среда

ПК пользователя:

- project path: `D:\KiraS\VV_knopka`;
- Python внутри `.venv`: `3.11.0`;
- bootstrap PASS;
- publication gate PASS;
- OpenAI key хранится локально в `.env`;
- Pexels key хранится локально в `.env`;
- MoneyPrinterTurbo v1.3.5 установлен в игнорируемую папку `MoneyPrinterTurbo`;
- MPT API успешно запускается на `127.0.0.1:8080`.

Первоначальный Python 3.10 bootstrap incident уже исправлен: setup сам обеспечивает Python 3.11+, проверяет exit codes и не перезаписывает `.env`.

`configure-mpt-windows.ps1` теперь пишет MPT `config.toml` как UTF-8 **без BOM**, чтобы убрать compatibility warning.

## 5. OpenAI slot 1

Первый неверный API key дал 401; пользователь исправил значение, проблема была не в коде/API.

`vv plan 1` успешно создан.

Стоимость первого OpenAI вызова:

**$0.0051 / $10.00**.

Тема slot 1: **«Почему осьминог меняет цвет во сне»**.

Fact-check PASS с оговоркой: изменения окраски во сне и wake-like neural activity наблюдались, но нельзя утверждать, что содержание сновидений осьминога доказано.

Повторно генерировать plan 1 пока не нужно.

## 6. Первый render slot 1 — FAIL по review

Первый `vv render-ai 1` успешно завершил MPT task и создал MP4, но human review выявил две проблемы:

1. скачанный `runtime/ready_for_review/slot-01-ru-ai.mp4` был полностью без звука;
2. footage оказался нерелевантным: вместе с осьминогами были рыбы/кораллы, медузы, черепахи и человеческая кожа.

MPT log подтвердил, что TTS/субтитры сами по себе работали: `audio.mp3`, `subtitle.srt`, `combined-1.mp4` и затем финальный `final-1.mp4` были созданы.

### Root cause звука — исправлен

Наш `MoneyPrinterTurboClient.download_video()` выбирал `combined_videos` раньше `videos`. `combined_videos` — промежуточная visual-only склейка; `videos` — финальный output.

Исправлено на `videos` → fallback `combined_videos`. Есть regression test.

## 7. Footage relevance: два этапа исправления

Старый режим позволял MPT самому выбирать Pexels results. Pexels search оказался слишком широким: `octopus skin texture macro` способен вернуть human skin, а reef/underwater terms — других морских животных.

### Попытка 1: strict slug gate — безопасно, но слишком мало recall

VV_knopka начал сам запрашивать Pexels и требовать, чтобы URL/source page slug содержал обязательный `visual_anchor` (`octopus`). Это не пропускает очевидный filler, но на реальном slot 1 после локальных `8 passed` команда `vv render-ai 1` завершилась до MPT с:

```text
Pexels relevance gate found only 2/8 usable clips whose source page explicitly matches visual anchor 'octopus'.
```

Это правильный fail-closed, но slug нельзя использовать как основной визуальный критерий.

### Попытка 2: текущий дизайн — GPT-5.6 Luna vision gate

URL slug теперь только дополнительный metadata signal.

Текущий pipeline для `ai_short`:

1. VV_knopka сам делает Pexels search до MPT task.
2. `visual_anchor` — обязательный видимый главный объект. Для старого slot 1 он автоматически выводится как `octopus`.
3. Для будущих plans `visual_anchor` отдельный structured field; каждый `search_term` обязан включать его.
4. Собирается максимум **30** уникальных portrait Pexels candidates длительностью >= текущих 6 сек.
5. Из Pexels берётся preview image каждого candidate.
6. **GPT-5.6 Luna** через Responses API и image input проверяет preview батчами по 10.
7. Принимается только candidate, где main subject реально виден; unrelated animals, human/human skin, scenery-only, drawings/text и ambiguous close-ups отклоняются.
8. Требуется `accepted=true` и confidence >= **0.72**.
9. Как только набрано **8** approved clips, они скачиваются в `MoneyPrinterTurbo/storage/local_videos`.
10. Provenance + vision decisions сохраняются в `runtime/slots/XX/ai_materials.json`.
11. MPT получает explicit `video_source=local` materials, а не делает blind Pexels selection.
12. Если после максимум 30 preview нет 8 approved clips — pipeline снова **fails closed**. Следующий шаг тогда второй бесплатный footage provider, а не ослабление проверки.

Vision model использует тот же `OPENAI_API_KEY` и тот же hard project ledger **$10**. Config: `gpt-5.6-luna`, batch 10, max 30 candidates, min confidence 0.72, safety reservation до `$0.03` на один vision call; ledger пишет фактический token cost.

Проверено по актуальной документации OpenAI 2026-08-28: latest GPT-5.6 models поддерживают image input через Responses API; Luna текущая цена $0.20/M input и $1.20/M output.

Pacing остаётся **6 сек на источник** вместо первых 4 сек.

## 8. Точная текущая точка продолжения

MPT API можно оставить запущенным. На ПК пользователя в другом PowerShell:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-ai 1
```

Не запускать `vv plan 1` снова перед этим.

Новый `render-ai 1` потратит небольшой объём OpenAI API budget на Luna vision. При успехе ожидается:

```text
Curated Pexels materials: 8
Material audit: D:\KiraS\VV_knopka\runtime\slots\01\ai_materials.json
MPT task: ...
```

После рендера проверить новый `runtime/ready_for_review/slot-01-ru-ai.mp4`.

PASS criteria:

- русская озвучка слышна;
- субтитры есть;
- кадры показывают осьминога как реально видимый основной объект;
- нет human skin / random fish / jellyfish / turtle filler;
- pacing выглядит спокойнее и осмысленнее.

Если vision gate не найдёт 8 материалов, прислать полный вывод и `runtime/slots/01/ai_materials.json`; тогда добавить второй бесплатный footage source.

## 9. После PASS slot 1

Дальше slot 2 — русская cute/funny animal compilation с source-tracked licensed clips и мягкими переходами. Только после ручного review slots 1–2 переходить к остальным 13.

До этого остаются отложены: automatic publish, analytics feedback loop, autonomous trend hunter, social scraper, mass batch, expensive text-to-video.
