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
- PR остаётся draft, ничего не merge до ручного PASS первых двух видео;
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
- Pexels + Pixabay stock curator;
- GPT-5.6 Luna vision relevance gate;
- explicit local-material handoff в MPT;
- duration-based reuse approved long footage;
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
- MoneyPrinterTurbo v1.3.5 установлен в игнорируемую `MoneyPrinterTurbo`;
- MPT API работает на `127.0.0.1:8080`;
- `configure-mpt-windows.ps1` пишет TOML UTF-8 без BOM.

Первоначальный Python 3.10 bootstrap incident исправлен: setup сам обеспечивает 3.11+, проверяет exit codes и не перезаписывает `.env`.

## 5. Slot 1 plan

`vv plan 1` успешно создан.

Тема: **«Почему осьминог меняет цвет во сне»**.

Первый plan-вызов OpenAI стоил **$0.0051**. Fact-check PASS с оговоркой: изменения окраски/активность мозга во сне наблюдаются, но нельзя утверждать, что содержание сновидений осьминога доказано.

`vv plan 1` повторно не запускать без причины.

## 6. Первый render slot 1 — review FAIL

Первый MPT render технически завершился, но human review выявил:

1. скачанный `slot-01-ru-ai.mp4` был без звука;
2. Pexels footage включал fish/coral, jellyfish, turtle и human skin.

MPT сам корректно создал `audio.mp3`, `subtitle.srt`, `combined-1.mp4`, затем `final-1.mp4`.

### Sound root cause — исправлен

VV adapter выбирал `combined_videos` раньше `videos`. `combined_videos` — silent intermediate; `videos` — final output.

Теперь порядок: `videos` → fallback `combined_videos`. Есть regression tests.

## 7. Footage relevance — реальные прогоны

### Strict slug gate

Требование `octopus` в Pexels URL дало только **2/8**. Безопасно, но слишком низкий recall.

### Luna vision gate на Pexels

GPT-5.6 Luna просмотрел 30 Pexels previews и одобрил только **2** настоящих octopus clips. Это подтвердило, что основной visual gate работает, но каталог Pexels для узкой темы бедный.

### Pexels + Pixabay

После добавления Pixabay и того же Luna vision gate фактический локальный результат пользователя:

```text
RuntimeError: Multi-source visual relevance gate found only 3/8 usable clips for visible anchor 'octopus' after Pexels + Pixabay.
OpenAI spent: $0.0104 / $10.00
10 passed in 0.10s
```

Итого после двух бесплатных stock providers нашлось **3 реально одобренных исходника**. Это не повод ослаблять relevance: filler по-прежнему запрещён.

## 8. Текущая footage policy — качество по хронометражу, не по числу файлов

Проверен актуальный MoneyPrinterTurbo `combine_videos()`:

- в `sequential` mode для каждого source используется только первый segment;
- в `random` mode длинный source режется на несколько непересекающихся segment-ов;
- random mode сначала приоритизирует по одному segment от каждого unique source, затем использует следующие segment-ы этих же файлов как fallback для покрытия narration.

Поэтому прежняя цель `ai_material_count=8` остаётся **preferred target**, но больше не является абсолютным PASS requirement.

Для vision-approved cached footage допустим duration fallback:

- minimum unique approved sources = **3**;
- segment = **6 sec**;
- при quality-gate учитывается максимум **4 segment-а с одного source**;
- minimum reusable approved footage = **36 sec**;
- Luna confidence threshold остаётся `>=0.72`;
- никакие unrelated/human-skin/random-animal кадры не разрешаются;
- MPT curated footage теперь использует `video_concat_mode=random`, чтобы брать разные непересекающиеся части одобренных длинных файлов.

Это не означает визуальное дублирование одного и того же 6-секундного куска: MPT берёт последующие участки source timeline.

## 9. Cache / cost behavior

`runtime/slots/01/ai_materials.json` хранит approved material + vision audit.

Новая логика перед любыми новыми stock/vision запросами сначала пытается использовать cached approved sources по duration-gate.

Если cache содержит >=3 unique sources и >=36 sec reusable footage:

- новых Pexels/Pixabay запросов для поиска не требуется;
- новых Luna vision calls не требуется;
- OpenAI spend не должен увеличиться на material stage;
- MPT сразу получает cached local materials.

Если оба provider pool уже визуально проверены, а cache не проходит duration-gate, pipeline останавливается без повторной оплаты за те же previews.

## 10. Точная текущая точка

Последнее подтверждение пользователя перед новым duration fallback:

```text
OpenAI spent: $0.0104 / $10.00
10 passed in 0.10s
Multi-source visual relevance gate found only 3/8 usable clips ...
```

После новых commits на ПК пользователя выполнить:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-ai 1
```

`vv plan 1` НЕ запускать.

Если три cached source достаточно длинные, ожидается примерно:

```text
Reusing approved stock: 3 unique sources, XX.Xs reusable footage
Curated stock materials: 3
Material audit: D:\KiraS\VV_knopka\runtime\slots\01\ai_materials.json
MPT task: ...
```

Если reusable footage <36 sec, команда должна остановиться с точным числом секунд и сообщением `No additional vision calls were made`. В таком случае следующий предпочтительный вариант: supplement релевантными still images (Ken Burns/pan-zoom) либо ещё один бесплатный source; **не снижать visual relevance threshold**.

## 11. PASS criteria slot 1

После успешного MPT render проверить `runtime/ready_for_review/slot-01-ru-ai.mp4`:

- русская озвучка слышна;
- субтитры есть;
- каждый использованный segment действительно содержит осьминога;
- нет human skin / random fish / jellyfish / turtle filler;
- использование нескольких segment-ов одного source не выглядит навязчиво повторяющимся;
- pacing приемлемый.

## 12. После PASS slot 1

Дальше slot 2 — русская cute/funny animal compilation с source-tracked licensed clips и мягкими переходами. Только после ручного review slots 1–2 переходить к остальным 13.

Отложено до этого: automatic publish, analytics feedback loop, trend hunter, social scraper, mass batch, expensive text-to-video.
