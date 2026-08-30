# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл хранит продуктовые решения и точку продолжения.

Последнее содержательное обновление: **2026-08-30**.

## 1. Frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.
Рабочая ветка: `mvp/pilot-scaffold`.
Draft PR #1 открыт; **не merge без отдельного решения пользователя после визуального review**.

Pilot: 15 Shorts; 8 × `ai_short`; 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI hard budget `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

## 2. Локально подтверждено

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- keys local `.env`, не коммитить;
- MPT только для `ai_short`; cats = local FFmpeg;
- last explicitly shown local tests before current YouTube-source code: **47 passed**;
- publication gate **PASS**;
- latest OpenAI ledger **$0.0340 / $10.00**;
- slot 1 octopus = manual QUALITY PASS;
- real user meow works;
- Impact title cards approved.

## 3. Cat presentation — accepted

- broad generic cat compilation; no narrow promised theme;
- RU title `#NNN — Котики`, EN `#NNN — Cats`;
- no voiceover / no BGM;
- real meow on black cards;
- intro ~0.9s, transitions ~0.75s, end ~1.0s;
- localized thanks end card;
- source audio retained/normalized;
- Windows font `C:\Windows\Fonts\impact.ttf`, sizes 84/78/82;
- minimum 5 unique usable production clips, target 6;
- long-run `en,en,en,en,ru` cadence;
- never use `Daily Dose of Cats` or close imitation.

## 4. Vertical source gate — locally validated

Earlier themed render exposed bad landscape 1920×1080 / 2560×1440 clips. We added a strict near-9:16 gate (`source_aspect_tolerance=0.08`), provider portrait filtering, and real ffprobe validation for cached/downloaded/imported media.

The user's next generic render succeeded. They inspected `animal_audio_sources.json`; all six selected sources were **exactly 720×1280 (aspect 0.5625)**:

- Pexels 10358235
- Pexels 19306625
- Pexels 10231519
- Pexels 5335581
- Pexels 15769301
- Pexels 17536779

User verdict: **«да, норм»**.

Therefore orientation/base presentation is no longer the current blocker.

## 5. Why current focus moved to YouTube CC

Pexels pipeline is now technically acceptable but can still feel stock-like. User wants funnier, more natural internet-cat footage.

Next experiment: **verified YouTube Creative Commons Attribution** as production-capable UGC-like source, with Pexels/Pixabay as fallback.

Official policy context checked 2026-08-30:

- YouTube offers Standard and Creative Commons Attribution licenses.
- CC BY videos may be reused subject to license terms and attribution.
- Suggested attribution info includes title, author, source URL and license.
- Standard-license/public availability alone does not grant reuse rights.
- YouTube Terms restrict downloading content outside authorized mechanisms; we therefore do not add auto-download for standard/unverified videos.

## 6. New `vv-cat-youtube` CLI

Entry point:

```powershell
vv-cat-youtube
```

Module:

```text
src/vv_knopka/youtube_cat_source.py
```

### A. `cc-search`

```powershell
vv-cat-youtube cc-search
```

Purpose: find **metadata-verified CC cat candidates** without Google Cloud/API key/login/media download.

Defaults:

- wide lookback: 3650 days;
- queries:
  - `funny cat shorts`
  - `cats being cats`
  - `funny kittens shorts`
- scan 15 results per query;
- output top 10 verified-CC candidates by views.

Can widen:

```powershell
vv-cat-youtube cc-search --days 6000 --limit 15 --scan-per-query 20
```

or custom repeated queries:

```powershell
vv-cat-youtube cc-search --query "funny cat" --query "cat fails" --query "cute kitten shorts"
```

This uses existing no-key `discover_ytdlp_cats()` and discards everything whose metadata does not identify Creative Commons.

### B. `cc`

```powershell
vv-cat-youtube cc 2 --url "https://www.youtube.com/watch?v=..."
```

Flow:

