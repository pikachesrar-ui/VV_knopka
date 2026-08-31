# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Рабочая ветка `mvp/pilot-scaffold`. Draft PR #1 открыт и **не merge** без отдельного решения пользователя.

## Текущая цель

Максимально автономный long-run pipeline:

`идея/факт -> validation -> render -> metadata -> YouTube upload -> publication verification -> statistics`

Текущий work block = YouTube v2 + AI fact-check + local AI-music infrastructure. TikTok намеренно отложен.

## Реальный checkpoint пользователя — 2026-08-31

На Windows ПК подтверждено:

- frozen pilot 15/15 визуально принят;
- slot 16 EN cats / #008 готов локально;
- всего ready локально: **16**;
- YouTube OAuth и channel binding работают;
- slots **1–10** реально опубликованы через API;
- для показанных receipts `requested_privacy=public`, `actual_privacy=public`;
- pending queue = **6**, slots 11–16;
- следующий generation target = slot 17 AI EN, но backlog-first policy блокирует его до pending=0.

Реальный канал: `Knopka322`.

## Windows scheduler

Task `VV Knopka Long Run` реально установлен и `Ready`.

```text
01:30 MSK
03:30 MSK
05:30 MSK
Timezone: Russian Standard Time (UTC+03:00)
```

PowerShell не нужно держать открытым. ПК должен быть включён, Windows user logged in; sleep/hibernation могут помешать.

Каждый trigger:

1. `vv status`;
2. `vv-youtube status`;
3. verify existing receipts when credentials exist;
4. best-effort stats;
5. если pending > 0 — upload exactly one oldest pending и exit без generation;
6. если pending == 0 — generate exactly one next long-run slot;
7. upload только newest newly rendered video;
8. deferred/failure блокирует дальнейшее увеличение backlog.

Максимум = 3 upload opportunities/day.

## YouTube daily limit

Первая ручная bulk upload успела успешно отправить slots 1–10, затем YouTube вернул:

```text
400 uploadLimitExceeded
The user has exceeded the number of videos they may upload.
```

Это channel-level YouTube daily limit, не Google Cloud quota.

Текущий uploader:

- распознаёт limit отдельно;
- возвращает `DEFERRED` без traceback;
- exit code 75;
- сохраняет ignored `runtime/youtube/upload-limit.json`;
- conservative retry-not-before +24h;
- не hammer'ит upload endpoint во время cooldown;
- использует receipts как idempotency source of truth.

## YouTube metadata v2

Для **новых long-run slots**:

- 3–5 hashtags в description;
- deterministic CTA rotation для cats;
- planner AI hashtags используются, а не теряются;
- `snippet.tags` с normalization/dedupe/caps;
- `metadata_version=2`;
- long-run metadata соответствует реальному `[youtube].auto_publish=true`;
- frozen pilot остаётся historical review-first;
- `vv status` раздельно показывает historical pilot flag и реальный YouTube auto-publish.

Conditional disclosure:

- `containsSyntheticMedia` передаётся только при конкретной необходимости;
- applied AI-generated music автоматически делает disclosure recommended/true;
- blanket marking любого AI assistance запрещён как продуктовая policy.

## Post-upload verification + stats

Commands:

```powershell
.\.venv\Scripts\vv-youtube.exe verify
.\.venv\Scripts\vv-youtube.exe stats
```

`verify` проверяет:

- upload status;
- processing status;
- actual privacy;
- failure/rejection reason;
- missing video.

Failed/missing публикация fail-closed для scheduler.

`stats` сохраняет views/likes/comments snapshots. Это observational data; failure stats collection сам по себе не блокирует publication.

## AI fact-check gate

Long-run AI plan до рендера проходит bounded evidence check:

```text
plan candidate
 -> max one OpenAI web-search tool call
 -> structured claims verdict
 -> actual evidence sources required
 -> PASS => plan.json
 -> FAIL => no render/no publish
```

Config:

```toml
fact_check_enabled = true
fact_check_model = "gpt-5.6-luna"
fact_check_max_tool_calls = 1
fact_check_max_estimated_cost_usd = 0.05
web_search_call_usd = 0.01
```

Model tokens + fixed web-search cost идут в тот же project-side `$10` ledger.

## MoneyPrinterTurbo lifecycle

Long-run `MPTProcessManager` умеет:

