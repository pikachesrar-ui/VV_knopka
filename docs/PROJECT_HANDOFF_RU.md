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
- slots **1–11** реально опубликованы через API;
- `vv-youtube verify`: slots 1–11 = **VERIFIED_PUBLIC**;
- для всех 1–11: `upload=processed`, `processing=succeeded`, `privacy=public`;
- pending queue = **5**, slots 12–16;
- следующий generation target = slot 17 AI EN, но backlog-first policy блокирует его до pending=0;
- текущий local OpenAI ledger = **$0.1885 / $10.00**.

Реальный канал: `Knopka322`.

## Windows scheduler — реальная production-проверка пройдена

Task `VV Knopka Long Run` реально установлен и `Ready`.

```text
01:30 MSK
03:30 MSK
05:30 MSK
Timezone: Russian Standard Time (UTC+03:00)
```

PowerShell не нужно держать открытым. ПК должен быть включён, Windows user logged in; sleep/hibernation могут помешать.

Ночной run подтвердил настоящий unattended flow:

1. scheduler самостоятельно upload'нул **slot 11**;
2. slot 11 после YouTube processing стал `VERIFIED_PUBLIC`;
3. следующая попытка получила `uploadLimitExceeded`;
4. graceful uploader сохранил cooldown без traceback;
5. status показал:

```text
pending ready uploads: 5
upload limit cooldown until: 2026-09-01T00:30:07.333703+00:00
```

Это примерно **03:30 MSK 2026-09-01**. До этого времени uploader не должен повторно обращаться к upload endpoint.

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

Это channel-level YouTube daily limit, не Google Cloud quota.

Текущий uploader:

- распознаёт limit отдельно;
- возвращает `DEFERRED` без traceback;
- exit code 75;
- сохраняет ignored `runtime/youtube/upload-limit.json`;
- conservative retry-not-before +24h;
- не hammer'ит upload endpoint во время cooldown;
- использует receipts как idempotency source of truth.

Graceful-limit path теперь подтверждён на реальном scheduler.

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

## Post-upload verification + stats + report

Commands:

```powershell
.\.venv\Scripts\vv-youtube.exe verify
.\.venv\Scripts\vv-youtube.exe stats
.\.venv\Scripts\vv-youtube.exe report
```

`verify` проверяет:

- upload status;
- processing status;
- actual privacy;
- failure/rejection reason;
- missing video.

Failed/missing публикация fail-closed для scheduler.

`stats` сохраняет views/likes/comments snapshots и append-only local history.

`report` считает age-aware metrics:

- views/hour;
- likes per 1000 views;
- comments per 1000 views;
- AI vs animal_compilation aggregates.

Первый real snapshot = 11 videos, sample пока очень маленький; использовать его для серьёзной оптимизации рано. На момент проверки slot 5 `How Ants Build Invisible Highways` имел 12 views и был top by age-adjusted views/hour.

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

Local bootstrap now:

```powershell
cd D:\KiraS\VV_knopka
powershell -ExecutionPolicy Bypass -File .\scripts\setup-acestep-windows.ps1
.\.venv\Scripts\vv-music.exe status
```

Then first candidate generation:

```powershell
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
- current local ledger explicitly confirmed `$0.1885/$10`;
- no new paid providers without explicit approval;
- secrets under `.env`/`runtime/`, never commit;
- ACE-Step generated audio must still be reviewed for quality/originality; do not make blanket copyright guarantees.

## CI — latest green code checkpoint

```text
head: 936bd0956ad0c08fb236c1a97aada6ff0464e88d
workflow: 33419768393
pytest: 147 passed in 0.90s
Ubuntu: PASS
Windows bootstrap: PASS
Windows scheduler dry-run: PASS
Windows ACE-Step setup/start dry-run: PASS
```

Operational documentation commits after this checkpoint move branch HEAD.

## Следующий meaningful checkpoint

1. scheduler продолжает draining slots 12–16 under cooldown/backlog-first policy;
2. пользователь локально устанавливает/запускает ACE-Step;
3. генерируются 8 candidate WAVs;
4. пользователь прослушивает и выбирает хорошие;
5. selected tracks approve, но `music.enabled=false` остаётся до отдельного решения;
6. затем controlled music ON vs OFF comparison;
7. после pending=0 первый unattended slot 17 должен пройти:

`plan -> fact-check -> MPT auto-start -> curated stock -> render -> metadata v2 -> YouTube -> verify/stats`.

TikTok пока не трогать.

## Git rules

- branch `mvp/pilot-scaffold`;
- PR #1 draft/open/unmerged;
- не merge без explicit user decision;
- substantive work => update `AGENT.md`, `PROJECT_HANDOFF_RU.md`, `PROGRESS_RU.md`.
