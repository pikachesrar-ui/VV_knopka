# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст проекта для продолжения работы в новом чате.

Последнее содержательное обновление: **2026-08-28**.

---

## 1. Что это за проект

`pikachesrar-ui/VV_knopka` — review-first надстройка над MoneyPrinterTurbo и локальными инструментами монтажа для производства YouTube Shorts.

Цель пилота — сделать **15 review-ready роликов**, оценить качество и реакцию аудитории, и только после этого решать, насколько глубоко автоматизировать публикацию и аналитику.

Главная тема пилота: **Animals / Nature Curiosities**.

Два формата на одном тестовом канале:

1. `ai_short` — оригинальные короткие факты/истории о животных и природе;
2. `animal_compilation` — милые/смешные компиляции с собственной редакционной подачей.

---

## 2. Зафиксированный состав первых 15 роликов

- Всего: **15 Shorts**.
- **8 × `ai_short`**.
- **7 × `animal_compilation`**.
- Ровно **2 русских теста**: по одному на каждую ветку.
- Остальные **13 роликов — английские**.
- Всё пока публикуется на **один YouTube-канал**.
- **slot 1:** русский AI Short.
- **slot 2:** русская animal compilation.
- Остальные 13 не генерировать массово, пока глазами не проверены первые два результата.

---

## 3. Бюджет

Hard project-side OpenAI API budget: **$10 USD** на весь первый пилот.

Правила:

- лимит контролируется нашим локальным ledger;
- деньги/credits относятся к **OpenAI API Platform**, а не к ChatGPT Plus;
- `OPENAI_API_KEY` хранится только локально в `.env`;
- ключ нельзя коммитить или присылать в чат;
- не добавлять другие платные AI/TTS/video providers без отдельного решения пользователя;
- GPT используется для идей/структурированного сценария/метаданных;
- Edge TTS — бесплатный TTS по умолчанию;
- MoneyPrinterTurbo/FFmpeg — локальная обработка;
- дорогую text-to-video генерацию в первый пилот не включаем.

---

## 4. Контентные и YouTube-ограничения

Мы НЕ строим mass-upload AI spam bot.

- `auto_publish = false`;
- готовые видео идут в `runtime/ready_for_review`;
- перед публикацией обязателен человеческий просмотр;
- нельзя штамповать почти одинаковые ролики;
- duplicate/similarity gate должен оставаться включённым;
- сохраняем AI-disclosure metadata там, где это требуется;
- source provenance/copyright/reused-content риск учитывается до рендера.

### Animal compilations

Фиксированное правило: **никаких громких bass/drop/impact/boom SFX между клипами**.

Предпочтительно: micro-fades, естественный звук, тишина или очень мягкий переход.

Animal pipeline не должен по умолчанию работать как `скачать чужие TikTok/Shorts → склеить → перезалить`.

Для каждого клипа сохраняются:

- source URL/origin;
- license/permission metadata;
- явный `commercial_use_allowed`.

---

## 5. Git status / workflow

Репозиторий: `pikachesrar-ui/VV_knopka`.

- default branch: `main`;
- рабочая ветка: `mvp/pilot-scaffold`;
- текущий review vehicle: **draft PR #1 — `MVP: review-first 15-Short pilot scaffold`**;
- PR остаётся draft до ручной проверки первых двух видео;
- ничего не merge только потому, что тесты прошли;
- новый чат всегда перепроверяет актуальный PR head/CI через GitHub.

---

## 6. Что уже реализовано

### Pilot manifest

- фиксированный manifest на 15 роликов;
- split 8 AI / 7 animal;
- ровно 2 русских ролика;
- русский тест есть в каждой ветке.

### OpenAI planner

Structured output содержит:

- title;
- hook;
- script;
- footage/search terms;
- caption;
- hashtags;
- editorial value;
- fact-check items;
- AI-disclosure recommendation.

### Budget ledger

- считает фактический token usage;
- пишет usage локально;
- hard budget = $10;
- блокирует новые платные вызовы, если они могут вывести пилот за лимит.

### OpenAI auth diagnostics

После реального 401-инцидента добавлены:

- `vv doctor` — безопасно проверяет, что `OPENAI_API_KEY` загружен, не печатая сам ключ;
- проверка ключа через официальный OpenAI account-info endpoint `/v1/me` без token spend;
- безопасные объяснения 401/403/429;
- API error text очищается от возможных `sk-...` секретов;
- `plan` больше не должен отдавать пользователю сырой `httpx` traceback для типовых OpenAI API ошибок;
- добавлен unit test на redaction и понятную 401-диагностику.

### MoneyPrinterTurbo adapter

Интеграция строится через локальный API MoneyPrinterTurbo.

Проверено на upstream на 2026-08-28:

- API server обычно `127.0.0.1:8080`;
- API prefix `/api/v1`;
- video generation `/api/v1/videos`;
- task-status API присутствует;
- states: failed=`-1`, complete=`1`, processing=`4`.

### AI short pipeline