```text
fetch full metadata
-> require Creative Commons
-> yt-dlp download
-> real ffprobe dimensions
-> near-9:16 gate
-> >= clip_seconds
-> audible-source gate
-> production sources.json
-> attribution.json
```

Imported CC clip metadata includes:

- source title / creator / URL;
- exact detected license;
- `rights_status=creative_commons_attribution_required`;
- `rights_verified=true`;
- `commercial_use_allowed=true`;
- `attribution_required=true` + attribution text;
- SHA-256;
- width/height/aspect;
- audio mean.

If metadata does not prove CC, no production download/import occurs. If media is landscape, too short or effectively silent, it is rejected after download and not accepted into the production source pool.

Normal `vv render-animal 2` then sees imported CC source first, while Pexels/Pixabay fill remaining target slots.

## 7. Ordinary YouTube private comparison — hard isolated

User also wants to compare ordinary funnier YouTube cats for private testing. Important boundary: local testing does not convert a standard/unverified upload into production permission, and automatic standard-license YouTube downloading is not added.

New test-only path accepts an **already-local** exact source file:

```powershell
vv-cat-youtube test-add 2 --url "https://www.youtube.com/watch?v=..." --file "D:\path\cat.mp4" --confirm-match
```

Validation still requires:

- near-9:16;
- enough duration;
- audible audio.

But rights fields intentionally fail closed:

- `rights_status=test_only_unverified`;
- `rights_verified=false`;
- `commercial_use_allowed=false`;
- `do_not_publish=true`;
- `publication_allowed=false`.

Storage ONLY:

```text
runtime/test_only/slot-02/
```

No write to:

```text
runtime/slots/02/sources.json
runtime/ready_for_review/
```

A `DO_NOT_PUBLISH.txt` marker is written as well.

After at least 3 test clips:

```powershell
vv-cat-youtube test-render 2
```

This uses the same highlight/editor/card stack but title is `ТЕСТ — Котики`; output:

```text
runtime/test_only/slot-02/render-test-only.mp4
```

The renderer checks both top-level and per-clip publication locks before running. This test render may use the existing Luna highlight step and therefore can consume a small amount of the same `$10` project budget.

## 8. Trend/community experiment history

Pexels-only footage looked stock-like, so trend discovery was explored.

- YouTube no-key `vv-cat-trends`: technically works, first useful run gave 5 recent candidates and 0 CC; weak as primary recent discovery.
- Reddit `vv-cat-community`: 30 candidates, useful as idea signal, but Reddit media remains permission-required/reference-only.
- `vv-cat-theme`: selected `important_jobs` correctly from Reddit, but user rejected narrow themes because stock could not satisfy every promised scene.
- Current production `render-animal` ignores theme files and stays generic.

## 9. Rights / monetization constraints

- Public Reddit post is not permission to reuse media.
- YouTube Standard/unverified is not production permission.
- Verified YouTube CC BY is a candidate with attribution, not a guarantee that the uploader actually owned every underlying element; human review remains useful.
- Creative Commons/permission alone does not solve YouTube reused-content monetization risk; editorial transformation remains important.
- Pexels/Pixabay production clips keep normal license/provenance gates.
- Test-only unverified media is never a production candidate.

## 10. Tests added for YouTube source layer

`tests/test_youtube_cat_source.py` covers:

- standard license rejected by production CC gate;
- CC license accepted by CC gate;
- CC search keeps only verified CC and dedupes repeated query hits;
- test-only import stays isolated and carries publication locks;
- test-only renderer refuses a missing publication lock.

GitHub `test` job passed on the first YouTube-source code head. After adding `cc-search`, a newer CI run must be checked before claiming the entire final head is green.

## 11. Immediate next local checkpoint

Once latest CI/head is confirmed, user should run:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-youtube.exe cc-search
```

Send full `cc-search` output.

If a promising CC candidate is found:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc 2 --url "CANDIDATE_URL"
.\.venv\Scripts\vv.exe render-animal 2
```

Then compare new render against the already-accepted Pexels generic vertical baseline.

Do not merge Draft PR #1 until explicit pilot quality approval.
