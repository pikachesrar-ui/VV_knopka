# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Frozen pilot: **15/15**, визуально принят.
- Real long-run slot 16 EN cats / #008: SUCCESS.
- Scheduler dry-run после slot16: target slot17 AI EN.
- Последний показанный OpenAI ledger: `$0.1885 / $10.00`.

## Пользователь разрешил публикацию

Явный новый intent:

- будущие long-run videos сразу публиковать на YouTube;
- existing ready videos также загрузить.

Config `[youtube]` теперь включает `enabled=true`, `auto_publish=true`, `privacy_status="public"`.
Frozen `[pilot] auto_publish=false` оставлен только как историческая настройка завершённого pilot.

## YouTube uploader — IMPLEMENTED

CLI:

```powershell
.\.venv\Scripts\vv-youtube.exe status
.\.venv\Scripts\vv-youtube.exe auth
.\.venv\Scripts\vv-youtube.exe upload-ready --dry-run
.\.venv\Scripts\vv-youtube.exe upload-ready
```

Local files:

```text
runtime/youtube/client_secret.json
runtime/youtube/token.json
runtime/youtube/channel.json
```

`runtime/` ignored, secrets/tokens не коммитятся.

Safety/idempotency:

- OAuth scopes = upload + readonly;
- `auth` bind'ит конкретный channel ID;
- каждый upload перепроверяет current channel against binding;
- successful upload пишет `.upload.youtube.json` receipt;
- retries skip receipts, поэтому existing backlog можно безопасно продолжить после interruption;
- receipt пишет requested/actual privacy и YouTube video ID/URL.

Official API caveat: unverified/audit-restricted API projects may have `videos.insert` uploads forced to private. Проверять `actual_privacy`, а не предполагать public.

## Existing backlog

На локальной машине ready outputs минимум slots 1–16.
После OAuth:

```powershell
.\.venv\Scripts\vv-youtube.exe upload-ready --dry-run
.\.venv\Scripts\vv-youtube.exe upload-ready
```

Dry-run ничего не загружает. Реальный вызов идёт oldest-slot-first.

## Scheduler — generation + publication

Approved triggers:

```text
01:30 MSK
03:30 MSK
05:30 MSK
```

Каждый run теперь:

1. lock;
2. generation status;
3. YouTube status;
4. retry one old pending upload;
5. generate one next long-run slot;
6. upload newest pending video;
7. log.

Если старый pending upload не проходит, новый slot не генерируется. Если новый MP4 готов, но upload упал, следующий trigger сначала retry publication.

## Tests / CI

YouTube uploader добавил 3 regression tests:

- backlog numeric order;
- newest dry-run without OAuth/network;
- duplicate prevention via receipt.

Uploader code-head Ubuntu result:

```text
117 passed in 0.77s
publication gate: PASS
long_run: True
```

Windows bootstrap для этого uploader head на момент первой проверки ещё выполнялся; recheck live before claiming full workflow green.

## Immediate next local step

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\vv-youtube.exe status
```

Дальше Google Cloud one-time setup:

- enable YouTube Data API v3;
- create OAuth Client ID type **Desktop app**;
- download JSON to `runtime\youtube\client_secret.json`;
- не вставлять JSON/token в чат.

Потом:

```powershell
.\.venv\Scripts\vv-youtube.exe auth
```

Пользователь должен прислать только строку `YouTube channel bound: <title> (<id>)`. После проверки канала — backlog dry-run, real upload, затем scheduler install.

Draft PR #1 остаётся open/draft/unmerged.
