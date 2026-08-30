# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Frozen pilot: **15/15**, визуально принят.
- Real long-run slot 16 EN cats / #008: SUCCESS.
- Scheduler dry-run после slot16: target slot17 AI EN.
- Последний показанный OpenAI ledger: `$0.1885 / $10.00`.
- Google OAuth для YouTube успешно пройден; uploader привязан к реальному каналу.
- Первый real backlog upload запущен и остановлен самим YouTube на channel daily upload limit:

```text
400 uploadLimitExceeded
The user has exceeded the number of videos they may upload.
```

## Что означает ошибка

Это **не Google Cloud quota**. Официальный YouTube `videos.insert` error `uploadLimitExceeded` = достигнут дневной лимит видео на канале. Он общий для desktop/mobile/API. YouTube рекомендует повторить через 24 часа. Daily limit variable; не хардкодить число.

Advanced YouTube feature eligibility обычно даёт higher daily upload limits. Проверка: YouTube Studio → Settings → Channel → Feature eligibility.

## Что уже могло успешно загрузиться

Old `upload-ready` шёл slot-by-slot и после каждого success сразу писал `.upload.youtube.json` receipt. Поэтому до момента ошибки часть slots могла реально успеть загрузиться.

Не угадывать количество. Проверить локально:

```powershell
Get-ChildItem .\runtime\ready_for_review\*.youtube.json | Sort-Object Name | Select-Object Name
(Get-ChildItem .\runtime\ready_for_review\*.youtube.json).Count
```

Receipt = duplicate guard для следующего запуска.

## Fix — graceful daily-limit handling

Добавлено:

- отдельное распознавание `uploadLimitExceeded`;
- CLI больше не должен показывать Python traceback для этого ожидаемого platform condition;
- вывод `DEFERRED ... Retry not before ...`;
- exit code `75` для scheduler;
- local ignored `runtime/youtube/upload-limit.json`;
- conservative 24h cooldown;
- `vv-youtube status` показывает cooldown;
- `vv-youtube pending-count` печатает pending queue size;
- во время active cooldown uploader не hammer'ит YouTube upload endpoint.

## Scheduler — backlog-first, max one upload/trigger

Approved triggers остаются:

```text
01:30 MSK
03:30 MSK
05:30 MSK
```

Новая последовательность каждого trigger:

1. lock/status;
2. count pending uploads;
3. если pending > 0 — upload exactly one oldest pending, затем exit **без generation**;
4. только при pending = 0 — generate one new long-run slot + immediately upload it;
5. deferred/failed publication blocks further generation until recovery.

Это уменьшает upload pressure с потенциальных 6/day до **максимум 3/day** и позволяет backlog реально уменьшаться.

## Tests / CI

Upload-limit code checkpoint:

```text
573bc4f2eb904da20fab03456f90391079144914
```

Ubuntu job:

```text
121 passed in 0.82s
publication gate: PASS
long_run: True
```

Regression coverage:

- Google error reason parser;
- 24h cooldown state;
- backlog stops cleanly at limit after earlier successful item;
- receipted files excluded from pending count.

Windows job этого workflow на первом checkpoint ещё выполнялся; recheck live перед утверждением full green.

## Immediate next local steps

Сначала не повторять `upload-ready` прямо сейчас: YouTube официально рекомендует retry через 24h после daily-limit error.

Проверить, сколько успело загрузиться и какую privacy реально вернул YouTube:

```powershell
Get-ChildItem .\runtime\ready_for_review\*.youtube.json |
  ForEach-Object { Get-Content $_ | ConvertFrom-Json } |
  Select-Object slot, title, requested_privacy, actual_privacy, youtube_url |
  Sort-Object slot
```

Затем проверить YouTube Studio → Settings → Channel → Feature eligibility. Если Advanced features ещё нет, official verification path может увеличить daily upload limit.

Подтянуть fix:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\vv-youtube.exe status
```

После окончания limit window безопасно повторить:

```powershell
.\.venv\Scripts\vv-youtube.exe upload-ready
```

Receipts не дадут залить уже успешные slots повторно.

Draft PR #1 остаётся open/draft/unmerged.