Есть:

- structured plan;
- MPT job submission;
- ожидание task completion;
- скачивание MP4;
- staging в review directory.

### Animal compilation pipeline

Есть локальный FFmpeg workflow:

- 9:16 output;
- `sources.json`;
- provenance/license gate;
- commercial-use flag;
- loudness normalization;
- micro-fades;
- никаких bass/drop/impact transition SFX.

### Review/quality gates

- duplicate/near-duplicate script protection;
- publication gate;
- human-review staging;
- `auto_publish=false`.

---

## 7. Windows bootstrap incident — исправлен

Первый setup на `D:\KiraS\VV_knopka` стартовал с системного Python `3.10.6`, из-за чего `.venv` была несовместима с `requires-python >=3.11`.

Первоначальный скрипт также не проверял `$LASTEXITCODE` внешних команд и после failed `pip install` ошибочно продолжал работу.

Исправлено:

- поиск/установка Python 3.11+;
- fallback через `uv`/`winget`;
- удаление несовместимой `.venv`;
- строгая проверка exit codes;
- существующий `.env` не перезаписывается;
- добавлен Windows bootstrap CI scenario, воспроизводящий старт с Python 3.10.6.

### Фактический повторный setup на ПК пользователя

Успешно подтверждено:

```text
.env already exists; keeping it unchanged.
manifest: D:\KiraS\VV_knopka\runtime\pilot_manifest.json
publication gate: PASS
.... [100%]
4 passed in 0.06s
VV_knopka setup complete.
```

Внутри `.venv`:

```text
Python 3.11.0
```

`vv status`:

```text
OpenAI spent: $0.0000 / $10.00
auto_publish: False
publication gate: PASS
```

---

## 8. Текущий OpenAI auth incident — 2026-08-28

Пользователь добавил `OPENAI_API_KEY` в локальный `.env` и запустил:

```powershell
.\.venv\Scripts\vv.exe plan 1
```

Запрос дошёл до `https://api.openai.com/v1/responses`, но OpenAI ответил:

```text
401 Unauthorized
```

Это означает, что генерация/модель ещё не запускались: запрос был отклонён на этапе аутентификации.

В ответ на этот инцидент в ветку добавлены `vv doctor` и safe OpenAI errors.

### Точная текущая точка продолжения

На ПК пользователя выполнить:

```powershell
git pull
.\.venv\Scripts\vv.exe doctor
```

`vv doctor` не должен печатать секрет и не тратит токены. Он показывает только тип/длину загруженного значения и результат auth-check.

Если результат снова `401` / `invalid_api_key`:

1. открыть OpenAI API Platform;
2. создать **новый secret API key** в нужном project;
3. заменить только значение `OPENAI_API_KEY=...` в локальном `.env`;
4. старый неверный/скомпрометированный ключ при необходимости удалить;
5. снова запустить `vv doctor`;
6. только после `OpenAI authentication: PASS` повторять `vv plan 1`.

Не просить пользователя присылать ключ в чат и не выводить содержимое `.env`.

После успешного `vv doctor`:

```powershell
.\.venv\Scripts\vv.exe plan 1
.\.venv\Scripts\vv.exe status
Get-Content .\runtime\slots\01\plan.json -Raw
```

Дальше проверить title/hook/script/search_terms/fact_check_items до установки MoneyPrinterTurbo и до рендера.

---

## 9. Следующий milestone после успешного plan 1

1. Проверить фактические claims slot 1 по надёжным источникам.
2. При необходимости скорректировать prompt/style.
3. Установить/запустить MoneyPrinterTurbo.
4. Проверить `http://127.0.0.1:8080/docs`.
5. Настроить footage provider и Edge TTS.
6. Render slot 1.
7. Получить MP4 в `runtime/ready_for_review`.
8. Пользователь вручную оценивает voice, pacing, hook, footage, subtitles, монтаж и AI-slop ощущение.
9. Затем подготовить source-tracked licensed clips и сделать slot 2.
10. Только после slots 1–2 переходить к остальным 13.

---

## 10. Что пока отложено

До первых двух роликов не делать без необходимости:

- automatic YouTube upload/publish;
- YouTube Analytics feedback loop;
- autonomous trend hunter;
- массовый batch остальных 13;
- social-media clip scraper;
- object-aware smart crop;
- heavy visual ranking model;
- analytics-driven content allocation;
- expensive text-to-video generation.

---

## 11. Что должен сделать новый чат

Если пользователь пишет «продолжаем VV_knopka»:

1. полностью прочитать `AGENT.md`;
2. полностью прочитать `docs/PROJECT_HANDOFF_RU.md`;
3. проверить актуальный `main`;
4. проверить `mvp/pilot-scaffold`;
5. проверить draft PR #1, head, changed files и CI;
6. если механические факты handoff устарели, GitHub является source of truth;
7. продолжить с последнего практического шага, не пересобирать архитектуру с нуля;
8. после существенного прогресса снова обновить этот handoff.
