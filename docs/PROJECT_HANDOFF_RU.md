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

## Manual quality / local state

Пользователь визуально принял proof pair обеих веток:

- slot 1 RU AI facts = QUALITY PASS;
- slot 2 RU cats = QUALITY PASS;
- slot 3 EN AI facts = QUALITY PASS;
- slot 4 EN cats = QUALITY PASS.

Slot 5 EN AI был первым полным успешным conveyor render через `vv pilot-next` и создал MP4 + `.upload.json`.

Последний показанный локальный pytest: **95 passed in 0.63s**. Последний явно показанный OpenAI ledger: **$0.0887 / $10.00** до последующих cat-source retries; более новое значение всегда читать через `vv status`.

## Cat / YouTube sourcing

Первый принятый YouTube CC source: `I_pdwiLlvuc` / Kawaiipets / YouTube Creative Commons Attribution / 2160×3840 / audio -14.8 dB / clean gate PASS 0.99.

Не вводить обязательную YouTube quota. Автоматический production sourcing должен предпочитать лицензированный downloadable stock (Pexels/Pixabay) и не ослаблять rights / clean-footage / near-9:16 / audible-audio gates.

## Cross-episode history

`source_history.py` сравнивает `provider + provider_id` нового cat episode с реально отрендеренными предыдущими cat episodes. Финальный gate разрешает максимум один incidental repeat и fail closed при 2+ reused IDs.

Первый batch остановился на slot 6 из-за 5 reused Pexels IDs. После history-aware pre-filter старые IDs начали исключаться до render.

## Реальный slot 6 fresh-pool bottleneck

После обновления пользователь подтвердил **95 passed in 0.63s** и повторил `vv pilot-batch --count 3`.

Slot 6 уже не прошёл с повторной пятёркой, но fresh sourcing нашёл только:

```text
Vertical audible-source gate found only 2/5 usable cat clips
```

Это корректный safe failure, а не повод ослаблять gate. Анализ кода показал, что stock collectors были слишком top-heavy: в основном первая страница популярных результатов. После исключения source history существующий `max_candidates` мог исчерпываться/беднеть раньше, чем поиск доходил до свежего хвоста каталога.

## Deep history-aware stock sourcing

`src/vv_knopka/animal_audio_sources_v4.py` добавляет:

- prior rendered source IDs исключаются **во время collection**, до заполнения candidate cap;
- Pexels/Pixabay pagination: до 4 страниц на query;
- extra generic cat query diversity (`cat`, `kitten`, `cute cat`, `funny cat`, `cat playing`, `kitten playing`, `cat meowing`, `cat purring`, `house cat`, `pet cat`);
- существующие max candidate caps, vision relevance, duration, near-9:16, audio and license checks сохраняются;
- audit field `deep_stock_search` документирует режим.

Цель: не увеличить шум, а заполнить тот же review pool свежими IDs, а не уже использованными top results.

## Resume after failed minimum-count attempt

`src/vv_knopka/animal_audio_sources_v5.py` поверх v4 делает retry resumable.

В failed slot 6 audit уже находились два fresh usable stock clips. Base pipeline не пишет финальный source manifest при `<5`, поэтому без recovery они могли снова проходить review.

Теперь retry:

1. читает предыдущий `animal_audio_sources.json -> selected_sources`;
2. восстанавливает только существующие локально Pexels/Pixabay files;
3. отбрасывает IDs, которые уже использовались в ранее отрендеренных cat episodes;
4. не восстанавливает YouTube через этот shortcut;
5. затем запускает deep v4 sourcing только за недостающими clips.

Текущий `vv` console entrypoint всё ещё `cli_v2`, но `cli_v2` теперь подключает `animal_audio_sources_v5`. Conveyor child processes остаются routed через `pilot_conveyor_v2`, поэтому та же политика действует внутри `pilot-next` / `pilot-batch`.

## Review-first conveyor

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

- strict manifest order;
- non-empty expected MP4 = resumable completion marker;
- state: `runtime/conveyor/state.json`;
- AI: plan-on-demand + managed/check MPT + render;
- cats: fresh licensed sourcing + audio/aspect/vision/history gates + local FFmpeg;
- stop on first failure;
- outputs only `runtime/ready_for_review`;
- `$10` OpenAI hard guard;
- `auto_publish=false`; no YouTube uploader/OAuth yet.

MPT process manager prefers local `.venv/venv` Python and only falls back to `uv`; if MPT already runs externally, conveyor leaves it alone.

## Upload metadata / titles

Successful renders produce `.upload.json` with proposed YouTube title/description, language/pipeline/video path, required attribution, `review_required=true`, `auto_publish=false`, `publication_allowed_by_conveyor=false`.

Cat external title family: `Cats That Made My Day 😹 #NNN #shorts`; on-card remains `#NNN — Cats`. AI titles come from each specific fact plan.

## CI

Latest code-head test job after deep pagination + retry recovery:

```text
99 passed in 0.65s
Verify pilot lock: success
```

Windows-bootstrap for that exact head was still running at the exact check; recheck live before claiming complete workflow green.

## Immediate local continuation

Slot 5 is complete; slot 6 has no final MP4. Do not manually delete its failed audit or the two fresh downloaded files.

```powershell
cd D:\KiraS\VV_knopka
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe pilot-batch --count 3
```

Expected tests around **99 passed**. The next slot 6 attempt should recover the 2 fresh clips from the failed audit, exclude all prior rendered source IDs during collection, paginate deeper, and search for the remaining fresh clips.

If it still cannot reach 5, inspect `runtime/slots/06/animal_audio_sources.json`. Do not lower rights/audio/aspect/history requirements. Next escalation should expand provider/search depth or add another explicitly approved downloadable licensed source, not mass reuse.

## Git / release

Continue on `mvp/pilot-scaffold`, Draft PR #1. Do not merge until separate user decision after more local conveyor validation/review.
