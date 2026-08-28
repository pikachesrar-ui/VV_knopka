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

MPT log подтвердил, что TTS/субтитры сами по себе работали:

- `audio.mp3` создан Edge TTS;
- `subtitle.srt` создан;
- `combined-1.mp4` создан;
- затем MPT создал финальный `final-1.mp4` с audio/subtitles.

### Root cause звука — исправлен

Наш `MoneyPrinterTurboClient.download_video()` ошибочно выбирал:

`combined_videos` → `videos`.

Но `combined_videos` — промежуточная visual-only склейка, а `videos` — финальный output.

Исправлено на:

`videos` → fallback `combined_videos`.

Добавлены regression tests.

## 7. Root cause footage и новый relevance gate

Старый режим отдавал MPT поисковые фразы и позволял MPT самому выбирать Pexels результаты. На каждый term Pexels вернул около 19–20 кандидатов, но semantic relevance недостаточна: `octopus skin texture macro` может вернуть human skin, reef/underwater — других морских животных.

Новый режим для `ai_short`:

1. VV_knopka сам запрашивает Pexels до запуска MPT task.
2. Вводится `visual_anchor` — обязательный видимый основной объект. Для текущего slot 1 он автоматически выводится из старого plan как `octopus`.
3. Для будущих OpenAI plans `visual_anchor` является отдельным structured field; каждый `search_term` обязан содержать его.
4. Pexels candidate принимается только если source page slug явно содержит visual anchor.
5. Выбираются **8 уникальных portrait clips**.
6. Каждый source должен быть минимум длиной текущего clip duration.
7. Provenance записывается в `runtime/slots/XX/ai_materials.json`.
8. Клипы скачиваются в `MoneyPrinterTurbo/storage/local_videos`.
9. MPT получает их как explicit `video_source=local` materials вместо собственного blind Pexels selection.
10. Если 8 релевантных клипов не найдено — pipeline **fails closed**, filler footage не допускается.

Pacing после первого review изменён с **4 сек → 6 сек на источник**. Для 25–45 секунд достаточно до 8 источников, меньше быстрых смен и меньше вероятность нерелевантного кадра.

## 8. Точная текущая точка продолжения

MPT API можно оставить запущенным. На ПК пользователя в другом PowerShell:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe render-ai 1
```

Не запускать `vv plan 1` снова перед этим.

Ожидаем перед MPT task:

```text
Curated Pexels materials: 8
Material audit: D:\KiraS\VV_knopka\runtime\slots\01\ai_materials.json
MPT task: ...
```

После рендера проверить новый:

`runtime/ready_for_review/slot-01-ru-ai.mp4`.

PASS criteria:

- русская озвучка слышна;
- субтитры есть;
- кадры действительно показывают осьминога;
- нет human skin / random fish / jellyfish / turtle filler;
- pacing выглядит спокойнее и осмысленнее.

Если relevance gate не найдёт 8 материалов, не ослаблять его вслепую: прислать полный вывод и `runtime/slots/01/ai_materials.json`.

## 9. После PASS slot 1

Дальше slot 2 — русская cute/funny animal compilation с source-tracked licensed clips и мягкими переходами. Только после ручного review slots 1–2 переходить к остальным 13.

До этого остаются отложены: automatic publish, analytics feedback loop, autonomous trend hunter, social scraper, mass batch, expensive text-to-video.
