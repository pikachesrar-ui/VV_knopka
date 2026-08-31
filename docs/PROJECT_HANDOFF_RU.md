# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Рабочая ветка `mvp/pilot-scaffold`. Draft PR #1 открыт и **не merge** без отдельного решения пользователя.

## Цель

Автономный long-run pipeline:

`идея/факт -> validation -> render -> metadata -> YouTube upload -> publication verification -> statistics`

Текущий work block = YouTube v2 + AI fact-check + local AI-music. TikTok отложен.

## Реальный checkpoint — 2026-08-31

Подтверждено на Windows ПК:

- frozen pilot 15/15 визуально принят;
- slot 16 EN cats / #008 готов локально;
- всего ready локально: **16**;
- YouTube OAuth/channel binding работают;
- slots **1–11** опубликованы через API и `VERIFIED_PUBLIC`;
- pending queue = **5**, slots 12–16;
- next generation target = slot 17 AI EN, но backlog-first policy блокирует его до pending=0;
- OpenAI ledger = **$0.1885 / $10.00**.

Реальный канал: `Knopka322`.

## Scheduler

Task `VV Knopka Long Run` установлен и `Ready`:

```text
01:30 MSK
03:30 MSK
05:30 MSK
Russian Standard Time (UTC+03:00)
```

Real unattended validation passed:

- scheduler сам upload'нул slot 11;
- slot 11 стал `VERIFIED_PUBLIC`;
- следующая попытка получила `uploadLimitExceeded`;
- uploader записал conservative 24h cooldown без traceback;
- pending уменьшился 6 -> 5.

Backlog-first trigger policy:

1. status;
2. verify receipts;
3. best-effort stats;
4. pending > 0 => upload exactly one oldest and stop;
5. pending == 0 => generate exactly one next slot;
6. upload only newest generated video;
7. deferred/failure blocks further backlog growth.

## YouTube v2

Реализовано:

- hashtags в descriptions;
- cat CTA rotation;
- planner AI hashtags reused;
- `snippet.tags`;
- metadata v2;
- real long-run auto-publish semantics;
- conditional `containsSyntheticMedia`;
- `vv-youtube verify` processing/privacy/failure checks;
- `vv-youtube stats` snapshots/history;
- `vv-youtube report` age-aware views/hour + engagement metrics.

Первый реальный stats sample = 11 videos; пока слишком маленький для optimisation decisions.

## AI fact-check

Long-run AI plan fail-closed до рендера:

```text
plan candidate
 -> bounded OpenAI web-search evidence check
 -> PASS => promote to plan.json
 -> FAIL => no render/no publish
```

Стоимость идёт в общий `$10` ledger.

## MoneyPrinterTurbo

`MPTProcessManager` умеет самостоятельно поднять MPT, дождаться readiness и закрыть только собственный процесс после render. Постоянно открытый MPT PowerShell не является целевой зависимостью.

## AI background music — real local validation passed

Production flag пока **OFF**:

```toml
[music]
enabled = false
```

На RTX 3060 пользователя успешно:

- установлен официальный `ACE-Step-1.5` через `scripts/setup-acestep-windows.ps1`;
- создан Python 3.11 environment через `uv`;
- подтверждён local API auto-start;
- исправлен реальный `httpx.ReadTimeout` на long `/query_result` polling: timeout теперь retry до общего deadline;
- после fix сгенерированы все 8 candidate WAVs:

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

Candidates лежат в `runtime/assets/music/candidates/` и production selector их не видит.

Пользователь прослушал часть треков и сообщил, что они нравятся. **Не считать это approval всех 8**: exact subset ещё нужно получить от пользователя.

Promotion:

```powershell
.\.venv\Scripts\vv-music.exe approve <selected wav names>
```

Даже после approve feature flag сам не включается.

Music pipeline также уже умеет:

- deterministic rotation + cooldown;
- pipeline-specific categories;
- quiet AI/cat volumes;
- sidechain ducking;
- per-slot SHA256 audit;
- mute MPT BGM when local music is used;
- set YouTube synthetic-media disclosure when AI-generated music реально applied.

## Safety / rules

- OpenAI hard cap = **$10**;
- no new paid providers without explicit approval;
- secrets stay ignored/local;
- source/provenance/audio/geometry/vision gates fail closed;
- generated ACE-Step tracks still require human quality review;
- PR #1 stays draft/open/unmerged until explicit user decision.

## Current CI nuance

Last fully green checkpoint before runtime timeout fix:

```text
936bd095... | 147 tests | Ubuntu PASS | Windows PASS
```

Timeout fix:

```text
795b7f01 — ACE-Step polling timeout retry
463f2d5d — regression test
```

Workflow `33429860042`: Ubuntu PASS; Windows was still running at last check. Re-check before claiming current HEAD fully green.

## Immediate continuation

1. get exact approved music track names from user;
2. promote only those candidates;
3. keep `music.enabled=false` until explicit activation decision;
4. scheduler keeps draining slots 12–16;
5. after pending=0 validate slot 17 end-to-end;
6. later run controlled music ON vs OFF comparison using `vv-youtube report`.

TikTok remains out of scope.
