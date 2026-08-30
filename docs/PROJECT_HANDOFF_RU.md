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

## Manual quality / latest local state

Пользователь визуально принял proof pair обеих веток:

- slot 1 RU AI facts = QUALITY PASS;
- slot 2 RU cats = QUALITY PASS;
- slot 3 EN AI facts = QUALITY PASS;
- slot 4 EN cats = QUALITY PASS.

Latest explicitly shown local state:

```text
99 passed in 0.67s
OpenAI spent: $0.1036 / $10.00
auto_publish: False
publication gate: PASS
```

Не угадывать более новый ledger/test count без нового user output.

## Conveyor validation status

Slot 5 EN AI был первым successful `pilot-next` render.

Последний `pilot-batch --count 3` затем сделал:

1. **slot 6 EN cats — SUCCESS**
   - 6 audible vertical licensed sources;
   - cross-episode source reuse audit PASS;
   - highlight selection PASS;
   - final `runtime/ready_for_review/slot-06-en-animals.mp4` + `.upload.json`;
   - final 1080x1920, ~35.75 s.
2. **slot 7 EN AI — SUCCESS**
   - plan-on-demand;
   - 8 curated stock materials;
   - MPT render;
   - final `runtime/ready_for_review/slot-07-en-ai.mp4` + `.upload.json`.
3. **slot 8 EN cats — STOPPED ON CODE BUG**, not source/quality policy.

Это важный proof: conveyor уже самостоятельно прошёл cat -> AI -> next cat без ручного вмешательства до software exception.

## Slot 8 Pixabay bug and fix

Ошибка:

```text
AttributeError: module 'vv_knopka.animal_audio_sources' has no attribute 'choose_pixabay_file'
```

`animal_audio_sources_v4.py` deep Pixabay collector ошибочно вызывал:

```text
_base.choose_pixabay_file
_base._text_matches_anchor
```

Оба helpers находятся в `pexels_curator.py`, а base animal module их не экспортирует. Первая ссылка упала; вторая была latent next-line failure.

Fix:

- direct import `choose_pixabay_file` from `pexels_curator`;
- direct import `_text_matches_anchor` from `pexels_curator`;
- dedicated regression test for Pixabay-like payload verifies file selection and tag-anchor path.

Latest code-head test job for the fix:

```text
100 passed in 0.60s
Verify pilot lock: success
```

Windows-bootstrap exact-head status надо recheck live перед full-CI claim.

## Cat sourcing architecture

Первый production-safe YouTube CC source остаётся `I_pdwiLlvuc` / Kawaiipets / Creative Commons Attribution / 2160×3840 / audio -14.8 dB / clean gate PASS 0.99.

Не вводить mandatory YouTube quota. Production automated acquisition primarily uses explicitly downloadable/licensed Pexels/Pixabay stock; keep rights / clean-footage / near-9:16 / audible-audio gates.

Cross-episode history final gate: максимум 1 incidental reused `provider + provider_id`; 2+ -> fail closed.

Deep history-aware sourcing (`animal_audio_sources_v4.py`):

- prior rendered IDs excluded during collection;
- Pexels/Pixabay pagination up to 4 pages/query;
- extra cat query diversity;
- same candidate caps and quality gates.

Retry recovery (`animal_audio_sources_v5.py`): if a failed minimum-count attempt wrote `animal_audio_sources.json`, reuse existing fresh local Pexels/Pixabay `selected_sources` before searching again. Do not shortcut YouTube through this recovery.

## Review-first conveyor

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

- strict manifest order;
- non-empty expected MP4 = completion marker/resume boundary;
- state in `runtime/conveyor/state.json`;
- AI: plan-on-demand + managed/check MPT + render;
- cats: fresh licensed sourcing + audio/aspect/vision/history gates + local FFmpeg;
- stop on first failure;
- outputs only `runtime/ready_for_review`;
- `$10` OpenAI hard guard;
- `auto_publish=false`; no uploader/OAuth yet.

MPT manager prefers local `.venv/venv` Python before `uv`; if MPT already runs externally, conveyor does not terminate it.

## Upload metadata / titles

Each successful render creates `.upload.json` with proposed title/description, language/pipeline/video path, attribution, `review_required=true`, `auto_publish=false`, `publication_allowed_by_conveyor=false`.

Cat external title family: `Cats That Made My Day 😹 #NNN #shorts`; on-card remains `#NNN — Cats`. AI title comes from each specific fact plan.

## Immediate local continuation

Because slot 6 and slot 7 now exist as final ready MP4s and slot 8 does not, after pull the next pending slot must be **slot 8**.

Use a one-slot retry first:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe pilot-next --dry-run
.\.venv\Scripts\vv.exe pilot-next
```

Expected tests around **100 passed** and dry-run `slot 08: animal_compilation / en`.

If slot 8 succeeds and the rendered result looks normal, resume larger batching. Do not regenerate slots 6/7 manually; resumability should skip them.

## Git / release

Continue on `mvp/pilot-scaffold`, Draft PR #1. Do not merge until separate user decision after local conveyor validation/review.
