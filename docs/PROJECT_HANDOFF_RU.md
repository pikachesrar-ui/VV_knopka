# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Рабочая ветка `mvp/pilot-scaffold`. Draft PR #1 открыт и не должен merge без отдельного решения пользователя.

## Текущая продуктовая цель

Довести VV_knopka до максимально автономного long-run конвейера:

`идея/факт -> проверки -> рендер -> metadata -> YouTube upload -> processing/privacy verification -> statistics`

Сейчас фокус только на YouTube. TikTok запланирован позже отдельным блоком.

## Что подтверждено на реальном ПК пользователя

На 2026-08-31:

- frozen pilot: 15/15 Shorts, визуально принят;
- long-run slot 16 EN cats / #008 готов локально;
- всего готово локально: **16**;
- YouTube OAuth успешно пройден и channel binding создан;
- реальные uploads через API работают;
- slots **1–10** имеют `.youtube.json` receipts;
- у проверенных 1–10 `requested_privacy=public`, `actual_privacy=public`;
- pending queue = **6** (slots 11–16);
- следующий generation target = slot 17 AI EN, но backlog-first policy не разрешает генерировать его, пока pending > 0.

Реальный канал: `Knopka322`.

## Scheduler

Windows Scheduled Task `VV Knopka Long Run` реально установлен и имеет состояние `Ready`.

Триггеры:

```text
01:30 MSK
03:30 MSK
05:30 MSK
```

Пользователь подтвердил Windows timezone:

```text
Russian Standard Time
UTC+03:00 Москва, Санкт-Петербург
```

PowerShell не обязан быть открыт. Для запуска задачи ПК должен оставаться включён, пользователь Windows — залогинен; сон/гибернация могут помешать.

Текущая trigger-policy:

1. status;
2. при наличии OAuth/receipts проверить уже uploaded видео;
3. best-effort собрать статистику;
4. если pending > 0 — загрузить ровно один oldest pending и закончить trigger;
5. если pending == 0 — создать ровно один следующий long-run slot;
6. после рендера загрузить только новый newest pending;
7. upload fail/deferred блокирует дальнейшее раздувание backlog.

Нормальное давление = максимум 3 upload opportunities/day.

## YouTube daily limit

Первая массовая ручная загрузка успела успешно отправить slots 1–10, после чего YouTube вернул:

```text
400 uploadLimitExceeded
The user has exceeded the number of videos they may upload.
```

Это channel-level daily upload limit, а не Google Cloud quota.

Реализовано:

- отдельное распознавание `uploadLimitExceeded`;
- `DEFERRED` вместо traceback;
- exit code 75;
- ignored `runtime/youtube/upload-limit.json`;
- conservative cooldown 24h;
- active cooldown не hammer'ит upload endpoint;
- receipts делают retry idempotent.

Старый лимит произошёл до установки новой graceful-версии, поэтому локальный cooldown мог не существовать до следующего наблюдения лимита.

## YouTube metadata v2

Для **новых long-run slots** реализовано:

- 3–5 релевантных hashtags в description;
- котовые CTA с детерминированной ротацией;
- planner-generated AI hashtags теперь используются, а не выбрасываются;
- `snippet.tags` заполняется нормализованными keyword tags;
- `metadata_version=2`;
- long-run publication semantics совпадает с реальной авторизацией: при `[youtube].auto_publish=true` metadata пишет `auto_publish=true`, `review_required=false`, `publication_allowed_by_conveyor=true`;
- frozen pilot metadata остаётся исторически review-first и не переписывается ради новых улучшений.

Uploader передаёт `containsSyntheticMedia=true` только если конкретная metadata этого требует — например, если реально применена AI-generated music или planner отдельно рекомендовал disclosure.

## Post-upload verification + statistics

Добавлены команды:

```powershell
.\.venv\Scripts\vv-youtube.exe verify
.\.venv\Scripts\vv-youtube.exe stats
```

`verify` читает upload receipts, запрашивает YouTube и отслеживает:

- upload status;
- processing status;
- privacy;
- failure/rejection;
- publication state.

`FAILED`/`MISSING` считаются fail-closed для unattended scheduler.

`stats` сохраняет snapshots для:

- views;
- likes;
- comments;
- title/slot/video ID.

Stats — observational: сбой их сбора не должен сам по себе блокировать публикацию.

## Fact-check gate для AI facts

Long-run AI planning теперь имеет fail-closed evidence step до рендера.

Flow:

