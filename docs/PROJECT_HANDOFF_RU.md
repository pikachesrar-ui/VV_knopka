# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

Manifest:

```text
AI slots:     1,3,5,7,9,11,13,15
Animal slots: 2,4,6,8,10,12,14
RU slots:     1,2
```

## Manual quality status

Пользователь визуально принял все четыре proof-of-format ролика:

- slot 1 RU AI facts = QUALITY PASS;
- slot 2 RU cats = QUALITY PASS;
- slot 3 EN AI facts = QUALITY PASS;
- slot 4 EN cats = QUALITY PASS.

Следовательно основной формат обеих веток подтверждён на RU и EN. Текущий milestone — **локальный review-first conveyor**, а не дальнейшие эксперименты с шаблоном.

Последний показанный OpenAI ledger до завершения EN proof pair: `$0.0618 / $10.00`; текущее значение всегда читать через `vv status`, не угадывать.

## Cat / YouTube sourcing

Первый принятый YouTube CC source:

```text
I_pdwiLlvuc | Kawaiipets
YouTube Creative Commons Attribution
2160x3840
Audio mean -14.8 dB
Full clean gate PASS 0.99
```

Не вводить обязательную YouTube quota. Clean YouTube pool может расти со временем; Pexels/Pixabay остаются safe fallback. Все rights / clean-footage / near-9:16 / audible-audio gates сохраняются.

## Cross-episode source history

`src/vv_knopka/source_history.py` добавлен перед масштабированием. Для нового cat slot он сравнивает текущие `provider + provider_id` с source manifests ранее реально отрендеренных cat episodes.

Политика:

```text
0–1 reused source identity -> PASS
2+ reused source identities -> FAIL before highlight/render
```

Audit: `runtime/slots/XX/source_reuse_audit.json`.

Это защита от серии почти одинаковых компиляций. При fail надо обновить source pool, а не ослаблять gate.

## Review-first conveyor

Новый `src/vv_knopka/pilot_conveyor.py` и команды:

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

`pilot-next` = один следующий отсутствующий slot. `pilot-batch` = несколько подряд, строго по manifest, stop-on-first-failure.

Resumability:

- non-empty expected MP4 в `runtime/ready_for_review` считается завершённым slot marker;
- состояние/attempt history: `runtime/conveyor/state.json`;
- существующие slots пропускаются;
- если slot AI и `plan.json` уже есть, plan не генерируется заново.

Safety:

- conveyor запускается только при publication gate PASS;
- `auto_publish=false` обязателен;
- `$10` OpenAI ledger guard сохраняется;
- никакого YouTube upload/OAuth;
- outputs только `runtime/ready_for_review`;
- первая ошибка останавливает batch.

## MPT process management

Обычный `vv render-ai` всё ещё делает ранний MPT healthcheck.

Conveyor умеет дополнительно поднять MPT для unattended AI slot. Порядок поиска executable:

```text
MoneyPrinterTurbo/.venv/Scripts/python.exe
MoneyPrinterTurbo/venv/Scripts/python.exe
MoneyPrinterTurbo/.venv/bin/python
MoneyPrinterTurbo/venv/bin/python
uv (только если есть в PATH)
```

Это учитывает реальный Windows пользователя, где `uv` ранее не распознавался.

Если MPT уже работает — conveyor его использует и не завершает. Если conveyor сам запустил MPT — пишет `runtime/conveyor/mpt.log`, ждёт health readiness, а в конце batch завершает только свой процесс.

## Upload metadata / titles

Новый `src/vv_knopka/publication_metadata.py`. После каждого нового render рядом с видео создаётся `.upload.json`.

Содержит:

- proposed YouTube title;
- proposed description;
- language / pipeline / video path;
- required CC attribution text from `sources.json`;
- `review_required=true`;
- `auto_publish=false`;
- `publication_allowed_by_conveyor=false`.

Cat external titles:

```text
slot 2 cat episode #001: Котики, которые сделали мой день 😹 #001 #shorts
slot 4 cat episode #002: Cats That Made My Day 😹 #002 #shorts
slot 6 cat episode #003: Cats That Made My Day 😹 #003 #shorts
...
```

On-card title remains simple `#NNN — Котики/Cats`.

AI external title uses each plan's own title + `#shorts`, so it remains fact-specific rather than one generic `Did You Know...?` template.

Conveyor best-effort backfills sidecars for already-existing outputs when their old plan/source metadata is sufficient.

## CI

Latest code-head test job after conveyor, sidecars and source-history:

```text
92 passed in 0.38s
Verify pilot lock: success
```

Windows-bootstrap was still in progress at that exact check. Recheck live GitHub before a full-CI claim.

## Immediate local validation

User should pull the latest branch and run:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe pilot-next --dry-run
```

Given standard output filenames for accepted slot 1–4, expected dry-run next item:

```text
slot 05: ai_short / en
```

Then validate one real autonomous iteration:

```powershell
.\.venv\Scripts\vv.exe pilot-next
```

If slot 5 succeeds and lands in `runtime/ready_for_review` with its `.upload.json`, move to:

```powershell
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Only after local conveyor behavior is proven should Windows Task Scheduler cadence be configured. Uploader/OAuth remains a separate later decision.

## Git / release

Continue on `mvp/pilot-scaffold`, Draft PR #1. Do not merge merely because tests pass. The next meaningful manual gate is successful local conveyor validation / review of generated pilot outputs unless the user explicitly changes release policy.
