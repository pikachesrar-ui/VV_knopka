# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- Frozen pilot полностью отрендерен: **15/15** и визуально принят пользователем.
- После первого long-run pull:

```text
108 passed in 0.99s
OpenAI spent: $0.1786 / $10.00
auto_publish: False
publication gate: PASS
long_run: True
```

- `vv longrun-next --dry-run` корректно определил:

```text
slot 16: animal_compilation / en -> ...slot-16-en-animals.mp4
```

## Первый реальный long-run slot — safe failure

`vv longrun-next` начал slot 16 EN cats, но sourcing остановился:

```text
Vertical audible-source gate found only 1/5 usable cat clips
```

Это подтвердило, что schedule/CLI/resume работают, но старая all-history source exclusion не подходит для бесконечной эксплуатации: после семи pilot cat episodes почти весь доступный vertical + audible stock уже считался навсегда запрещённым.

Не удалять `runtime/slots/16`: failed audit содержит один уже валидированный fresh clip и v5 recovery может его переиспользовать при retry.

## Fix — rolling cat source cooldown

Текущая политика:

```toml
[long_run]
cat_source_cooldown_episodes = 5
```

Поведение:

- pilot slots сохраняют all-history source protection;
- long-run защищает source IDs из последних 5 rendered cat episodes;
- более старый source становится eligible fallback;
- после повторного использования source снова попадает в cooldown;
- never-used stock ранжируется раньше cooled-down reuse;
- последние 5 episodes исключаются ещё до Luna/candidate selection;
- final audit отдельно показывает recent protected overlap и `reused_cooled_down_sources`;
- provenance/commercial-use, near-9:16, audible audio, Luna relevance и minimum 5 unique clips не ослаблены.

Для slot 16 / cat #008 protected episodes = cat #003–#007; sources из #001/#002 могут вернуться только после fresh search как fallback.

## Tests / CI

Новые regressions проверяют:

- rolling window выбирает ровно последние 5 rendered cat slots;
- старые cooled-down identities не считаются recent reuse failure;
- fresh Pexels result на более глубокой странице приоритетнее старого cooled candidate с первой страницы;
- существующий pilot all-history reuse gate остаётся прежним.

Code-head `487ccd6946c2a3e5ed405f6619f904e02d3dd7bf`:

```text
111 passed in 0.70s
publication gate: PASS
long_run: True
vv longrun-next --dry-run -> slot 16 EN cats
```

Workflow run `33323215094` завершён `success`: Ubuntu test и Windows bootstrap оба green. Последующие docs-only commits двигают branch HEAD; exact CI выше относится к указанному code commit.

## Long-run schedule / other features

```text
16 cats EN (#008)
17 AI EN
18 cats EN (#009)
19 AI EN
20 cats EN (#010)
21 AI EN
22 cats EN (#011)
23 AI EN
24 cats RU (#012)
```

AI subject cooldown = последние 6 distinct visual anchors. Cat descriptions имеют deterministic variation. Attempt state = `runtime/long_run/state.json`. Existing ready MP4 = resume marker.

## Immediate next local step

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe longrun-next --dry-run
```

Ожидается около `111 passed` и снова slot 16.

Потом:

```powershell
.\.venv\Scripts\vv.exe longrun-next
```

Если slot 16 успешно готов — визуально проверить его и `runtime/slots/16/source_reuse_audit.json`, после чего следующий milestone = Windows Task Scheduler. Publication остаётся manual/review-first; `auto_publish=false`.

Draft PR #1 остаётся open/draft/unmerged.
