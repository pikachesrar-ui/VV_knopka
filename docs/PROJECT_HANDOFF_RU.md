# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя после visual review.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

## Локально подтверждено

- Windows path `D:\KiraS\VV_knopka`, `.venv` Python 3.11.
- Latest shown OpenAI ledger **$0.0618 / $10.00**; publication gate PASS.
- Latest shown local pytest **81 passed in 0.55s**.
- Slot 1 octopus = manual QUALITY PASS.
- Cat renderer local FFmpeg; Impact + real meow; no voiceover/BGM.
- Production cats = broad generic `#NNN — Котики` / `#NNN — Cats`; narrow themes abandoned.
- Generic vertical slot 2 baseline manually accepted as normal.
- Strict stock baseline: six Pexels clips exactly 720×1280.

## YouTube Data API / CC

User enabled YouTube Data API v3 and stores `YOUTUBE_API_KEY` locally in ignored `.env`. Never ask for or commit the key.

Official API search/verification works: `search.list(videoLicense=creativeCommon)` plus `videos.status.license=creativeCommon` recheck before import.

## Proven clean-gate behavior

Three Pawcsu CC imports were technically valid (CC/2160×3840/audio) but visibly packaged. `cc-clean 2` rejected all three at confidence 0.99–1.00 for `Pawcsu/@Pawcsu`, avatar/branding and large added captions. This is desired. Never crop/blur branding to make a source pass.

`nWieRK7Fw-g` passed thumbnail screening but was later rejected for livestream/social chat UI, creator branding and large Korean caption overlays. This proved thumbnail-only screening is insufficient.

## Search / preflight evolution

v5 search added official CC + one candidate/channel + Luna thumbnail prescreen. v5.1 then added:

```text
official CC recheck
-> low-res temporal preview
-> 4-frame clean review
-> only on preflight PASS download full-quality media
-> 9:16/duration/audio
-> final full-quality 4-frame clean review
```

plus reject memory.

Latest relevant search before v6 recheck:

```text
Known full/preview-gate rejects skipped: 2
1 selected / 30 reviewed / 43 raw CC after reject memory
01 hxXfevBB9Zs | Kumpulan Video Hewan Lucu | clean-thumb=0.95
```

## clean-footage v2 + CLI v6

Entry point:

```text
vv-cat-youtube = vv_knopka.youtube_cat_source_v6:main
```

New contact-sheet-aware clean review explicitly distinguishes:

- outer 2x2 = OUR analysis artifact, never source evidence by itself;
- `source_frame_collage=true` only if an individual source frame contains real split-screen/collage/ranking packaging;
- `multi_clip_sequence=true` only with strong temporal evidence of unrelated source clips stitched together (different cats/locations/camera sources/events);
- ordinary movement/reframing/time progression is not enough.

Real branding, social UI, large captions and actual repost packaging remain fail-closed. Prompt/review version was bumped so stale v1 cached decisions are not silently reused.

Reject memory is version-aware: old obvious branding/UI/caption rejects remain durable, while stale v1 collage-only rejects were eligible for one v2 recheck.

## hxXfevBB9Zs — FINAL STATUS: PROVEN REJECT

Old v1 full gate had rejected this clip with wording about a `2x2 compilation/collage`, which could have confused our generated contact sheet with the source. v2 was created specifically to remove that ambiguity.

User pulled v6 and locally confirmed:

```text
81 passed in 0.55s
OpenAI spent: $0.0618 / $10.00
auto_publish: False
publication gate: PASS
```

Then re-ran current candidate 1. The corrected gate failed **at low-res temporal preflight before any new full-quality re-download**:

```text
YouTube CC candidate failed low-resolution temporal clean preflight before full download:
The cat is visible and no social branding or captions appear, but the sampled frames show clearly unrelated scenes and multiple animals/events, strongly indicating a stitched compilation.
```

This is now considered a real reject, not a contact-sheet false positive. The corrected gate did not object to the outer 2x2 layout; it found temporal evidence of unrelated scenes/multiple animals/events, i.e. a stitched compilation.

## Current YouTube production-source status

So far **0 YouTube CC clips are accepted for production**:

- 3 Pawcsu clips rejected for branding/captions.
- `nWieRK7Fw-g` rejected for livestream/chat/UI/caption packaging.
- `hxXfevBB9Zs` rejected by contact-sheet-aware v2 as a real stitched compilation.

Pexels/Pixabay remain the accepted licensed fallback. Do not loosen clean gates merely to increase yield.

## Tests / CI

Latest code-head CI before docs update:

```text
81 passed in 0.52s
Verify pilot lock: success
```

User independently confirmed local **81 passed in 0.55s**.

## Immediate next step

Rerun official search so reject memory removes the newly confirmed bad candidate:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-search
```

If zero clean candidates remain, do not weaken the gates. Expand official API queries toward more likely raw/self-shot footage such as:

```text
my cat
cat home video
kitten playing home
cat reaction home video
funny cat home video
```

while preserving exact CC verification, one-per-channel diversity, low-res temporal preflight and the final full-quality clean gate.

Send the complete next `cc-search` output before importing another candidate.

## Ordinary YouTube test-only

Standard/unverified YouTube is not production-safe merely because testing is local. Already-local exact files only through `test-add` / `test-render` under `runtime/test_only`, with publication locks.

Do not merge Draft PR #1 until explicit user approval after visual pilot review.
