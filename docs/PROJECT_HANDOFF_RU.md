# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл хранит продуктовые решения и точку продолжения.

Последнее содержательное обновление: **2026-08-30**.

## 1. Frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.
Рабочая ветка: `mvp/pilot-scaffold`.
Draft PR #1 открыт; **не merge без отдельного решения пользователя после визуального review**.

Pilot: 15 Shorts; 8 × `ai_short`; 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI hard budget `$10`; `auto_publish=false`; human review; outputs only `runtime/ready_for_review`.

## 2. Локально подтверждено

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- keys local `.env`, не коммитить;
- MPT только для `ai_short`; cats = local FFmpeg;
- latest user test before current code changes: **47 passed**;
- publication gate **PASS**;
- latest OpenAI ledger **$0.0340 / $10.00**;
- slot 1 octopus = manual QUALITY PASS;
- real user meow works;
- Impact title cards approved.

## 3. Accepted cat presentation

- no voiceover;
- no BGM;
- real meow on black cards;
- intro ~0.9s, transitions ~0.75s, end ~1.0s;
- numbered intro/transition title;
- localized thanks end card;
- source audio retained/normalized;
- Windows font `C:\Windows\Fonts\impact.ttf`, sizes 84/78/82;
- minimum 5 unique usable clips, target 6;
- long-run `en,en,en,en,ru` cadence;
- never use `Daily Dose of Cats` or close imitation.

## 4. Trend/community experiment history

Pexels-only footage looked stock-like, so trend discovery was explored.

### YouTube no-key

`vv-cat-trends` via yt-dlp works without Google Cloud/API key/login. Google Cloud was explicitly rejected by user because setup requested address/card.

Actual useful run: 5 recent candidates, **0 CC confirmed**; only one had meaningful views. Verdict: technically works but weak as primary source.

### Reddit public RSS

`vv-cat-community` worked well as a trend/reference signal: user got 30 candidates with 1 feed warning. Reddit remains reference-only (`author_permission_required`), never automatic reusable media.

### Trend → Theme

`vv-cat-theme` / `cat_theme.py` was implemented and successfully selected `important_jobs` for slot 2 from real Reddit evidence.

User then rendered:

```text
Trend theme: important_jobs
Cat episode: #001 — Важные кошачьи дела
Audible licensed animal sources: 6
```

The render completed successfully, but manual verdict was only **«более менее»**.

## 5. Why narrow themes were removed from production

User identified two concrete issues after watching the themed render:

1. **Landscape stock** sometimes appeared in the montage and looked bad in 9:16 Shorts.
2. Even with theme-driven search, some clips were simply “a cat doing something else” and did not match the promised episode theme.

Therefore current product decision is simpler:

> **Animal episodes are broad cat compilations, not narrow themed videos.**

Research tooling (`vv-cat-community`, `vv-cat-theme`, YouTube trend discovery) may remain in repo, but current `render-animal` does **not** use `trend-theme.json`.

## 6. Generic cat compilation mode — IMPLEMENTED

New module:

```text
src/vv_knopka/cat_compilation.py
```

`build_generic_cat_plan(language)` returns a free/deterministic plan:

- RU title `Котики`;
- EN title `Cats`;
- `visual_anchor = cat`;
- broad search terms:
  - cat funny reaction
  - cat playing
  - cat jumping
  - cat running
  - cat curious
  - cat interacting with human
  - cat meowing
  - cat purring

`src/vv_knopka/cli.py` production behavior now:

- `render-animal` always uses this generic plan;
- no cat writer API call required;
- stale `plan.json` / `trend-theme.json` do not control the production cat render;
- writes `runtime/slots/XX/effective-plan.json` for audit;
- expected slot 2 title = `#001 — Котики`.

This intentionally avoids promising a storyline that every licensed stock clip must satisfy.

## 7. Near-9:16 cat source gate — IMPLEMENTED

The previous themed render log proved accepted sources included both correct portrait `720x1280` and bad landscape files such as `1920x1080` and `2560x1440`.

New rule: **cat source footage must already be vertical and close to 9:16 before montage acceptance**.

Config:

```toml
[animal]
source_aspect_tolerance = 0.08
```

Definition:

- target width/height = `9/16` (`0.5625`);
- accept only portrait footage whose width/height is within `0.08` of target;
- reject all landscape, square and visibly-wide portrait formats.

Implementation in `animal_audio_sources.py`:

- `video_dimensions()` probes actual local/downloaded media with ffprobe;
- `is_short_portrait()` applies the near-9:16 rule;
- Pexels audio search now sends `orientation=portrait`;
- Pexels/Pixabay candidate file metadata is filtered **before Luna review/download**;
- old cached/local/imported media is re-probed with ffprobe before reuse;
- downloaded media is checked again before final acceptance;
- accepted source manifest stores width/height/aspect;
- audit v2 stores target aspect/tolerance and rejected landscape rows;
- if fewer than 5 licensed + audible + vertical sources remain, fail closed.

This means old 1920×1080/2560×1440 sources from the previous slot 2 cache should be rejected automatically on the next render.

## 8. Cat audio/source gates

Still required:

- actual audio stream;
- effective mean signal above configured threshold (`-55 dB` by default);
- visual cat relevance via Luna;
- source provenance/license/commercial-use metadata;
- near-9:16 source dimensions;
- minimum 5 unique usable clips.

Do not silently relax these if a run fails. Inspect `runtime/slots/02/animal_audio_sources.json` first.

## 9. Controlled UGC / rights

- Reddit/public social post != permission.
- YouTube unverified candidate != permission; CC must be verified.
- `vv-cat-import` remains controlled/local and rights-gated.
- Creative Commons/permission alone does not solve YouTube reused-content monetization risk.
- Human review remains mandatory.
- Do not add raw social repost scraping as default workflow.

## 10. Tests added in current change

- vertical aspect helper accepts 9:16 and rejects landscape/4:5;
- cached audible landscape clip is rejected;
- cached portrait clip can still be reused;
- generic RU/EN cat plan stays broad and cat-anchored.

CI test job for the code head passed after these changes; Windows bootstrap may complete separately. Last user-confirmed local count is still 47 until the user pulls/runs the new tests.

## 11. Next local checkpoint

User should run:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

Do **not** run `vv-cat-theme 2` for production; it is now optional research tooling.

Expected start:

```text
Cat compilation mode: generic | title=Котики | effective plan: ...
Audible vertical licensed cat sources: ...
```

After render, review:

1. all six selected sources visually portrait/Short-native;
2. no obvious 16:9 blur-fill footage;
3. title is generic `#001 — Котики`;
4. all clips are simply good cat moments, so there is no theme-mismatch problem;
5. source audio and real meow remain correct.

If source gate finds <5 clips, inspect audit rather than weakening aspect/audio gates automatically.

Do not merge Draft PR #1 until explicit pilot quality approval.
