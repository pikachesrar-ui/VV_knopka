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

Первые два тестовых слота задуманы как:

- **slot 1:** русский AI Short;
- **slot 2:** русская animal compilation.

Остальные 13 не стоит массово генерировать, пока глазами не проверены первые два результата.

---

## 3. Бюджет

На весь первый пилот заложено:

**$10 OpenAI API budget cap**.

Важно:

- это проектный лимит, который наш код контролирует локально;
- деньги/credits для OpenAI должны находиться на балансе OpenAI API, а не в подписке ChatGPT Plus;
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
- source provenance/copyright/reused-content риск учитывается до рендера, а не после жалобы/демонетизации.

### Animal compilations

Пользователь отдельно попросил избавиться от раздражающих громких bass transitions.

Фиксированное правило:

**никаких громких bass/drop/impact/boom SFX между клипами.**

Предпочтительно:

- маленькие audio fades;
- естественный звук исходного клипа;
- тишина;
- очень мягкий переход, если он вообще нужен.

Также animal pipeline не должен по умолчанию работать как:

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

На момент создания этого handoff:

- первоначальный `main` содержит bootstrap README;
- основной MVP находится в `mvp/pilot-scaffold`;
- draft PR #1 открыт против `main`;
- до добавления этих handoff-файлов последний известный PR head был `a2bf842da2d14db6777827fac1b9d6f50a9183aa`;
- `AGENT.md` добавлен отдельным коммитом `19ccc864780df7dd920ca6d6a6422541d58cd7b7`;
- этот файл добавляется следующим коммитом, поэтому новый чат должен всегда перепроверять актуальный PR head через GitHub.

---

## 6. Что уже реализовано в MVP

На текущем этапе в ветке уже сделаны основные строительные блоки:

### Pilot manifest

- фиксированный manifest на 15 роликов;
- проверяется split 8 AI / 7 animal;
- проверяется ровно 2 русских ролика;
- проверяется, что русский тест есть в каждой ветке.

### OpenAI planner

Planner возвращает структурированные данные, а не просто свободный текст.

В план ролика входят как минимум:

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
- имеет hard project budget = $10;
- должен блокировать новые платные вызовы, если они могут вывести пилот за лимит.

### MoneyPrinterTurbo adapter

Наш проект не вендорит весь MoneyPrinterTurbo внутрь себя.

Интеграция строится через актуальный локальный API MoneyPrinterTurbo.

Проверено на upstream на 2026-08-28:

- API server обычно на `127.0.0.1:8080`;
- API prefix: `/api/v1`;
- video generation endpoint: `/api/v1/videos`;
- task-status API присутствует;
- известные states MoneyPrinterTurbo:
  - failed = `-1`;
  - complete = `1`;
  - processing = `4`.

MoneyPrinterTurbo поддерживает Windows 10+, Python 3.11+, Edge TTS и portrait 9:16.

### AI short pipeline

На уровне scaffold уже предусмотрено:

- structured plan;
- MoneyPrinterTurbo job submission;
- ожидание task completion;
- скачивание результата;
- staging в review directory.

### Animal compilation pipeline

Есть отдельный локальный FFmpeg workflow.

Текущие правила:

- вертикальный 9:16 output;
- source/provenance gate;
- минимум несколько источников/клипов для компиляции;
- `sources.json` с provenance/license fields;
- commercial-use flag должен быть разрешён;
- audio loudness normalization;
- micro-fades;
- никаких bass/drop/impact transition SFX.

### Review/quality gates

Уже заложены:

- duplicate/near-duplicate script gate;
- publication gate;
- human review staging;
- `auto_publish=false`.

### Windows/bootstrap

Добавлен Windows setup script и quick-start документация для локального развёртывания.

---

## 7. Тесты

Последний подтверждённый локальный результат перед созданием handoff:

**4/4 tests PASS**.

Проверки охватывают как минимум:

- правильный 15-slot manifest;
- 8/7 split;
- русский split;
- duplicate-script protection;
- отключённую автопубликацию/publication gate.