```text
plan candidate
 -> one bounded OpenAI web-search tool call
 -> structured fact verdict + evidence sources
 -> PASS => promote to plan.json
 -> FAIL => no render / no publish
```

Config:

```toml
fact_check_enabled = true
fact_check_model = "gpt-5.6-luna"
fact_check_max_tool_calls = 1
fact_check_max_estimated_cost_usd = 0.05
web_search_call_usd = 0.01
```

Проверка требует не только `pass=true`, но и supported claim results + реальные returned evidence sources.

Стоимость model tokens и отдельная fixed fee web-search учитываются в том же project-side `$10` ledger.

## MoneyPrinterTurbo lifecycle

Long-run conveyor уже имел `MPTProcessManager`, который:

- проверяет локальный MPT;
- при необходимости сам запускает его;
- ждёт health readiness;
- пишет runtime log;
- после batch закрывает процесс, если сам его поднял.

Ручной `render-ai` также переведён на auto-availability helper.

Таким образом оставлять отдельный PowerShell с MoneyPrinterTurbo как постоянное условие больше не требуется, если локальный MPT checkout/env исправен.

## AI background music

Пользователь одобрил идею: сгенерировать небольшую библиотеку спокойной/приятной фоновой музыки и ротировать её между Shorts.

Текущая инфраструктура уже готова:

- target local generator: **ACE-Step**;
- local ignored library: `runtime/assets/music`;
- pipeline-oriented track naming/ranking: `curious_*`, `calm_*`, `cute_*`, `playful_*`, `generic_*`;
- cooldown по последним использованным трекам;
- per-slot `music.json` audit;
- SHA256 трека в audit;
- AI-generator/disclosure metadata;
- FFmpeg mix под существующий audio;
- quiet levels: AI и cats отдельно;
- ducking включён;
- если local library включена, MPT BGM автоматически мутится, чтобы не было двойной музыки.

Важно: сейчас в config:

```toml
[music]
enabled = false
```

Не включать production music до локального generation/listening checkpoint с пользователем. План: сгенерировать примерно 8–12 инструментальных треков и оставить только одобренные.

Для cat compilations original clip audio остаётся главным; музыка должна быть очень тихой.

## Cat pipeline — актуальные правила

- local FFmpeg renderer;
- generic cats;
- real source audio required;
- real meow on black cards;
- no bass/drop/impact/boom SFX;
- minimum 5 unique usable clips;
- near-9:16 source gate, tolerance 0.08;
- provenance/commercial-use fail-closed;
- Pexels/Pixabay normal sources;
- frozen pilot reuse protection all-history;
- long-run source cooldown previous 5 cat episodes;
- fresh-first, cooled-history fallback.

Future approved AI music may be added quietly only after `[music].enabled=true`.

## Budget

Project-side OpenAI hard cap remains **$10.00**.

Last explicitly shown real local ledger before this block: approximately `$0.1885 / $10.00`.

Новые платные providers не добавлять без explicit approval.

Fact-check web-search fee теперь тоже учитывается внутри ledger.

## Tests / CI

Полностью зелёный checkpoint перед последними semantic/docs commits:

```text
head: cdf9e2adbc709a93269ef7b2a560f890544a9075
workflow: 33416185965
138 passed
Ubuntu: success
Windows bootstrap: success
Windows scheduler dry-run: success
```

Windows CI отдельно подтвердил scheduler dry-run с новым описанием behavior и 3 triggers/day.

Последующие commits с publication semantics/docs двигают HEAD, поэтому финальный HEAD нужно перепроверить после завершения этого блока.

## Immediate continuation

Без участия пользователя можно:

1. дождаться green CI текущего HEAD;
2. поддерживать docs/PR в актуальном состоянии;
3. не менять current real scheduler автоматически через GitHub — пользовательский ПК должен сначала сделать `git pull`/reinstall;
4. после pull проверить `vv-youtube verify` + `vv-youtube stats` на реальных receipts;
5. позволить scheduler догрузить slots 11–16;
6. после pending=0 проверить первый полностью автономный slot 17: plan -> fact-check -> MPT autostart -> render -> metadata v2 -> YouTube.

Первый ожидаемый пользовательский checkpoint по новому feature block: локальная установка/запуск ACE-Step и прослушивание generated music.

TikTok пока не трогать.

## Git rules

- branch: `mvp/pilot-scaffold`;
- PR #1 stays draft/open/unmerged;
- secrets under `runtime/` / `.env` never commit;
- после substantive work обновлять этот handoff + `PROGRESS_RU.md` + `AGENT.md`.
