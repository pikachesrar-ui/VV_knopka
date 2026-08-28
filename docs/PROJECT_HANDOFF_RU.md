# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст проекта для продолжения работы в новом чате.

Последнее содержательное обновление: **2026-08-28**.

---

## 1. Что это за проект

`pikachesrar-ui/VV_knopka` — наша надстройка над MoneyPrinterTurbo и локальными инструментами монтажа для производства YouTube Shorts.

Цель пилота — сделать **15 review-ready роликов**, посмотреть качество и реакцию аудитории, и только после этого решать, насколько глубоко автоматизировать публикацию и аналитику.

Главная тема канала на пилот:

**Animals / Nature Curiosities**

Так на одном канале можно тестировать два формата, не превращая его в случайную смесь тематик:

1. оригинальные короткие факты/истории о животных и природе;
2. милые/смешные компиляции с животными с собственной редакционной подачей.

---

## 2. Зафиксированный состав первых 15 роликов

Всего: **15 Shorts**.

- **8 × `ai_short`** — AI-assisted animal/nature facts/stories.
- **7 × `animal_compilation`** — cute/funny animal compilations.
- **2 русских теста всего**:
  - 1 русский `ai_short`;
  - 1 русский `animal_compilation`.
- **13 остальных роликов — на английском**.
- На пилоте всё выкладывается **на один YouTube-канал**.

Первые два тестовых слота:

- **slot 1:** русский AI Short;
- **slot 2:** русская animal compilation.

Остальные 13 не генерировать массово, пока глазами не проверены первые два результата.

---

## 3. Бюджет

На весь первый пилот заложено:

**$10 OpenAI API budget cap**.

Важно:

- это проектный лимит, который наш код контролирует локально;
- деньги/credits для OpenAI находятся на балансе OpenAI API, а не в подписке ChatGPT Plus;
- API key хранится только локально в `.env`;
- ключ нельзя коммитить в GitHub и не нужно присылать в чат;
- не добавлять другие платные AI/TTS/video providers без отдельного решения пользователя.

Текущая концепция стоимости:

- GPT используется для идей/структурированного сценария/метаданных;
- Edge TTS — бесплатный TTS по умолчанию;
- MoneyPrinterTurbo/FFmpeg — локальная обработка;
- Pexels/Pixabay/другие разрешённые источники — для материалов, где это подходит;
- дорогую AI video generation в первый пилот не включаем.

---

## 4. Правила контента и YouTube

Мы НЕ строим бездумный mass-upload AI spam bot.

Для пилота действуют следующие принципы:

- `auto_publish = false`;
- готовый результат складывается в `runtime/ready_for_review`;
- перед публикацией обязателен человеческий просмотр;
- нельзя делать много почти одинаковых роликов с одним шаблоном;
- duplicate/similarity gate должен оставаться включённым;
- сохраняем AI-disclosure metadata там, где это требуется;
- source provenance/copyright/reused-content риск учитывается до рендера.

### Animal compilations

Фиксированное правило:

**никаких громких bass/drop/impact/boom SFX между клипами.**

Предпочтительно:

- маленькие audio fades;
- естественный звук исходного клипа;
- тишина;
- очень мягкий переход, если он вообще нужен.

Animal pipeline не должен по умолчанию работать как:

> скачать чужие TikTok/Shorts → склеить → перезалить.

Для клипа должны сохраняться:

- source URL/origin;
- license/permission metadata;
- явный флаг commercial-use eligibility.

---

## 5. Репозиторий и Git status

Репозиторий:

`pikachesrar-ui/VV_knopka`

Default branch:

`main`

Текущая рабочая ветка:

`mvp/pilot-scaffold`

Текущий PR:

**draft PR #1 — `MVP: review-first 15-Short pilot scaffold`**

PR намеренно остаётся draft до проверки первых двух видео.

Важно: не считать PR готовым к merge только потому, что unit tests проходят.

Новый чат всегда должен перепроверять актуальный PR head и CI через GitHub.

---

## 6. Что уже реализовано в MVP

### Pilot manifest

- фиксированный manifest на 15 роликов;
- split 8 AI / 7 animal;
- ровно 2 русских ролика;
- русский тест есть в каждой ветке.

### OpenAI planner

Planner возвращает структурированные данные:

- hook;
- script;
- footage/search terms;
- caption;
- hashtags;
- список утверждений/фактов для проверки;
- recommendation/metadata для AI disclosure.

### Budget ledger

