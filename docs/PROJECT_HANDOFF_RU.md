# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл — для продуктовых решений и точки продолжения.

Последнее содержательное обновление: **2026-08-28**.

## 1. Frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.

Цель: review-first pipeline для 15 YouTube Shorts в нише **Animals / Nature Curiosities**.

Зафиксировано:

- 15 Shorts;
- 8 × `ai_short`;
- 7 × `animal_compilation`;
- slot 1 = русский AI Short;
- slot 2 = русская animal compilation;
- остальные 13 = English;
- пока один канал;
- OpenAI hard project budget = **$10**;
- `auto_publish=false`;
- human review обязателен;
- output только в `runtime/ready_for_review`;
- не добавлять новые платные providers без отдельного решения пользователя.

Animal compilations: никакого loud bass/drop/impact/boom SFX; source/provenance и commercial-use eligibility обязательны; raw social repost pipeline запрещён как default.

## 2. Git workflow

- default branch: `main`;
- рабочая ветка: `mvp/pilot-scaffold`;
- draft PR #1: `MVP: review-first 15-Short pilot scaffold`;
- PR не merge до ручного PASS первых двух видео;
- новый чат сначала полностью читает `AGENT.md`, этот файл и `docs/PROGRESS_RU.md`, затем проверяет live GitHub state/CI.

## 3. Реализовано

- deterministic 15-slot manifest;
- OpenAI Responses API structured planner;
- token/cost budget ledger;
- duplicate/script similarity/publication gates;
- MoneyPrinterTurbo `/api/v1` adapter;
- Windows bootstrap VV_knopka;
- Windows setup/config/start scripts для MPT;
- Edge TTS + Edge subtitles;
- multi-source stock curator с Pexels + Pixabay;
- GPT-5.6 Luna vision relevance gate;
- local explicit-material handoff в MPT;
- duration-based approved-footage fallback;
- FFmpeg animal compilation pipeline;
- provenance/commercial-use gate для animal clips;
- review staging;
- context persistence: `AGENT.md`, `PROJECT_HANDOFF_RU.md`, `PROGRESS_RU.md`.

## 4. Подтверждённая локальная среда

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- bootstrap PASS;
- publication gate PASS;
- OpenAI/Pexels/Pixabay keys локально в `.env`;
- MoneyPrinterTurbo v1.3.5 установлен в ignored `MoneyPrinterTurbo`;
- MPT API работает на `127.0.0.1:8080`;
- последний известный OpenAI ledger после material vision: **$0.0104 / $10.00**.

## 5. Slot 1 plan

`vv plan 1` успешно создан.

Тема: **«Почему осьминог меняет цвет во сне»**.

Первый plan-вызов OpenAI стоил **$0.0051**. Fact-check PASS с оговоркой: изменения окраски/активность мозга во сне наблюдаются, но нельзя утверждать, что содержание сновидений осьминога доказано.

`vv plan 1` повторно не запускать без причины.

## 6. Первый render slot 1 — FAIL

Первый MPT render технически завершился, но review выявил:

1. скачанный review MP4 был без звука;
2. blind Pexels selection подмешал fish/coral, jellyfish, turtle и human skin.

Sound bug исправлен: VV adapter теперь скачивает `videos` (final output), а не промежуточный `combined_videos`.

## 7. Footage relevance evolution

- strict Pexels URL/slug gate: `2/8`;
- GPT-5.6 Luna visual review 30 Pexels previews: `2/8`;
- Pexels + Pixabay visual review: всего `3/8` unique source videos;
- вывод: relevance gate работает, но 8 отдельных исходников — неправильный hard requirement для узких тем.

Текущий gate:

- visual anchor обязателен (`octopus` для slot 1);
- candidate проходит только Luna image review `accepted=true` + confidence >= `0.72`;
- minimum unique approved sources = **3**;
- clip segment = **6 sec**;
- max reusable segments per source for capacity = **4**;
- minimum reusable approved footage = **36 sec**;
- filler/relevance threshold не ослабляется;
- MPT curated footage использует `video_concat_mode=random`, чтобы сначала использовать уникальные sources, затем непересекающиеся segments длинных sources.

## 8. Второй render slot 1 — TECHNICAL PASS, QUALITY PASS ещё нет

MPT task: `d4e53d76-3be1-49f3-9dc2-fe6a944967ab`.

Пользователь просмотрел итог и сообщил: **звук есть, результат достойный, но надо дорабатывать**.

Подтверждено из task log:

- narration audio ~36.82 sec;
- Edge subtitle file создан;
- 3 approved source videos: 2 portrait Pexels + 1 landscape Pixabay;
- MPT создал 17 available source segments и использовал 9 segments;
- final MP4 успешно создан.

### Quality-проблемы по human review

1. Русские subtitles выглядят плохо: разреженные буквы, агрессивный wrap, слово `хроматофоры` визуально разорвано между строками.
2. Landscape Pixabay footage показан с огромными black bars в 9:16.
3. Некоторые переходы затемняют кадр.
4. Один long Pixabay source используется несколькими непересекающимися segments; пока допустимо, но следить за заметной повторяемостью.

Root causes:

- MPT task использовал `STHeitiMedium.ttc` для русского;
- MPT mismatch-aspect code сохраняет landscape целиком на black canvas;
- `FadeIn` применяется **к каждому source segment отдельно**, то есть fade-from-black, а не настоящий crossfade.

## 9. Текущий quality-fix в рабочей ветке

Внесено до следующего render:

- `visual_transition = none` — чистые cuts вместо per-clip fade-from-black;
- для русского VV_knopka локально копирует установленный Windows Cyrillic font в ignored MPT runtime: приоритет Arial Bold -> Segoe UI Bold -> Arial -> Segoe UI;
- никакой font binary не попадает в Git;
- Russian subtitles: size **46**, position `custom`, vertical position **68%**, stroke width **2.2**;
- landscape local stock до MPT автоматически конвертируется в **1080x1920 blur-fill**:
  - blurred zoomed source fills background;
  - полный sharp original frame остаётся по центру;
  - black bars исчезают;
- portrait sources не транскодируются;
- derived `*-vv916.mp4` кэшируется локально;
- script/plan/vision-approved source set не меняются;
- новых OpenAI calls для этой quality-проверки не требуется.

## 10. Точная текущая точка

MPT API можно оставить запущенным. На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-ai 1
```

`vv plan 1` НЕ запускать.

При первом render после quality-fix один landscape Pixabay source будет локально transcoded в `*-vv916.mp4`; это может добавить паузу до создания MPT task, но OpenAI budget не расходует.

Проверить `runtime/ready_for_review/slot-01-ru-ai.mp4`:

- звук есть;
- Cyrillic subtitles выглядят естественно;
- нет странного межбуквенного spacing;
- subtitle placement не конфликтует с нижним UI Shorts;
- black bars исчезли;
- нет fade-from-black на каждом clip;
- footage всё ещё про осьминога;
- повторяемость long source не раздражает.

Только после **manual QUALITY PASS slot 1** переходить к slot 2 — русской cute/funny animal compilation.

Отложено: automatic publish, analytics feedback loop, trend hunter, social scraper, mass batch, expensive text-to-video.
