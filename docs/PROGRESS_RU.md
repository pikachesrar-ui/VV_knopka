# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-31**. Подробный контекст — `AGENT.md`, `docs/PROJECT_HANDOFF_RU.md`, `docs/AI_MUSIC_RU.md`.

## Реальный локальный checkpoint пользователя

На вечер 2026-08-31 пользователь подтвердил на своём Windows ПК:

```text
готово локально: 16 Shorts
YouTube receipts: 11
published + VERIFIED_PUBLIC: slots 1–11
pending: slots 12–16 (5 штук)
next generation target: slot 17 AI EN
OpenAI spent: $0.1885 / $10.00
```

У всех slots 1–11 `vv-youtube verify` вернул:

```text
upload=processed
processing=succeeded
privacy=public
publication_state=VERIFIED_PUBLIC
```

Реальный YouTube API upload, processing verification и public visibility подтверждены.

## Windows scheduler — REAL PRODUCTION VALIDATION PASSED

Task Scheduler:

```text
TaskName: VV Knopka Long Run
State: Ready
01:30 +03:00
03:30 +03:00
05:30 +03:00
Timezone: Russian Standard Time (UTC+03:00)
```

Ночной unattended run реально подтвердил backlog-first поведение:

1. scheduler самостоятельно опубликовал **slot 11**;
2. slot 11 после processing стал `VERIFIED_PUBLIC`;
3. следующая upload opportunity получила YouTube `uploadLimitExceeded`;
4. новый uploader сохранил cooldown вместо traceback;
5. локальный status показал:

```text
pending ready uploads: 5
upload limit cooldown until: 2026-09-01T00:30:07.333703+00:00
```

Это соответствует примерно **03:30 MSK 2026-09-01**. Во время active cooldown scheduler не должен повторно hammer'ить upload endpoint.

PowerShell окна можно закрывать. Для выполнения задачи ПК должен оставаться включённым, Windows user — logged in; сон/hibernation нежелателен.

Текущая policy каждого trigger:

1. `vv status`;
2. `vv-youtube status`;
3. при наличии credentials/receipts — `vv-youtube verify`;
4. best-effort `vv-youtube stats`;
5. если pending > 0 — upload exactly one oldest pending и exit без generation;
6. если pending == 0 — `vv longrun-next`;
7. затем upload только newest rendered video;
8. upload deferred/failure блокирует дальнейшее накопление backlog.

Максимум: **3 upload opportunities/day**.

## YouTube upload limit — DONE / REAL VALIDATED

Uploader:

- возвращает clean `DEFERRED` вместо traceback;
- использует exit code 75;
- пишет ignored `runtime/youtube/upload-limit.json`;
- держит conservative 24h cooldown;
- не hammer'ит endpoint во время cooldown;
- безопасно retry через idempotent receipts.

Это поведение теперь подтверждено не только тестами, но и настоящим ночным scheduler run.

## YouTube metadata v2 — DONE

Для новых long-run slots:

- hashtags в description;
- CTA rotation для cats;
- planner AI hashtags реально используются;
- `snippet.tags` передаются через API;
- tags/hashtags dedupe + caps;
- `metadata_version=2`;
- long-run metadata отражает реальный YouTube auto-publish policy;
- frozen pilot остаётся исторически review-first;
- `vv status` отдельно показывает `pilot auto_publish (historical)` и `youtube auto_publish`.

Synthetic-media disclosure включается только когда конкретная metadata требует этого; applied AI-generated music автоматически включает flag.

## YouTube observability + performance report — DONE

Команды:

```powershell
vv-youtube verify
vv-youtube stats
vv-youtube report
```

`verify` проверяет processing/upload/privacy/failure/rejection для videos из receipts. Failed/missing publication fail-closed для scheduler.

`stats` сохраняет views/likes/comments snapshots и append-only `statistics-history.jsonl`.

`report` строит age-aware comparison:

- views/hour;
- likes per 1000 views;
- comments per 1000 views;
- aggregate AI vs animal_compilation.

