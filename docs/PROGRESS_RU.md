# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- Frozen pilot полностью отрендерен: **15/15** и визуально принят пользователем.
- Первый real long-run slot успешно готов:

```text
D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.mp4
D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.upload.json
```

- Scheduler runner dry-run после slot16:

```text
OpenAI spent: $0.1885 / $10.00
auto_publish: False
publication gate: PASS
long_run: True
slot 17: ai_short / en -> ...slot-17-en-ai.mp4
SUCCESS: scheduled longrun-next completed.
```

Следующий missing target = **slot 17 AI EN**.

## Long-run cat sourcing — validated in real run

Рабочая policy:

- source IDs последних 5 rendered cat episodes protected;
- never-used remote stock first;
- cooled older Pexels/Pixabay allowed only as fallback;
- failed-attempt accepted local stock recovered;
- if remote stock minimum fails, local Pexels/Pixabay history outside cooldown may seed fallback;
- seeded local history is revalidated by current 9:16 + audible-audio gates;
- quality/license/vision/minimum-count gates unchanged.

Slot16 success реально подтвердил этот fallback.

## Long-run schedule

```text
16 cats EN (#008) — SUCCESS
17 AI EN            — NEXT
18 cats EN (#009)
19 AI EN
20 cats EN (#010)
21 AI EN
22 cats EN (#011)
23 AI EN
24 cats RU (#012)
...
```

AI subject cooldown = последние 6 distinct visual anchors. Cat descriptions имеют deterministic variation. Attempt state = `runtime/long_run/state.json`. Existing ready MP4 = resume marker.

## Windows Task Scheduler — 3 nightly triggers approved

Пользователь одобрил недельный test с **до 3 generated videos per night**.

Approved Moscow-time triggers:

```text
01:30
03:30
05:30
```

Installer updated: одна Windows Scheduled Task может иметь несколько daily triggers.

Default:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1
```

регистрирует 01:30,03:30,05:30.

Custom `-At "HH:mm"` всё ещё работает; также поддерживается comma/semicolon-separated список.

Runtime behavior:

- один `longrun-next` на trigger;
- `vv status` before generation;
- `runtime/scheduler/longrun-task.log`;
- exclusive lock + Task Scheduler `IgnoreNew` prevent overlap;
- if prior render is still running, later trigger is skipped rather than parallelized;
- failure exits nonzero; next trigger resumes same missing slot;
- no git pull / no code update / no publishing;
- `auto_publish=false` unchanged.

Поэтому это **до 3/day**. За 7 дней максимум = **21 generated videos**.

OpenAI cost planning estimate based on observed usage = roughly **$0.25–0.50/week** for 21 videos, with hard cap still `$10`.

## Tests / CI

Multi-trigger installer checkpoint:

```text
92145209f9bc68eba3fcbe5e7a2e27725cd2f036
6838930aeba02441176d5fabd6bb9653697be48f
```

Ubuntu test job for this checkpoint:

```text
114 passed in 0.64s
publication gate: PASS
long_run: True
```

Windows CI dry-run now validates both:

- default 3-trigger installer plan;
- custom single-trigger `-At "12:00"` plan.

Workflow run = `33326252717`; recheck live status before claiming full Windows completion.

## Immediate next local step

```powershell
cd D:\KiraS\VV_knopka
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1 -DryRun
```

Expected key lines:

```text
Schedule  : daily at 01:30, 03:30, 05:30
Triggers  : 3 per day
DRY RUN: scheduled task was not registered.
```

Then real install:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1
```

Expected after registration:

```text
Registered: VV Knopka Long Run
State     : Ready
Triggers  : 3
Next run  : ...
```

After first night inspect:

```powershell
Get-Content .\runtime\scheduler\longrun-task.log -Tail 100
Get-ChildItem .\runtime\ready_for_review\slot-*.mp4 | Sort-Object Name | Select-Object -Last 10
```

Publishing stays manual/review-first; uploader/OAuth not implemented. Draft PR #1 remains open/draft/unmerged.
