# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт и не merge без отдельного решения пользователя после visual review.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

## Подтверждено локально

- Windows project path `D:\KiraS\VV_knopka`, `.venv` Python 3.11.
- Latest shown OpenAI ledger `$0.0340 / $10.00`; publication gate PASS.
- Slot 1 octopus = manual QUALITY PASS.
- Cat renderer local FFmpeg; Impact cards + real meow; no voiceover/BGM.
- Narrow themes removed from production; cats are generic `#NNN — Котики` / `#NNN — Cats` compilations.
- User manually accepted latest generic slot 2 as normal.
- Strict near-9:16 source gate is manually validated: all 6 selected Pexels clips were exactly 720×1280 / aspect 0.5625.

## Why current work is YouTube CC

Pexels footage is technically acceptable but can feel stock-like. User wants funnier/more natural cat footage. Current experiment = verified YouTube Creative Commons Attribution as production-capable UGC-like source, while keeping Pexels/Pixabay fallback.

Google Cloud/API key is explicitly not suitable for the user; do not require address/card/billing for this project.

## Old YouTube CC search failure

Old `vv-cat-youtube cc-search` kept only candidates whose yt-dlp `license` field explicitly said Creative Commons. User ran:

```text
vv-cat-youtube cc-search
Verified CC cat candidates: 0

vv-cat-youtube cc-search --days 6000 --limit 15 --scan-per-query 20
Verified CC cat candidates: 0
```

Conclusion: this is not a recency-window problem. `license` is optional metadata in yt-dlp, so absence of that field makes metadata-only CC discovery unusable.

## YouTube CC search v2 — IMPLEMENTED

New module:

```text
src/vv_knopka/youtube_cat_source_v2.py
```

`pyproject.toml` now maps:

```text
vv-cat-youtube = vv_knopka.youtube_cat_source_v2:main
```

The old `youtube_cat_source.py` remains as lower-level helper/legacy strict mode/test-only implementation.

### Search mechanism

Current yt-dlp includes `YoutubeSearchURLIE`, explicitly supporting YouTube search URLs with `sp=` filters. YouTube Help still says Creative Commons content can be found using the Creative Commons advanced search filter.

v2 search therefore uses the **platform CC filter itself**, not the optional direct `license` field as the sole discovery signal:

```text
YouTube Creative Commons search filter
-> filtered video IDs
-> full yt-dlp hydration per video
-> explicit Standard/non-CC license => reject
-> explicit CC license => accept with metadata+filter evidence
-> empty license field => accept only because it came from CC-filtered search
-> saved report
```

The filter provenance is stored in every candidate and the report.

Command:

```powershell
vv-cat-youtube cc-search
```

Default queries:

- funny cat shorts
- cats being cats
- funny kittens shorts
- cat fails shorts

Defaults: days=6000, scan-per-query=20, limit=15.

Report:

```text
runtime/trends/youtube-cat-cc-filtered.json
```

Diagnostics per query include `filtered_results`, `hydrated`, `accepted`, `search_url`. If result is again zero, inspect this report instead of blindly increasing scan depth.

### Safe report-based import

Preferred production import:

```powershell
vv-cat-youtube cc-import 2 --candidate N
```

It only accepts a candidate from a report whose source/filter provenance matches the expected YouTube CC-filter search. Before downloading it re-fetches metadata and checks video ID. If current metadata explicitly reports Standard/non-CC, import refuses even if the older report had filter evidence.

Then:

```text
yt-dlp download
-> real ffprobe near-9:16 gate
-> duration >= clip_seconds
-> audible source gate
-> production runtime/slots/02/sources.json
-> attribution.json
```

CC production clip stores creator/title/source URL/license, attribution text, `rights_verified=true`, `rights_status=creative_commons_attribution_required`, and verification method.

Legacy strict URL mode remains:

```powershell
vv-cat-youtube cc 2 --url "..."
```

but it requires direct yt-dlp CC license metadata, so `cc-import` from v2 report is preferred.

## Ordinary YouTube private test-only path

User also wants to compare normal funny YouTube clips privately. Standard/unverified media does not become production-safe merely because test is local. No automatic standard-license download is added.

Already-local exact files can be isolated:

```powershell
vv-cat-youtube test-add 2 --url "https://youtube..." --file "D:\path\cat.mp4" --confirm-match
vv-cat-youtube test-render 2
```

They live only under `runtime/test_only/slot-02/`, never production `sources.json`/`ready_for_review`. Required locks: `do_not_publish=true`, `publication_allowed=false`, `commercial_use_allowed=false`, `rights_verified=false`. Test cards say `ТЕСТ — Котики`.

## Tests / current CI

Previous YouTube source layer had 54 tests. v2 added 4 regression tests covering:

- CC `sp=` filter in generated search URL;
- empty direct `license` accepted only with CC-filter provenance;
- explicit Standard license rejected;
- CC report provenance required and import recheck fails on current explicit non-CC.

GitHub CI `test` job for v2 code head `2e56412a...`: **58 passed in 0.49s**, `Verify pilot lock` success. Windows bootstrap was still running at last check; do not claim entire workflow complete unless rechecked.

## Immediate next local step

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-youtube.exe cc-search
```

Expected tests: ~58 passed.

If candidates appear, inspect top list and then:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate N
.\.venv\Scripts\vv.exe render-animal 2
```

If search still gives 0, ask user for:

```powershell
Get-Content .\runtime\trends\youtube-cat-cc-filtered.json -Raw
```

The diagnostics will show whether YouTube returned zero filtered IDs or whether hydration/rejection removed them.

Do not merge Draft PR #1 until explicit user approval after visual pilot review.