- проверить MPT;
- при необходимости запустить локальный MPT;
- дождаться readiness;
- логировать;
- закрыть только процесс, который он сам запустил.

Manual `render-ai` также использует auto-availability helper. Постоянное открытое окно MPT больше не является целевой зависимостью.

## AI background music — implementation ready, user listening pending

Пользователь одобрил идею маленькой rotating library тихой AI-generated music.

Production feature flag пока намеренно:

```toml
[music]
enabled = false
```

### Реализовано

- local generator target = **ACE-Step 1.5**;
- ignored local checkout `ACE-Step-1.5/`;
- ACE-Step REST client: `/health`, async `/release_task`, `/query_result`, audio download;
- automatic local API process manager;
- `vv-music` CLI;
- Windows setup/debug scripts;
- production library: `runtime/assets/music/`;
- generated candidates: `runtime/assets/music/candidates/`;
- production selector **не сканирует candidates**;
- `vv-music approve ...` explicit promotion выбранных WAV в approved root;
- approve не включает production flag;
- stable initial 8 candidates: `cute_01/02`, `playful_01/02`, `curious_01/02`, `calm_01/02`;
- generation manifest хранит task/model/seed/prompt/approval metadata;
- deterministic rotation + cooldown;
- per-slot SHA256 `music.json` audit;
- AI/cat separate quiet volumes;
- sidechain ducking;
- when local music enabled, MoneyPrinterTurbo BGM = 0 to prevent double music;
- applied AI music propagates to YouTube disclosure.

Guide: `docs/AI_MUSIC_RU.md`.

Local bootstrap later:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-acestep-windows.ps1
.\.venv\Scripts\vv-music.exe generate-library --count 8 --duration 45
```

Первый launch может скачивать model weights. Generated tracks остаются candidates и не могут сами попасть в production.

## Cat pipeline rules

- local FFmpeg renderer;
- generic cats;
- no voiceover;
- original source audio primary;
- real meow on black cards;
- no bass/drop/impact/boom SFX;
- source provenance/commercial-use/audio/near-9:16 gates fail-closed;
- min 5 unique usable clips;
- Pexels/Pixabay normal sources;
- frozen pilot reuse all-history;
- long-run cooldown previous 5 cat episodes;
- fresh-first, cooled-history fallback;
- future approved music must remain very quiet.

## Budget/safety

- OpenAI hard cap **$10** unchanged;
- last explicitly shown real local ledger before this block ~`$0.1885/$10`;
- no new paid providers without explicit approval;
- secrets under `.env`/`runtime/`, never commit;
- ACE-Step generated audio must still be reviewed for quality/originality; do not make blanket copyright guarantees.

## CI — final code checkpoint

After implementing YouTube v2, fact-check, MPT lifecycle improvements and safe ACE-Step candidate workflow:

```text
head: 6def0e462c17eb5f6b536d7d3446daee21ebecf8
workflow: 33419061821
pytest: 146 passed in 0.93s
Ubuntu: PASS
Windows bootstrap: PASS
Windows scheduler dry-run: PASS
Windows ACE-Step setup/start dry-run: PASS
```

One earlier run caught only a test-fixture `FileExistsError`; after fixing the redundant mkdir, fresh full CI is green.

Documentation commits after this code checkpoint move branch HEAD, so final docs HEAD should also be observed before claiming all-current HEAD green.

## Следующий meaningful checkpoint требует локального ПК

Fresh code first:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Then real YouTube check:

```powershell
.\.venv\Scripts\vv-youtube.exe verify
.\.venv\Scripts\vv-youtube.exe stats
```

Then optional/next music checkpoint:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-acestep-windows.ps1
.\.venv\Scripts\vv-music.exe generate-library --count 8 --duration 45
```

Пользователь должен прослушать candidates и выбрать хорошие. До этого `music.enabled=false`.

После pending=0 первый unattended slot 17 должен пройти:

`plan -> fact-check -> MPT auto-start -> curated stock -> render -> metadata v2 -> YouTube -> verify/stats`.

TikTok пока не трогать.

## Git rules

- branch `mvp/pilot-scaffold`;
- PR #1 draft/open/unmerged;
- не merge без explicit user decision;
- substantive work => update `AGENT.md`, `PROJECT_HANDOFF_RU.md`, `PROGRESS_RU.md`.
