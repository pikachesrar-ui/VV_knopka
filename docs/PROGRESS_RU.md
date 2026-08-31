# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-31**. Подробный контекст — `AGENT.md`, `docs/PROJECT_HANDOFF_RU.md`, `docs/AI_MUSIC_RU.md`.

## Реальный локальный checkpoint пользователя

```text
готово локально: 16 Shorts
YouTube receipts: 10
published public: slots 1–10
pending: slots 11–16 (6 штук)
next generation target: slot 17 AI EN
```

У всех показанных receipts:

```text
requested_privacy = public
actual_privacy = public
```

Реальный YouTube API upload и public visibility подтверждены.

## Windows scheduler

Task Scheduler:

```text
TaskName: VV Knopka Long Run
State: Ready
01:30 +03:00
03:30 +03:00
05:30 +03:00
Timezone: Russian Standard Time (UTC+03:00)
```

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

## YouTube upload limit — DONE

После 10 успешных реальных uploads YouTube вернул:

```text
400 uploadLimitExceeded
The user has exceeded the number of videos they may upload.
```

Новый uploader:

- возвращает clean `DEFERRED` вместо traceback;
- использует exit code 75;
- пишет ignored `runtime/youtube/upload-limit.json`;
- держит conservative 24h cooldown;
- не hammer'ит endpoint во время cooldown;
- безопасно retry через idempotent receipts.

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
- `vv status` теперь отдельно показывает `pilot auto_publish (historical)` и `youtube auto_publish`, поэтому старая путаница убрана.

Synthetic-media disclosure включается только когда конкретная metadata требует этого; applied AI-generated music автоматически включает flag.

## YouTube observability — DONE

```powershell
vv-youtube verify
vv-youtube stats
```

`verify` проверяет processing/upload/privacy/failure/rejection для videos из receipts. Failed/missing publication fail-closed для scheduler.

`stats` сохраняет views/likes/comments snapshots для будущего анализа того, какие темы/форматы работают на канале. Stats collection — best-effort.

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

## Финальный code checkpoint этого блока

```text
head: 6def0e462c17eb5f6b536d7d3446daee21ebecf8
workflow: 33419061821
pytest: 146 passed in 0.93s
Ubuntu: PASS
Windows bootstrap: PASS
Windows scheduler dry-run: PASS
Windows ACE-Step helper dry-run: PASS
```

Перед этим CI поймал один regression только в test setup (`FileExistsError` из-за повторного mkdir); production code не был причиной. Тест исправлен, свежий полный CI зелёный.

## Что осталось до следующего server-side milestone

- поддерживать PR/docs в актуальном состоянии;
- PR #1 оставить draft/open/unmerged;
- TikTok пока не трогать;
- не включать `[music].enabled=true` без прослушивания локально generated tracks.

## Следующий шаг уже требует локального ПК пользователя

Сначала подтянуть свежий код:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

После этого можно реальным OAuth проверить YouTube observability:

```powershell
.\.venv\Scripts\vv-youtube.exe verify
.\.venv\Scripts\vv-youtube.exe stats
```

Для первого music checkpoint:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-acestep-windows.ps1
.\.venv\Scripts\vv-music.exe generate-library --count 8 --duration 45
```

Первый ACE-Step launch может скачивать model weights и занять время. Generated WAVs останутся **candidates** и сами не попадут в production.

После прослушивания выбранные tracks можно approved отдельно; только затем решать, включать ли production music и делать небольшой comparison music ON vs OFF.

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
