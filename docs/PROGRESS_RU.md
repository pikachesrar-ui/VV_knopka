# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний показанный OpenAI ledger до английских финальных тестов: **$0.0618 / $10.00**; не угадывать текущее значение, получить через `vv status`.
- Последний явно показанный локальный pytest до conveyor-кода: **81 passed in 0.55s**. GitHub code-head CI ниже уже имеет больше тестов.
- Slot 1 RU AI = manual **QUALITY PASS**.
- Slot 2 RU cats = manual **QUALITY PASS**.
- Slot 3 EN AI facts = manual **QUALITY PASS** по текущему сообщению пользователя.
- Slot 4 EN cats = manual **QUALITY PASS** по текущему сообщению пользователя.
- Значит обе ветки подтверждены визуально и на RU, и на EN; текущий этап — запуск review-first конвейера.

## Cat production / YouTube CC

Первый production-safe YouTube CC источник остаётся:

```text
I_pdwiLlvuc | Kawaiipets
YouTube Creative Commons Attribution
2160x3840
Audio mean -14.8 dB
Full clean gate PASS 0.99
```

Плохие кандидаты (Pawcsu branding/captions, livestream UI, stitched compilation, bad aspect) остаются rejects. Не ослаблять clean/rights/9:16/audio gates и не вводить обязательную квоту YouTube-клипов.

Cat формат принят: generic numbered cats, Impact, real meow, без voiceover/BGM, strict near-9:16, Pexels/Pixabay fallback.

## Cross-episode source reuse gate — IMPLEMENTED

Новый `src/vv_knopka/source_history.py` проверяет `provider + provider_id` текущего cat source manifest против ранее отрендеренных cat slots.

Политика:

- 0–1 повтор в одном новом выпуске допустим;
- 2+ уже использованных source identities -> fail closed **до highlight/render**;
- audit пишется в `runtime/slots/XX/source_reuse_audit.json`.

Это не пытается ослаблять sourcing; при срабатывании надо обновить source pool слота.

## Review-first conveyor — IMPLEMENTED

Новый `src/vv_knopka/pilot_conveyor.py` и команды CLI:

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Поведение:

1. читает frozen 15-slot manifest;
2. non-empty MP4 в `runtime/ready_for_review` считается готовым/resumable slot marker;
3. выбирает следующие отсутствующие slots по порядку;
4. AI slot: создаёт plan только если его нет, обеспечивает MPT availability, затем `render-ai`;
5. cat slot: `render-animal` со всеми существующими source/clean/audio/aspect/history gates;
6. останавливается на первой ошибке;
7. пишет checkpoint в `runtime/conveyor/state.json`;
8. никогда не публикует и требует `auto_publish=false` + publication gate PASS;
9. OpenAI ledger остаётся hard `$10` guard.

### MPT lifecycle

Если MPT уже запущен пользователем, conveyor использует его и не завершает.

Если MPT offline, conveyor пытается найти локально:

```text
MoneyPrinterTurbo/.venv/Scripts/python.exe
MoneyPrinterTurbo/venv/Scripts/python.exe
MoneyPrinterTurbo/.venv/bin/python
MoneyPrinterTurbo/venv/bin/python
```

и только затем `uv`, если он есть в PATH. Это важно, потому что на пользовательском Windows `uv` ранее не был доступен. Самостоятельно поднятый conveyor-ом MPT логируется в `runtime/conveyor/mpt.log` и завершается после batch.

## Upload metadata sidecars — IMPLEMENTED

Каждый новый успешный render теперь пишет рядом с MP4:

```text
slot-XX-...upload.json
```

Sidecar содержит:

- `youtube_title`;
- `youtube_description`;
- language / pipeline / video path;
- обязательные YouTube CC attribution lines из `sources.json`;
- `review_required=true`;
- `auto_publish=false`;
- `publication_allowed_by_conveyor=false`.

Cat external title family:

```text
RU: Котики, которые сделали мой день 😹 #001 #shorts
EN: Cats That Made My Day 😹 #002 #shorts
```

Номер cats считается по animal episode index (slot 2=#001, slot 4=#002, slot 6=#003...). On-card identity остаётся `#NNN — Котики/Cats`.

AI title берётся из конкретного plan title и получает `#shorts`; без общего повторяющегося `Did You Know...?` шаблона.

При первом запуске conveyor также best-effort создаёт `.upload.json` для уже существующих slot 1–4, если хватает старых plan/source metadata.

## CI

Code-head CI после conveyor + metadata + source-history tests:

```text
92 passed in 0.38s
Verify pilot lock: success
```

Windows-bootstrap для этого exact head на момент последней проверки ещё выполнялся; не утверждать full workflow green без нового live check.

## Immediate next local step

Пользователь уже визуально принял slot 1–4. Теперь:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe pilot-next --dry-run
```

Ожидаемо dry-run должен показать **slot 05 / ai_short / en**, если локальные MP4 slot 1–4 лежат под стандартными именами в `runtime/ready_for_review`.

После этого проверить один настоящий unattended step:

```powershell
.\.venv\Scripts\vv.exe pilot-next
```

Если slot 5 успешно появляется в `ready_for_review`, следующий этап — `pilot-batch --count 3`, затем уже Windows Task Scheduler. Не подключать uploader/OAuth до отдельного решения пользователя; `auto_publish=false` остаётся frozen.

Draft PR #1 остаётся open/draft, не merge без отдельного решения пользователя.
