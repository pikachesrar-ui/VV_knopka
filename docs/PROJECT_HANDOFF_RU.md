# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст проекта для продолжения работы в новом чате.

Последнее содержательное обновление: **2026-08-28**.

## 1. Что это за проект

Репозиторий: `pikachesrar-ui/VV_knopka`.

Это review-first конвейер для производства YouTube Shorts поверх OpenAI API, MoneyPrinterTurbo и локального FFmpeg.

Цель первого пилота — сделать **15 review-ready роликов**, вручную проверить первые результаты и только затем решать, насколько глубоко автоматизировать публикацию, аналитику и масштабирование.

Общая ниша пилота: **Animals / Nature Curiosities**.

Два формата:

1. `ai_short` — оригинальные короткие факты/истории о животных и природе с AI-assisted сценарием;
2. `animal_compilation` — милые/смешные компиляции животных с собственной редакционной подачей.

## 2. Зафиксированный пилот

До отдельного решения пользователя параметры не менять:

- 15 Shorts всего;
- 8 × `ai_short`;
- 7 × `animal_compilation`;
- ровно 2 русских теста: по одному на каждый pipeline;
- slot 1 = русский AI Short;
- slot 2 = русская animal compilation;
- остальные 13 — английские;
- всё пока публикуется на один YouTube-канал;
- hard project-side OpenAI API budget = **$10**;
- `auto_publish = false`;
- готовые видео идут только в `runtime/ready_for_review`;
- никаких громких `bass/drop/impact/boom` SFX между animal-клипами.

Не производить оставшиеся 13 роликов массово до визуальной проверки slots 1–2.

## 3. Контентные и YouTube-ограничения

Проект не должен превращаться в mass-upload AI spam bot.

Обязательные правила:

- human review перед публикацией;
- duplicate/near-duplicate checks не отключать;
- AI-disclosure metadata сохранять, когда требуется;
- animal pipeline не должен быть простым `скачал чужой TikTok → склеил → перезалил`;
- каждый animal clip должен иметь source/provenance metadata;
- commercial-use permission/licensing должен быть явно отмечен;
- reused-content/copyright риск учитывается до рендера;
- для переходов использовать natural audio, micro-fades, silence или очень мягкую обработку, но не громкий bass impact.

## 4. Бюджет

На пилот зафиксировано **$10 OpenAI API**.

- API key хранится только локально в `.env`;
- `.env` не коммитить;
- ключ не присылать в чат;
- проект ведёт локальный ledger фактических input/output tokens;
- новые платные вызовы должны блокироваться, если могут превысить лимит;
- Edge TTS используется как бесплатный TTS по умолчанию;
- дорогую text-to-video генерацию в первый пилот не включаем;
- новые платные провайдеры без отдельного решения пользователя не подключать.

## 5. Git status / workflow

Default branch: `main`.

Рабочая ветка: `mvp/pilot-scaffold`.

Текущий review vehicle: **draft PR #1 — `MVP: review-first 15-Short pilot scaffold`**.

PR намеренно остаётся draft до визуальной проверки первых двух роликов.

Не merge автоматически только потому, что tests/CI зелёные.

На момент перед этим handoff-update рабочий head был `269080d40ad24912212d21b9198849f975aa59fa`; сам handoff-update создаёт новый commit, поэтому новый чат всегда обязан перепроверить актуальный PR head через GitHub.

## 6. Что уже реализовано

### Pilot manifest

- фиксированный manifest на 15 роликов;
- проверка 8 AI / 7 animal;
- проверка ровно двух русских роликов;
- проверка, что русский тест есть в каждой ветке.

### OpenAI planner

Structured output включает:

- hook;
- script;
- footage/search terms;
- caption;
- hashtags;
- fact-check list;
- AI-disclosure recommendation/metadata.

### Budget ledger

- считает фактическое token usage;
- хранит локальную историю затрат;
- hard cap = $10;
- должен не допускать выхода за лимит.

### MoneyPrinterTurbo adapter

VV_knopka не копирует MoneyPrinterTurbo внутрь репозитория, а вызывает его локальный API.

Проверено на upstream 2026-08-28:

- API обычно `127.0.0.1:8080`;
- prefix `/api/v1`;
- video endpoint `/api/v1/videos`;
- task states: failed `-1`, complete `1`, processing `4`;
- Windows 10+ поддерживается;
- MoneyPrinterTurbo требует Python 3.11+;
- portrait 9:16 поддерживается;
- Edge TTS доступен без отдельного платного TTS key.

### AI short pipeline