GitHub Actions workflow был добавлен после основного scaffold, но в момент последней проверки workflow run ещё не появился.

Поэтому НЕЛЬЗЯ писать, что CI PASS, пока новый чат не проверит Actions напрямую.

---

## 8. Что пока НЕ сделано / осознанно отложено

Пока нет необходимости делать это до первых тестовых видео:

- автоматический upload/publish на YouTube;
- YouTube Analytics feedback loop;
- полностью автономный trend hunter;
- массовое batch-production оставшихся 13 роликов;
- автоматический сбор чужих animal clips из соцсетей;
- object-aware/AI smart crop животных;
- sophisticated visual-ranking model для отбора лучших моментов;
- automatic analytics-driven niche allocation;
- дорогая text-to-video генерация.

Эти функции нужно добавлять после проверки качества первых роликов, а не раньше.

---

## 9. Выбранная ниша

Для первого пилота выбрана:

**Animals / Nature Curiosities**.

Логика выбора:

- animal Shorts сохраняют высокий viral potential;
- cute/funny animal footage подходит для очень короткого формата;
- animal facts/stories естественно объединяются с компиляциями на одном канале;
- это лучше для одного канала, чем случайная смесь `space facts + history + cats + finance`;
- ниша позволяет тестировать и реальные клипы, и AI-assisted narrative в рамках одной аудитории.

Это рабочая гипотеза пилота, а не обещание монетизации или просмотров.

---

## 10. Следующий практический шаг на ПК пользователя

Ранее пользователю были даны команды:

```powershell
git clone https://github.com/pikachesrar-ui/VV_knopka.git
cd VV_knopka
git checkout mvp/pilot-scaffold

powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

После setup должен появиться локальный `.env`.

В него пользователь самостоятельно добавляет:

```text
OPENAI_API_KEY=...
```

Ключ не публиковать и не отправлять в чат.

Затем предполагаемый status check:

```powershell
.\.venv\Scripts\vv.exe status
```

Ожидаемая логика результата:

- OpenAI spent около `$0.0000 / $10.00` на чистом запуске;
- `auto_publish: False`;
- publication gate должен быть безопасным/закрытым для автопубликации.

### После этого

1. Проверить вывод setup/status пользователя.
2. Установить/запустить MoneyPrinterTurbo на Windows.
3. Настроить нужные бесплатные material sources/API keys, если требуются.
4. Сделать **slot 1 — русский AI Short**.
5. Получить MP4 в `runtime/ready_for_review`.
6. Пользователь смотрит ролик глазами и оценивает:
   - голос;
   - темп;
   - hook;
   - подбор кадров;
   - субтитры;
   - монтаж;
   - ощущение AI-slop/не AI-slop.
7. Исправить стиль по результату.
8. Подготовить источники для **slot 2 — русской animal compilation**.
9. Сделать slot 2 и проверить переходы/звук.
10. Только после двух успешных тестов планировать остальные 13.

---

## 11. Что должен сделать новый чат в самом начале

Если пользователь пишет что-то вроде «продолжаем VV_knopka»:

1. Через GitHub полностью прочитать:
   - `AGENT.md`;
   - `docs/PROJECT_HANDOFF_RU.md`.
2. Проверить актуальный `main`.
3. Проверить ветку `mvp/pilot-scaffold`.
4. Проверить draft PR #1, его текущий head и CI/checks.
5. Сравнить GitHub state с этим handoff и обновить handoff, если механические данные устарели.
6. Продолжить ровно с последнего практического шага, а не пересобирать архитектуру с нуля.

---

## 12. Как поддерживать handoff дальше

Этот файл должен обновляться после каждого значимого этапа, например:

- пользователь успешно установил проект;
- изменились команды запуска;
- появился новый provider/API;
- поменялся бюджет;
- изменился состав 15 роликов;
- отрендерен slot 1/2/etc;
- выявлен баг;
- изменён стиль видео;
- появился новый PR/branch;
- PR merged/closed;
- появилась автоматическая публикация;
- начался сбор YouTube Analytics.

Цель: чтобы новый чат мог восстановить проект почти полностью только из GitHub.
