# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Ветка `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя.

## Что завершено

- Frozen pilot: 15/15 Shorts, визуально принят пользователем.
- Первый real long-run slot 16 EN cats / #008 успешно завершён.
- Следующий deterministic generation target = slot 17 AI EN.
- Long-run scheduler = до 3 запусков за ночь: 01:30, 03:30, 05:30 МСК.
- Последний показанный OpenAI ledger: `$0.1885 / $10.00`.
- YouTube OAuth Desktop-app flow реально пройден пользователем и channel binding создан.

## Auto-publish intent

Пользователь явно попросил:

1. будущие generated Shorts сразу выкладывать на YouTube;
2. уже готовые ролики тоже выложить.

Config `[youtube]` намеренно:

```toml
enabled = true
auto_publish = true
privacy_status = "public"
category_id = "15"
made_for_kids = false
notify_subscribers = false
```

Frozen pilot `pilot.auto_publish=false` остаётся только исторической настройкой.

## Реальный backlog upload — channel daily limit

Первый реальный `vv-youtube upload-ready` на ПК пользователя дошёл до YouTube API error:

```text
400 uploadLimitExceeded
The user has exceeded the number of videos they may upload.
```

Это **не Google Cloud API quota**. По официальной документации YouTube это channel-level daily video upload limit, общий для desktop/mobile/API. YouTube рекомендует retry через 24 часа. Точное число не фиксировать в проекте: оно зависит от channel/account history/eligibility и может меняться.

YouTube Advanced feature access обычно даёт более высокий daily upload limit. Проверять в YouTube Studio → Settings → Channel → Feature eligibility.

Важно: старый uploader загружал последовательно и писал receipt сразу после каждого success. Поэтому все ролики, успевшие загрузиться до `uploadLimitExceeded`, должны иметь `<name>.upload.youtube.json` и при retry не должны дублироваться.

## Upload-limit fix

Новая policy/реализация:

- `uploadLimitExceeded` распознаётся отдельно;
- вместо Python traceback CLI печатает `DEFERRED` и завершает exit code `75`;
- момент лимита записывается в ignored `runtime/youtube/upload-limit.json`;
- сохраняется conservative `retry_not_before = observed + 24h`;
- пока cooldown активен, uploader не повторяет бессмысленные API upload attempts;
- `vv-youtube status` показывает cooldown;
- добавлен `vv-youtube pending-count`;
- successful receipts остаются idempotency source of truth.

## Scheduler после реального limit

Раньше scheduler мог upload old pending + generate + upload new в одном trigger, что давало до 6 upload attempts/day при трёх triggers.

Теперь каждый trigger имеет **не более одной публикации**:

1. status checks + lock;
2. `pending-count`;
3. если pending > 0 — upload exactly one oldest pending и завершить trigger **без нового render**;
4. только если pending = 0 — generate one long-run slot и upload newest;
5. любой deferred/failed upload блокирует новую generation до восстановления публикации.

Таким образом approved 01:30/03:30/05:30 schedule создаёт максимум 3 uploads/day и сначала реально уменьшает backlog.

## YouTube uploader files / commands

```text
src/vv_knopka/youtube_uploader.py
src/vv_knopka/youtube_cli.py
docs/YOUTUBE_PUBLISHING_RU.md
vv-youtube
```

Commands:

```powershell
.\.venv\Scripts\vv-youtube.exe status
.\.venv\Scripts\vv-youtube.exe pending-count
.\.venv\Scripts\vv-youtube.exe upload-ready --dry-run
.\.venv\Scripts\vv-youtube.exe upload-ready
```

Local ignored files:

```text
runtime/youtube/client_secret.json
runtime/youtube/token.json
runtime/youtube/channel.json
runtime/youtube/upload-limit.json
```

OAuth scopes = `youtube.upload` + `youtube.readonly`; uploader channel-binds and fail-closes on wrong channel. Each successful upload writes `.upload.youtube.json` receipt with video ID/URL and requested vs actual privacy.

## Existing backlog

Ready local backlog originally had slots 1–16. Unknown exactly how many succeeded before the real daily-limit error; determine locally from `.youtube.json` receipts or YouTube Studio. Do not guess.

Useful local check:

```powershell
Get-ChildItem .\runtime\ready_for_review\*.youtube.json | Sort-Object Name | Select-Object Name
(Get-ChildItem .\runtime\ready_for_review\*.youtube.json).Count
```

After the 24h window (or legitimate feature-eligibility increase), rerunning `upload-ready` is safe because receipts skip already successful slots.

## Long-run cat sourcing

- last 5 rendered cat episodes source IDs protected;
- fresh remote Pexels/Pixabay first;
- cooled old stock fallback only;
- local cooled history can seed after fresh minimum failure;
- local history revalidated 9:16 + audible audio;
- provenance/commercial-use/Luna/minimum-count gates unchanged.

## Budget / safety

- OpenAI hard cap `$10` unchanged.
- Не добавлять paid providers без explicit approval.
- OAuth/token/client secret не коммитить и не просить пользователя вставлять в чат.
- `runtime/` ignored.
- PR #1 stays draft/open/unmerged.

## Tests / CI

Upload-limit regressions added for:

- parsing `uploadLimitExceeded` from Google API error content;
- active 24h cooldown state;
- stopping backlog cleanly at limit after prior success;
- pending count ignoring receipted videos.

Code checkpoint `573bc4f2eb904da20fab03456f90391079144914`, workflow `33328852436`:

```text
121 passed in 0.82s
publication gate: PASS
long_run: True
```

Workflow fully **success**:

- Ubuntu tests green;
- Windows bootstrap green;
- Windows scheduler dry-run green.

Docs commits after code checkpoint move branch HEAD.

## Immediate continuation

1. На ПК пользователя посмотреть число receipts и actual privacy уже загруженных роликов.
2. Проверить YouTube Studio → Settings → Channel → Feature eligibility; если Advanced features не доступны, рассмотреть официальную verification path для higher daily limit.
3. `git pull` + reinstall editable package to get graceful daily-limit handling.
4. Не повторять массовый upload до конца текущего platform limit window; YouTube рекомендует 24h.
5. После восстановления лимита повторить `vv-youtube upload-ready`; receipts предотвратят дубли.
6. После/вместо ручного backlog drain установить scheduler; он будет публиковать максимум один ролик на trigger и не генерировать новое, пока backlog существует.

PR #1 остаётся draft/open/unmerged.
