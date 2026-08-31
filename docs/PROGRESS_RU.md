# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-31**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Реальный локальный checkpoint

Пользователь подтвердил на своём Windows ПК:

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

То есть настоящий YouTube API upload и public visibility подтверждены.

## Windows scheduler

Task Scheduler:

```text
TaskName: VV Knopka Long Run
State: Ready
```

Триггеры подтверждены пользователем:

```text
01:30 +03:00
03:30 +03:00
05:30 +03:00
```

Windows timezone:

```text
Russian Standard Time (UTC+03:00)
```

PowerShell окна можно закрывать. ПК должен оставаться включённым и Windows user — logged in; сон/hibernation нежелателен.

## Current scheduler policy

Каждый trigger:

1. `vv status`;
2. `vv-youtube status`;
3. если credentials/receipts доступны — `vv-youtube verify`;
4. best-effort `vv-youtube stats`;
5. если pending > 0 — upload exactly one oldest pending и exit без generation;
6. если pending == 0 — `vv longrun-next`;
7. затем upload только newest newly rendered video;
8. upload deferred/failure блокирует дальнейшую generation.

Максимум: **3 upload opportunities/day**.

## YouTube upload limit

После 10 успешных реальных uploads YouTube вернул:

```text
400 uploadLimitExceeded
The user has exceeded the number of videos they may upload.
```

Новый uploader умеет:

- распознавать это отдельно;
- возвращать `DEFERRED` без traceback;
- exit code 75;
- писать 24h cooldown в ignored `runtime/youtube/upload-limit.json`;
- не hammer'ить endpoint во время active cooldown;
- безопасно retry через idempotent receipts.

## YouTube metadata v2 — DONE

Для новых long-run slots:

- hashtags добавляются в description;
- cats получают CTA rotation;
- planner AI hashtags реально используются;
- `snippet.tags` передаются через API;
- tags/hashtags dedupe + caps;
- metadata version 2;
- long-run publication metadata теперь отражает реальный auto-publish policy;
- frozen pilot metadata остаётся review-first.

AI/synthetic disclosure:

- uploader поддерживает `containsSyntheticMedia`;
- он включается только когда конкретная metadata это рекомендует;
- applied AI-generated music автоматически ставит disclosure flag.

## YouTube observability — DONE

Добавлены:

```powershell
vv-youtube verify
vv-youtube stats
```

`verify` проверяет processing/upload/privacy/failure/rejection для videos из receipts.

`stats` собирает текущие views/likes/comments и сохраняет snapshots для дальнейшего анализа эффективности форматов/тем.

Publication verification fail-closed; stats collection best-effort.

## Long-run AI fact check — DONE

Перед promotion long-run AI plan в `plan.json` теперь идёт bounded evidence check.

```text
plan candidate
 -> 1 web-search tool call max
 -> structured claims verdict
 -> actual evidence sources required
 -> PASS => render allowed
 -> FAIL => candidate не рендерится и не публикуется
```

Config:

```text
fact_check_enabled = true
fact_check_model = gpt-5.6-luna
fact_check_max_tool_calls = 1
web_search_call_usd = 0.01
```

Model token cost + web-search fixed fee учитываются в `$10` BudgetLedger.

## MoneyPrinterTurbo autonomy — DONE in code

Long-run уже умеет сам поднимать MPT при необходимости через `MPTProcessManager`.

Manual `render-ai` тоже переведён на auto-availability helper.

Следовательно отдельное постоянно открытое PowerShell окно с MPT больше не должно быть обязательным для будущего unattended AI slot, если локальный MPT environment исправен.

## AI background music — INFRASTRUCTURE DONE / CONTENT PENDING

User approved AI-generated quiet BGM.

Реализовано:

- local music library abstraction;
- target generator = ACE-Step;
- `runtime/assets/music`;
- track ranking by `curious/calm/cute/playful/generic` prefixes;
- deterministic rotation;
- recent-track cooldown;
- per-slot music audit + SHA256;
- quiet volume settings separately for AI/cats;
- sidechain ducking;
- FFmpeg mix into final video;
- MPT BGM muting when local library enabled;
- YouTube synthetic-media disclosure when AI music actually applied.

Но production music пока **OFF**:

```toml
[music]
enabled = false
```

Следующий music checkpoint требует пользователя: локально сгенерировать примерно 8–12 ACE-Step instrumentals, прослушать и оставить только хорошие.

## Tests / CI

YouTube-v2 implementation checkpoint:

```text
head: cdf9e2adbc709a93269ef7b2a560f890544a9075
workflow: 33416185965
pytest: 138 passed
Ubuntu: PASS
Windows bootstrap: PASS
Windows scheduler dry-run: PASS
```

После этого сделаны publication-semantics + docs commits. Новый HEAD должен пройти свежий CI перед финальной фиксацией.

## Что делаем дальше

Сейчас без пользователя:

1. дождаться свежего CI текущего HEAD;
2. при необходимости исправить regressions;
3. обновить PR #1 summary;
4. сохранить PR draft/open/unmerged.

На реальном ПК позже:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\vv-youtube.exe verify
.\.venv\Scripts\vv-youtube.exe stats
```

После этого scheduler продолжит backlog-first upload slots 11–16.

Когда pending станет 0, первый важный unattended generation test — slot 17:

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

TikTok пока отложен.

Draft PR #1 остаётся open/draft/unmerged.
