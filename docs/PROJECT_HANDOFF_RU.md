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
- FFmpeg animal compilation pipeline;
- provenance/commercial-use gate для animal clips;
- review staging;
- context persistence: `AGENT.md`, `PROJECT_HANDOFF_RU.md`, `PROGRESS_RU.md`.

## 4. Подтверждённая локальная среда

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- bootstrap PASS;
- publication gate PASS;
- OpenAI key локально в `.env`;
- Pexels key локально в `.env`;
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

## 7. Footage relevance: реальные прогоны

### Strict slug gate

Требование `octopus` в Pexels page URL дало только **2/8**. Fail-closed правильный, но recall слишком низкий.

### Luna vision gate

Затем URL стал только metadata signal. GPT-5.6 Luna стал смотреть реальные Pexels previews.

Локальный прогон пользователя:

```text
9 passed in 0.10s
OpenAI spent before vision run: $0.0051 / $10.00
RuntimeError: Pexels visual relevance gate found only 2/8 usable clips after reviewing 30 previews for visible anchor 'octopus'.
```

Вывод: **visual gate работает, но каталог Pexels для этой темы недостаточен**. Не снижать confidence и не разрешать filler.

## 8. Текущий footage design: Pexels + Pixabay

Текущая ветка после этого FAIL:

1. `visual_anchor=octopus` обязателен.
2. Pexels и Pixabay — бесплатные stock providers.
3. Каждый candidate проходит Luna image review.
4. Accept только при `accepted=true` и confidence >= `0.72`.
5. Unrelated animals, human/human-skin, scenery-only и ambiguous frames блокируются.
6. Approved clips скачиваются локально и MPT получает `video_source=local` + explicit `video_materials`; MPT больше не выбирает stock вслепую.
7. Provenance, creator/source URLs, provider IDs и vision reasons сохраняются в `runtime/slots/XX/ai_materials.json`.
8. Pacing = **6 секунд на источник**.
9. Target = **8** уникальных source clips.
10. Если Pexels+Pixabay не дают 8, pipeline FAILS CLOSED.

### Важный cache behavior

Последний Pexels vision run уже просмотрел 30 previews и скачал 2 approved Pexels clips.

Новый код читает существующий `ai_materials.json` и:

- переиспользует эти 2 локальных approved Pexels clips;
- помнит, что Pexels preview budget уже exhausted;
- **не должен повторно платить за те же 30 Pexels vision checks**;
- ищет недостающие 6 через Pixabay.

`.env.example` уже содержит `PIXABAY_API_KEY=`.

Pixabay Video API используется напрямую VV_knopka; отдельная настройка MPT для Pixabay не нужна, потому что MPT получает уже скачанные local materials.

## 9. Точная текущая точка

Перед следующим render нужен бесплатный Pixabay API key в локальном `.env`:

```text
PIXABAY_API_KEY=...
```

После этого:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-ai 1
```

Не запускать `vv plan 1` снова.

При успехе material stage:

```text
Curated stock materials: 8
Material audit: D:\KiraS\VV_knopka\runtime\slots\01\ai_materials.json
MPT task: ...
```

После render проверить `runtime/ready_for_review/slot-01-ru-ai.mp4`.

PASS criteria:

- русская озвучка слышна;
- субтитры есть;
- каждый/практически каждый clip реально показывает осьминога;
- нет human skin / random fish / jellyfish / turtle filler;
- pacing приемлемый.

## 10. После PASS slot 1

Дальше slot 2 — русская cute/funny animal compilation с source-tracked licensed clips и мягкими переходами. Только после ручного review slots 1–2 переходить к остальным 13.

Отложено до этого: automatic publish, analytics feedback loop, trend hunter, social scraper, mass batch, expensive text-to-video.