Уже предусмотрено:

- планирование;
- submit в MoneyPrinterTurbo;
- polling task status;
- скачивание результата;
- staging готового MP4 в `runtime/ready_for_review`.

### Animal pipeline

Есть FFmpeg workflow:

- vertical 9:16;
- source/provenance gate;
- `sources.json`;
- минимум несколько clips;
- explicit commercial-use flag;
- loudness normalization;
- micro-fades;
- no bass/drop/impact transition SFX.

### Review gates

- duplicate/near-duplicate script protection;
- publication gate;
- human-review staging;
- `auto_publish=false`.

### Tests

До первого пользовательского Windows-запуска локально подтверждено: **4/4 tests PASS**.

GitHub Actions содержит Linux test job и теперь также отдельный Windows bootstrap job.

Новый чат обязан перепроверять CI непосредственно в GitHub и не считать его PASS по этому тексту.

## 7. Реальный Windows bootstrap incident — 2026-08-28

Пользователь запустил первоначальный `scripts/setup-windows.ps1` на ПК в `D:\KiraS\VV_knopka`.

Системный Python оказался:

`3.10.6`

Первый setup создал `.venv` на Python 3.10.6, после чего установка проекта упала:

```text
ERROR: Package 'vv-knopka' requires a different Python: 3.10.6 not in '>=3.11'
```

Следом появились каскадные ошибки:

```text
ModuleNotFoundError: No module named 'vv_knopka'
No module named pytest
```

Причина каскада: старый PowerShell bootstrap использовал `$ErrorActionPreference = "Stop"`, но не проверял ненулевые exit codes внешних программ. Поэтому после failed `pip install` он ошибочно продолжил следующие шаги и даже успел создать `.env`.

### Исправление уже внесено в ветку

`scripts/setup-windows.ps1` теперь:

- ищет Python 3.11 через `py -3.11`;
- принимает системный `python`, только если он >=3.11;
- проверяет стандартные пути Python 3.11;
- если доступен `uv`, умеет поставить Python 3.11 через `uv python install 3.11`;
- иначе при наличии `winget` пытается установить `Python.Python.3.11`;
- обнаруживает старую `.venv` на Python <3.11 и удаляет её;
- пересоздаёт `.venv` на Python 3.11+;
- после каждого native command проверяет `$LASTEXITCODE`;
- немедленно останавливается при failed venv/pip/install/init/tests;
- существующий `.env` не перезаписывает.

Коммиты исправления bootstrap:

- `11b9345fe1c08f6866eebce36260cbd5c231a276`
- `15d5f7b5ad7b5c3d85566f7565875d38f46cc3e3`

Дополнительно добавлен Windows CI scenario, который намеренно начинает с Python `3.10.6` и проверяет переход на 3.11+: commit `269080d40ad24912212d21b9198849f975aa59fa`.

## 8. Точная текущая точка продолжения на ПК пользователя

Пользователь уже находится в:

```text
D:\KiraS\VV_knopka
```

У него после первого failed setup уже может существовать:

- несовместимая `.venv` на Python 3.10.6;
- `.env`, созданный старым скриптом.

Новый setup должен сам удалить несовместимую `.venv` и сохранить `.env` без изменений.

Следующие команды:

```powershell
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

Не нужно вручную удалять `.venv`, если новый bootstrap работает как задумано.

После успешного setup выполнить:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\vv.exe status
```

Ожидается Python >=3.11 и безопасный pilot status примерно с:

- OpenAI spent около `$0.0000 / $10.00` на чистом ledger;
- `auto_publish: False`;
- publication gate без автопубликации.

Если `.env` ещё без ключа, после успешного setup пользователь сам добавляет туда `OPENAI_API_KEY=...` и не присылает ключ в чат.

## 9. Следующий milestone после bootstrap

После успешного status check:

1. установить/запустить MoneyPrinterTurbo на Windows;
2. убедиться, что `http://127.0.0.1:8080/docs` доступен;
3. настроить footage provider (например, Pexels) и бесплатный Edge TTS;
4. сгенерировать plan для slot 1;
5. проверить фактические claims сценария;
6. render **slot 1 — русский AI Short**;
7. получить MP4 в `runtime/ready_for_review`;
8. пользователь вручную оценивает voice, pacing, hook, footage, subtitles, монтаж и AI-slop ощущение;
9. скорректировать стиль;
10. подготовить лицензированные/source-tracked clips и сделать slot 2 — русскую animal compilation;
11. только после проверки slots 1–2 переходить к остальным 13.

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
