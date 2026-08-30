# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- Последний локальный pytest: **99 passed in 0.67s**.
- Последний явно показанный OpenAI ledger: **$0.1036 / $10.00**.
- `auto_publish=false`; publication gate = `PASS`.
- Slot 1 RU AI = manual **QUALITY PASS**.
- Slot 2 RU cats = manual **QUALITY PASS**.
- Slot 3 EN AI facts = manual **QUALITY PASS**.
- Slot 4 EN cats = manual **QUALITY PASS**.
- Slot 5 EN AI = первый успешный настоящий conveyor render.
- Slot 6 EN cats = **успешный conveyor render после deep fresh-source sourcing**.
- Slot 7 EN AI = **успешный conveyor render в том же batch**.

Slot 6 успешно собрал 6 audible vertical licensed sources, прошёл cross-episode reuse audit и highlight selection, затем FFmpeg сделал `runtime/ready_for_review/slot-06-en-animals.mp4` + `.upload.json`. Финальный файл: 1080x1920, ~35.75 s. В concat были предупреждения `Non-monotonic DTS`, но render завершился и final MP4 был создан.

Slot 7 затем без ручного вмешательства создал plan, 8 curated stock materials, MPT task и `runtime/ready_for_review/slot-07-en-ai.mp4` + `.upload.json`.

Это уже подтверждает, что один `pilot-batch` способен последовательно завершить cat -> AI и продолжить к следующему slot.

## Slot 8 — кодовый Pixabay blocker

Тот же batch дошёл до slot 8 EN cats и упал не на quality/source gate, а на Python bug:

```text
AttributeError: module 'vv_knopka.animal_audio_sources' has no attribute 'choose_pixabay_file'
```

Причина: `animal_audio_sources_v4.py` deep Pixabay collector обращался к `_base.choose_pixabay_file` и далее должен был обратиться к `_base._text_matches_anchor`, но оба helpers определены в `pexels_curator.py` и не экспортируются базовым `animal_audio_sources` module.

Исправлено:

- `choose_pixabay_file` импортируется напрямую из `pexels_curator`;
- `_text_matches_anchor` импортируется оттуда же;
- добавлен regression test с реальным Pixabay-like payload, проверяющий file selection + tag/anchor metadata path.

Latest code-head test job после фикса:

```text
100 passed in 0.60s
Verify pilot lock: success
```

Windows-bootstrap для exact head на момент проверки мог ещё выполняться; не утверждать full workflow green без live recheck.

## Deep fresh-stock sourcing

`src/vv_knopka/animal_audio_sources_v4.py`:

1. исключает IDs предыдущих реально отрендеренных cat episodes во время сбора;
2. пагинирует Pexels/Pixabay до 4 страниц на query;
3. добавляет query diversity: `cat`, `kitten`, `cute cat`, `funny cat`, `cat playing`, `kitten playing`, `cat meowing`, `cat purring`, `house cat`, `pet cat`;
4. сохраняет duration / near-9:16 / vision / audible-audio / license gates;
5. candidate cap заполняется свежими IDs, а не уже использованными popular results.

`animal_audio_sources_v5.py` делает failed-source retry resumable через `animal_audio_sources.json -> selected_sources` для локальных Pexels/Pixabay clips, если audit успел быть записан.

## Cat production / YouTube CC

Первый production-safe YouTube CC источник остаётся `I_pdwiLlvuc` / Kawaiipets / Creative Commons Attribution / 2160×3840 / audio -14.8 dB / clean gate PASS 0.99.

Не вводить обязательную YouTube quota. Pexels/Pixabay остаются основным автоматически скачиваемым safe fallback. Все rights / clean-footage / near-9:16 / audible-audio gates сохраняются.

## Review-first conveyor

Команды:

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Поведение: strict manifest order; existing ready MP4 = resumable completion marker; state in `runtime/conveyor/state.json`; AI plan-on-demand + MPT; cats use fresh licensed source acquisition + all quality/history gates; stop on first failure; outputs only `runtime/ready_for_review`; no publishing; hard `$10` OpenAI guard.

MPT manager prefers local MPT `.venv/venv` Python and does not require `uv`; if MPT was already running, conveyor leaves it alone.

## Upload metadata

Successful new renders produce `.upload.json` with proposed title/description, language/pipeline/video path, required attribution, `review_required=true`, `auto_publish=false`, `publication_allowed_by_conveyor=false`.

Cat external title family: `Cats That Made My Day 😹 #NNN #shorts`; on-card identity remains `#NNN — Cats`. AI title is derived from the actual fact plan.

## Immediate next local step

Slots 6 and 7 now have final MP4s, while slot 8 does not. Therefore after pulling the Pixabay fix, `pilot-next --dry-run` should identify slot 8.

Recommended validation:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe pilot-next --dry-run
.\.venv\Scripts\vv.exe pilot-next
```

Expected local tests around **100 passed**. `pilot-next` should retry only slot 8, not regenerate slots 6/7. If slot 8 succeeds visually, continue with another `pilot-batch --count 3` for subsequent pending slots.

Draft PR #1 remains open/draft and unmerged.
