# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-31**. Подробный контекст — `AGENT.md`, `docs/PROJECT_HANDOFF_RU.md`, `docs/AI_MUSIC_RU.md`.

## Реальный локальный checkpoint

Подтверждено на Windows ПК пользователя:

```text
готово локально: 16 Shorts
YouTube receipts: 11
published + VERIFIED_PUBLIC: slots 1–11
pending: slots 12–16 (5)
next generation target: slot 17 AI EN
OpenAI spent: $0.1885 / $10.00
```

`vv-youtube verify` для slots 1–11:

```text
upload=processed
processing=succeeded
privacy=public
publication_state=VERIFIED_PUBLIC
```

## Windows scheduler — production validation passed

Task `VV Knopka Long Run` установлен и `Ready`:

```text
01:30 MSK
03:30 MSK
05:30 MSK
Russian Standard Time (UTC+03:00)
```

Реальный unattended run подтвердил backlog-first flow:

1. scheduler сам опубликовал slot 11;
2. slot 11 стал `VERIFIED_PUBLIC`;
3. следующая upload opportunity получила `uploadLimitExceeded`;
4. uploader сохранил cooldown без traceback;
5. pending уменьшился до 5.

Последний показанный cooldown:

```text
2026-09-01T00:30:07.333703+00:00
```

Во время active cooldown upload endpoint не hammer'ится.

## YouTube v2 — DONE

Для новых long-run slots:

- hashtags в description;
- CTA rotation для cats;
- planner AI hashtags реально используются;
- `snippet.tags` передаются через API;
- normalization/dedupe/caps;
- `metadata_version=2`;
- long-run metadata отражает реальный YouTube auto-publish;
- frozen pilot остаётся historical review-first;
- conditional `containsSyntheticMedia`;
- `vv-youtube verify`, `stats`, `report` работают на реальном канале.

Первый real stats snapshot = 11 videos. Sample пока слишком маленький для optimisation decisions.

## Long-run AI fact-check — DONE

```text
plan candidate
 -> max 1 bounded web-search call
 -> structured evidence verdict
 -> PASS => plan.json
 -> FAIL => no render/no publish
```

Model cost + fixed web-search fee идут в общий `$10` BudgetLedger.

## MoneyPrinterTurbo autonomy — DONE in code

`MPTProcessManager` умеет сам поднять локальный MPT, дождаться readiness, выполнить AI render и остановить только процесс, который он сам запустил. Постоянно открытый PowerShell с MPT больше не является целевой зависимостью.

## AI background music — REAL LOCAL GENERATION PASSED

Production music всё ещё намеренно выключена:

```toml
[music]
enabled = false
```

На реальном RTX 3060 ПК пользователя успешно подтверждено:

1. `scripts/setup-acestep-windows.ps1` клонировал официальный `ACE-Step-1.5`;
2. Python 3.11 / `uv sync` setup прошёл;
3. локальный ACE-Step API стартует через `vv-music`;
4. первый реальный run выявил `httpx.ReadTimeout` при `/query_result` polling;
5. клиент исправлен: polling `ReadTimeout` теперь считается transient и retry'ится до общего deadline;
6. regression test добавлен;
7. после `git pull` повторный запуск успешно сгенерировал все **8 WAV candidates**:

```text
cute_01.wav
cute_02.wav
playful_01.wav
playful_02.wav
curious_01.wav
curious_02.wav
calm_01.wav
calm_02.wav
```

Файлы лежат только в:

```text
runtime/assets/music/candidates/
```

и не могут попасть в production rotation до explicit `vv-music approve ...`.

Пользователь уже прослушал несколько candidates и сообщил, что музыка нравится. Точный approved subset ещё не выбран.

### Реализованная music infrastructure

- local library + FFmpeg mixer;
- ACE-Step async REST client;
- API auto-start/wait/stop;
- candidate/approved separation;
- `vv-music status/list/generate-library/approve`;
- deterministic rotation + cooldown;
- SHA256 per-slot audit;
- separate quiet volumes for AI/cats;
- sidechain ducking;
- MPT BGM muted when approved local music is applied;
- applied AI-generated music propagates YouTube disclosure.

## CI

Последний полностью зелёный checkpoint до runtime timeout fix:

```text
head: 936bd0956ad0c08fb236c1a97aada6ff0464e88d
workflow: 33419768393
pytest: 147 passed
Ubuntu: PASS
Windows: PASS
```

Runtime timeout fix commits:

```text
795b7f01 — retry ACE-Step polling read timeouts
463f2d5d — regression test
```

Ubuntu job на workflow `33429860042` уже PASS; Windows bootstrap ещё выполнялся при последней проверке. Не называть весь current HEAD fully green, пока Windows не завершён.

## Следующий шаг

1. пользователь прослушивает оставшиеся 8 candidates;
2. сообщает, какие конкретно tracks допускаются в production;
3. только выбранные файлы promoted через `vv-music approve ...`;
4. после этого отдельно решаем, включать ли `[music].enabled=true`;
5. scheduler продолжает draining slots 12–16;
6. после pending=0 validate slot 17 end-to-end:

```text
plan -> fact-check -> MPT auto-start -> curated stock -> render -> metadata v2 -> YouTube -> verify/stats
```

TikTok пока не трогать.

Draft PR #1 остаётся open/draft/unmerged.
