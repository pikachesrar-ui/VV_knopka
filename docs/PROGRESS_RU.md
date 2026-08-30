# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- Frozen pilot полностью отрендерен: **15/15** и визуально принят пользователем.
- Последний показанный long-run test run:

```text
111 passed in 1.23s
vv longrun-next --dry-run -> slot 16 animal_compilation / en
```

- Реальный retry slot 16 снова остановился fail-closed:

```text
Vertical audible-source gate found only 1/5 usable cat clips
```

`runtime/slots/16` не удалять: failed audit содержит один уже принятый fresh local source.

## Уточнённый root cause

Rolling cooldown сам по себе не решает depletion. Он делает старые IDs снова **разрешёнными**, но current Pexels/Pixabay search не обязан заново вернуть те же старые IDs. Поэтому slot16 снова остался на `1/5`, хотя cat #001/#002 уже вышли из cooldown.

## Fix — cooled local history fallback

Текущая long-run policy:

```toml
[long_run]
cat_source_cooldown_episodes = 5
```

Поведение:

- pilot сохраняет all-history source protection;
- long-run блокирует IDs последних 5 rendered cat episodes;
- never-used remote stock остаётся первым приоритетом;
- older cooled-down remote IDs допустимы как fallback;
- после фактического fresh minimum-count failure система дополнительно может seed локальные Pexels/Pixabay files из rendered episodes вне cooldown;
- local historical files повторно проходят current near-9:16 и audible-audio проверки перед acceptance;
- YouTube и прочие providers этим fallback не импортируются;
- на retry после существующего minimum-count audit accepted fresh clips сначала восстанавливаются, затем cooled local history добавляется **без повторения того же fresh discovery pass**;
- если fresh failure случается впервые, recover+local fallback выполняется в том же `vv longrun-next` invocation;
- final reuse audit отдельно фиксирует cooled-down reuse и продолжает fail-closed на protected recent overlap.

Для slot 16 protected cat episodes = #003–#007. Eligible local fallback = ранние #001/#002. Один свежий slot16 clip должен остаться первым в manifest.

## Tests / CI

Code-head `91e2932e2d9e3e2868288584664fabb6f84bc3d9`:

```text
114 passed in 0.69s
publication gate: PASS
long_run: True
vv longrun-next --dry-run -> slot 16 EN cats
```

Ubuntu test job green. Windows bootstrap этого run на момент последней проверки ещё выполнялся; recheck live before claiming full workflow green. Docs-only commits после code-head двигают branch HEAD.

Новые regressions проверяют:

- local history seed не берёт recent-blocked source;
- retry с failed `1/5` audit сохраняет fresh clip и затем добавляет cooled local stock;
- first fresh minimum failure может перейти к local fallback в том же invocation.

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

Ожидается около `114 passed` и снова slot 16.

Потом:

```powershell
.\.venv\Scripts\vv.exe longrun-next
```

Не чистить slot16 перед retry. Если slot 16 успешно готов — визуально проверить его и `runtime/slots/16/source_reuse_audit.json`, после чего следующий milestone = Windows Task Scheduler. Publication остаётся manual/review-first; `auto_publish=false`.

Draft PR #1 остаётся open/draft/unmerged.
