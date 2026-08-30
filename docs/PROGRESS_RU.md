# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- Frozen pilot полностью отрендерен: **15/15** и визуально принят пользователем.
- Long-run local validation дошёл до первого реального SUCCESS.

Успешный post-pilot output:

```text
D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.mp4
D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.upload.json
```

Последняя команда завершилась:

```text
Long-run conveyor outputs:
D:\KiraS\VV_knopka\runtime\ready_for_review\slot-16-en-animals.mp4
```

Slot 16 = EN cats / cat episode #008. Следующий missing target должен быть **slot 17 ai_short / en**.

## Что реально подтвердил slot 16

До success были два fail-closed `1/5` sourcing attempts. Финальный рабочий механизм:

- long-run блокирует источники последних 5 rendered cat episodes;
- never-used remote stock остаётся первым приоритетом;
- старые Pexels/Pixabay outside cooldown могут вернуться как fallback;
- existing accepted fresh clip из failed slot audit сохраняется;
- если remote search не находит минимум, local Pexels/Pixabay history outside cooldown может seed fallback;
- local history повторно проходит current 9:16 + audible-audio checks;
- recent protected sources не seedятся;
- quality/license/vision/minimum-count gates не ослаблены.

Этот fallback теперь подтверждён реальным готовым MP4.

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

## Windows Task Scheduler — IMPLEMENTED

Добавлены:

```text
scripts/run-longrun-task.ps1
scripts/install-longrun-task.ps1
```

Runner:

- один `longrun-next` за запуск;
- `vv status` перед generation;
- лог `runtime/scheduler/longrun-task.log`;
- exclusive lock против overlapping runs;
- no `git pull` / no auto-update;
- no publishing;
- generation failure = nonzero, следующий run resume того же slot;
- `-DryRun` не генерирует видео.

Installer:

- один daily Windows Scheduled Task;
- время задаётся явно `-At "HH:mm"`;
- текущий interactive Windows user, пароль не запрашивается и не хранится;
- StartWhenAvailable;
- IgnoreNew при overlap;
- execution limit 4h;
- battery run allowed;
- `-DryRun` ничего не регистрирует.

## Tests / CI

Scheduler code checkpoint:

```text
commit: 1844ddf3c5f39734989b99cf5c3a05df04ae33d6
workflow run: 33325562523
114 passed
publication gate: PASS
long_run: True
```

Workflow = `success` полностью:

- Ubuntu tests green;
- Windows bootstrap green;
- scheduler runner dry-run green;
- scheduler installer dry-run green.

Docs commits после scheduler code checkpoint двигают branch HEAD.

## Immediate next local step

Подтянуть scheduler scripts и проверить их без реальной генерации:

```powershell
cd D:\KiraS\VV_knopka
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\run-longrun-task.ps1 -DryRun
```

Ожидается:

```text
OpenAI spent: ... / $10.00
auto_publish: False
publication gate: PASS
long_run: True
slot 17: ai_short / en -> ...slot-17-en-ai.mp4
```

После этого нужно получить от пользователя желаемое **локальное время ежедневного запуска** и установить task:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1 -At "HH:mm"
```

Publishing остаётся manual/review-first; uploader/OAuth пока не реализованы. Draft PR #1 остаётся open/draft/unmerged.
