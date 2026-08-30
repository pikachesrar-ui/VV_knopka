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

Пользователь визуально принял proof pair обеих веток:

- slot 1 RU AI facts = QUALITY PASS;
- slot 2 RU cats = QUALITY PASS;
- slot 3 EN AI facts = QUALITY PASS;
- slot 4 EN cats = QUALITY PASS.

Последний показанный локальный статус после запуска conveyor:

```text
92 passed in 0.79s
OpenAI spent: $0.0887 / $10.00
auto_publish: False
publication gate: PASS
```

Не угадывать более новые local test/ledger значения.

## Первый реальный conveyor success

`pilot-next --dry-run` правильно определил slot 5 как следующий отсутствующий:

```text
slot 05: ai_short / en -> runtime/ready_for_review/slot-05-en-ai.mp4
```

Затем настоящий `pilot-next` успешно выполнил slot 5:

```text
runtime/slots/05/plan.json
Curated stock materials: 8
MPT task: bde437d8-38e1-48c2-bc41-8515a5d68595
runtime/ready_for_review/slot-05-en-ai.mp4
runtime/ready_for_review/slot-05-en-ai.upload.json
```

Это локально подтверждает resumable next-slot selection, plan-on-demand, MPT handling, AI render и metadata sidecar.

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

## Cross-episode source history + automatic refresh

Первоначальный `source_history.py` post-gate разрешает максимум один reused `provider + provider_id` и fail closed при 2+ повторах.

Первый `pilot-batch --count 3` дошёл до slot 6 и корректно остановился, потому что source pool содержал **5 clips уже использованных в предыдущих cat episodes**. Примеры: `pexels:15769301`, `17536779`, `19306625`, `20420481`, `5335581`.

Проблема была не в gate, а в автономности: source picker сначала переиспользовал старые top results, а post-gate требовал ручного refresh.

Исправление: `src/vv_knopka/animal_audio_sources_v3.py`.

Теперь до source review/render:

1. `prior_rendered_cat_identities()` собирает IDs из реально существующих предыдущих cat MP4/source manifests;
2. эти IDs удаляются из текущего `sources.json`;
3. удаляются из slot-local legacy `ai_materials.json` cache;
4. те же IDs отфильтровываются из новых Pexels/Pixabay search results;
5. sourcing автоматически идёт глубже за свежими licensed/audible/near-9:16 clips;
6. старый final reuse audit остаётся второй fail-closed линией защиты.

Старые media files не удаляются с диска.

Чтобы политика применялась и к child processes, текущий console entrypoint:

```text
vv -> vv_knopka.cli_v2:main
```

`cli_v2` подменяет cat sourcing на v3 и conveyor на `pilot_conveyor_v2`; child CLI также идёт через v2.

Если свежих источников всё равно меньше production minimum, система должна остановиться, а не разрешить heavy reuse.

## Review-first conveyor

Команды:

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Resumability:

- non-empty expected MP4 в `runtime/ready_for_review` считается завершённым slot marker;
- состояние/attempt history: `runtime/conveyor/state.json`;
- существующие slots пропускаются;
- если AI `plan.json` уже есть, он не генерируется заново.

Safety:

- publication gate PASS обязателен;
- `auto_publish=false` frozen;
- `$10` OpenAI hard guard;
- никакого YouTube upload/OAuth;
- outputs only `runtime/ready_for_review`;
- batch stop-on-first-failure.

## MPT process management

Conveyor умеет использовать уже работающий MPT или автоматически поднять локальный MPT через первый найденный executable:

```text
MoneyPrinterTurbo/.venv/Scripts/python.exe
MoneyPrinterTurbo/venv/Scripts/python.exe
MoneyPrinterTurbo/.venv/bin/python
MoneyPrinterTurbo/venv/bin/python
uv (fallback only)
```

Это учитывает Windows пользователя, где `uv` не был в PATH. Если conveyor сам поднял MPT, он пишет `runtime/conveyor/mpt.log` и завершает только свой процесс после batch.

## Upload metadata / titles

После каждого нового render создаётся `.upload.json` с proposed YouTube title/description, language/pipeline/video path, required CC attribution, `review_required=true`, `auto_publish=false`, `publication_allowed_by_conveyor=false`.

Cat external titles: `Cats That Made My Day 😹 #NNN #shorts`; on-card remains `#NNN — Cats`. AI title берётся из конкретного fact plan + `#shorts`.

## CI

Latest code-head test job после automatic cat-source refresh:

```text
95 passed in 0.65s
Verify pilot lock: success
```

Windows-bootstrap для exact head на момент проверки ещё выполнялся; recheck live before claiming full workflow green.

## Immediate local continuation

На пользовательском ПК slot 5 уже существует, а failed slot 6 не создал final MP4. Поэтому после pull новый batch должен снова начать с slot 6.

Команды:

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Expected tests around **95 passed**.

Для slot 6 ожидается: old cat IDs будут исключены автоматически, sourcing попробует найти свежую шестёрку, затем final reuse audit должен PASS. Если production minimum свежих источников не набирается, исследовать `runtime/slots/06/animal_audio_sources.json`; не ослаблять rights/audio/aspect/clean/history gates.

После успешного batch можно перейти к Windows Task Scheduler. Uploader/OAuth остаётся отдельным более поздним решением.

## Git / release

Continue on `mvp/pilot-scaffold`, Draft PR #1. PR не merge без отдельного решения пользователя после дальнейшей local conveyor validation/review.