Первый реальный snapshot (11 videos) пока слишком маленький для optimisation decisions, но data path работает. На момент проверки лидировал slot 5 (`How Ants Build Invisible Highways`) с 12 views; sample size ещё нельзя считать статистически значимым.

## Long-run AI fact check — DONE

```text
plan candidate
 -> max 1 bounded web-search tool call
 -> structured claim verdict
 -> actual evidence sources required
 -> PASS => promote to plan.json
 -> FAIL => no render / no publish
```

Config:

```text
fact_check_enabled = true
fact_check_model = gpt-5.6-luna
fact_check_max_tool_calls = 1
web_search_call_usd = 0.01
```

Model token cost + web-search fixed fee учитываются в общем `$10` BudgetLedger.

## MoneyPrinterTurbo autonomy — DONE in code

Long-run `MPTProcessManager` умеет сам поднять MPT, дождаться health readiness, выполнить AI render и остановить только процесс, который он запустил.

Manual `render-ai` также использует auto-availability helper. Постоянное отдельное PowerShell окно с MPT больше не является целевой зависимостью unattended flow.

## AI background music — CODE/WORKFLOW DONE, LOCAL CONTENT PENDING

Production music пока намеренно выключена:

```toml
[music]
enabled = false
```

Реализовано:

- local music library + FFmpeg mixer;
- target generator **ACE-Step 1.5**;
- REST client `src/vv_knopka/acestep_client.py`;
- auto-start `/health` / async task polling / WAV download;
- CLI `vv-music`;
- Windows setup/debug helpers;
- ignored local checkout `ACE-Step-1.5/`;
- separate `runtime/assets/music/candidates/`;
- candidate files не участвуют в production rotation;
- explicit `vv-music approve ...` переносит только выбранные WAV в approved root;
- approval **не** включает feature flag;
- initial stable candidate set: `cute_01/02`, `playful_01/02`, `curious_01/02`, `calm_01/02`;
- deterministic rotation + cooldown;
- per-slot SHA256/music audit;
- quiet volume settings отдельно для AI/cats;
- sidechain ducking;
- MPT BGM muting при использовании approved local music;
- YouTube synthetic-media disclosure при реально applied AI music.

Документация: `docs/AI_MUSIC_RU.md`.

## Финальный CI checkpoint

```text
head: 936bd0956ad0c08fb236c1a97aada6ff0464e88d
workflow: 33419768393
pytest: 147 passed in 0.90s
Ubuntu: PASS
Windows bootstrap: PASS
Windows scheduler dry-run: PASS
Windows ACE-Step helper dry-run: PASS
```

## Следующий локальный checkpoint — ACE-Step

Пользователь уже готов продолжать на реальном RTX 3060 PC.

Setup:

```powershell
cd D:\KiraS\VV_knopka
powershell -ExecutionPolicy Bypass -File .\scripts\setup-acestep-windows.ps1
.\.venv\Scripts\vv-music.exe status
```

После успешного setup первые candidates:

```powershell
.\.venv\Scripts\vv-music.exe generate-library --count 8 --duration 45
```

Первый ACE-Step launch может скачивать model weights и занять время. Generated WAVs останутся **candidates** и сами не попадут в production.

После прослушивания:

```text
cute_01/02
playful_01/02
curious_01/02
calm_01/02
```

выбранные tracks можно approve отдельно. Даже после approve `[music].enabled=false` остаётся неизменным до отдельного решения.

Дальше планируется небольшой controlled comparison music ON vs OFF с использованием собственного `vv-youtube report`.

Когда YouTube backlog станет 0, первый важный unattended generation test — slot 17:

```text
AI plan
 -> fact-check
 -> MPT auto-start
 -> curated stock
 -> render
 -> metadata v2
 -> YouTube upload
 -> verification/statistics
```

TikTok — отдельный более поздний work block.

Draft PR #1 остаётся open/draft/unmerged.