- считает фактическое token usage по ответам OpenAI;
- записывает API usage локально;
- hard project budget = $10;
- блокирует новые платные вызовы, если они могут вывести пилот за лимит.

### MoneyPrinterTurbo adapter

Интеграция через локальный API MoneyPrinterTurbo.

Проверено на upstream на 2026-08-28:

- API server обычно на `127.0.0.1:8080`;
- API prefix: `/api/v1`;
- video generation endpoint: `/api/v1/videos`;
- task-status API присутствует;
- states:
  - failed = `-1`;
  - complete = `1`;
  - processing = `4`.

### AI short pipeline

Есть:

- structured plan;
- MoneyPrinterTurbo job submission;
- ожидание task completion;
- скачивание результата;
- staging в review directory.

### Animal compilation pipeline

Есть отдельный локальный FFmpeg workflow:

- вертикальный 9:16 output;
- source/provenance gate;
- `sources.json` с provenance/license fields;
- commercial-use flag;
- audio loudness normalization;
- micro-fades;
- никаких bass/drop/impact transition SFX.

### Review/quality gates

Есть:

- duplicate/near-duplicate script protection;
- publication gate;
- human-review staging;
- `auto_publish=false`.

### Tests

Подтверждено на ПК пользователя 2026-08-28:

**4/4 tests PASS**.

GitHub Actions содержит Linux test job и отдельный Windows bootstrap job. Новый чат обязан перепроверять CI непосредственно в GitHub.

---

## 7. Windows bootstrap incident и исправление

Первый `scripts/setup-windows.ps1` был запущен на ПК пользователя в:

`D:\KiraS\VV_knopka`

Системный Python оказался `3.10.6`, поэтому первоначальный setup создал несовместимую `.venv` и `pip install` упал с:

```text
ERROR: Package 'vv-knopka' requires a different Python: 3.10.6 not in '>=3.11'
```

Старый bootstrap также не останавливался после ненулевых exit codes внешних программ, из-за чего появились вторичные `ModuleNotFoundError` для `vv_knopka` и `pytest`.

Исправлено в ветке:

- поиск/установка Python 3.11+;
- fallback через `uv`/`winget`;
- удаление несовместимой `.venv`;
- строгая проверка `$LASTEXITCODE`;
- существующий `.env` не перезаписывается;
- добавлен Windows bootstrap CI scenario.

### Фактический результат повторного setup на ПК пользователя

Повторный setup **успешно завершён**.

Подтверждено:

```text
.env already exists; keeping it unchanged.
manifest: D:\KiraS\VV_knopka\runtime\pilot_manifest.json
publication gate: PASS
.... [100%]
4 passed in 0.06s
VV_knopka setup complete.
```

Python внутри проекта:

```text
Python 3.11.0
```

`vv status`:

```text
OpenAI spent: $0.0000 / $10.00
auto_publish: False
publication gate: PASS
```

Пользователь также сообщил, что **добавил `OPENAI_API_KEY` в локальный `.env`**. Сам ключ в GitHub/чат не передавался.

---

## 8. Точная текущая точка продолжения

Локальная база проекта полностью готова.

Следующий шаг — **проверить реальный OpenAI вызов на slot 1 до установки MoneyPrinterTurbo**.

Команда на ПК пользователя:

```powershell
.\.venv\Scripts\vv.exe plan 1
```

Ожидаемый результат:

- один небольшой OpenAI API вызов;
- создаётся `runtime/slots/01/plan.json`;
- budget ledger становится > $0.0000, но остаётся далеко ниже $10;
- ничего не рендерится и ничего не публикуется.

После этого нужно:

1. посмотреть полный вывод команды;
2. открыть/прочитать `runtime/slots/01/plan.json`;
3. проверить title/hook/script/search_terms/fact_check_items;
4. проверить реальные фактические claims сценария по надёжным источникам;
5. при необходимости скорректировать planner/prompt до рендера;
6. только затем установить/запустить MoneyPrinterTurbo;
7. убедиться, что `http://127.0.0.1:8080/docs` доступен;
8. настроить footage provider и Edge TTS;
9. render slot 1;
10. получить MP4 в `runtime/ready_for_review` и проверить глазами.

---

## 9. Следующий milestone после slot 1

После успешного русского AI Short:

1. подготовить лицензированные/source-tracked clips;
2. сделать slot 2 — русскую animal compilation;
3. проверить переходы/звук/темп;
4. скорректировать оба формата;
5. только после этого переходить к остальным 13.

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
