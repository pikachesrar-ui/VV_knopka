# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя после visual review.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

## Локально подтверждено

- Windows path `D:\KiraS\VV_knopka`, `.venv` Python 3.11.
- Latest shown OpenAI ledger **$0.0509 / $10.00**; publication gate PASS.
- Latest local pytest: **62 passed in 0.48s**.
- Slot 1 octopus = manual QUALITY PASS.
- Cat renderer local FFmpeg; Impact + real meow; no voiceover/BGM.
- Production cats = broad generic `#NNN — Котики` / `#NNN — Cats`, narrow trend themes abandoned.
- Latest generic slot 2 manually accepted as normal.
- Strict near-9:16 gate manually validated: all six selected Pexels clips were exactly 720×1280 / aspect 0.5625.

## Current milestone: better cat footage through YouTube CC

Pexels is technically acceptable but can feel stock-like. Goal: find funnier/more natural cat footage with verified YouTube Creative Commons Attribution and keep Pexels/Pixabay fallback.

Old no-key yt-dlp license discovery was exhausted: two scans, including 6000-day window, returned 0 verified CC because `license` is optional metadata.

## Google Cloud / YouTube Data API — WORKING LOCALLY

User successfully entered Google Cloud Console, selected project `VV Knopka`, enabled YouTube Data API v3, created an API key, and stored it locally in `.env` as `YOUTUBE_API_KEY`.

Never ask user to paste the key. Never commit `.env` or secrets. Public metadata search does not require OAuth/channel access.

## Official `vv-cat-youtube` v3

`pyproject.toml` maps:

```text
vv-cat-youtube = vv_knopka.youtube_cat_source_v3:main
```

### Successful official CC discovery

User ran:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-search
```

and got:

```text
YouTube CC search: official YouTube Data API (videoLicense=creativeCommon)
Public metadata only; no OAuth, no channel login, no media download
Creative Commons cat candidates: 15
D:\KiraS\VV_knopka\runtime\trends\youtube-cat-cc-official.json
```

Top 15 returned by the official API:

```text
[01]  9,490,575  Never about drinking water! 😼
[02] 27,067,392  Bichinhos que nos entendem -gatos e pássaros
[03] 58,256,969  Bichinhos que nos entendem - gatos e caixas
[04] 34,953,145  Bichinhos que nos entendem - mamãe gata
[05]  9,947,315  Wind swept rescue mission! 🤯
[06] 10,979,204  Bichinhos que nos entendem -gatos e água
[07] 33,876,469  Bichinhos que nos entendem -gatos e suas patinhas
[08] 13,067,369  What was the reason for this? 👀
[09]  9,894,205  Bichinhos que nos entendem-gatos e aspiradores
[10] 27,289,448  Bichinhos que nos entendem -dando tilt nos gatos
[11] 36,424,618  Bichinhos que nos entendem - gatos laranjas
[12]  7,944,733  Ranking Best Big Cats Moments
[13] 20,034,233  Bichinhos que nos entendem - gatos com fobia social
[14] 10,244,613  What was this cat trying to do 🤔🐾
[15] 20,670,771  Bichinhos que nos entendem - gatitos e brinquedos
```

This proves the official search path works and returns real CC inventory. The report uses YouTube API `videoLicense=creativeCommon` and candidates are rechecked through `videos.status.license=creativeCommon`.

### Recommended first import test

Prefer single-scene-looking Shorts first, based on titles:

- candidate 1 — `Never about drinking water! 😼`
- candidate 8 — `What was the reason for this? 👀`
- candidate 14 — `What was this cat trying to do 🤔🐾`

Avoid candidate 12 for current domestic-cat target. The repeated Portuguese `Bichinhos que nos entendem` titles may represent already-edited compilations; they can be inspected later, but first avoid a compilation-inside-compilation artifact.

Commands:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 1
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 8
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 14
```

Each import:

1. validates official report provenance;
2. rechecks current API `status.license == creativeCommon`;
3. downloads only after that;
4. validates real ffprobe near-9:16 orientation;
5. requires enough duration and audible source audio;
6. prepends accepted source to production `sources.json`;
7. writes attribution metadata.

Orientation/audio rejection is expected and should not be bypassed. If 2–3 YouTube candidates pass, run:

```powershell
.\.venv\Scripts\vv.exe render-animal 2
```

Then compare against the already-accepted all-Pexels generic vertical baseline. Pexels/Pixabay should only fill remaining slots up to target six.

## Ordinary YouTube private comparison

Standard/unverified YouTube does not become production permission just because use is local. No automatic standard-license download in production flow.

Already-local exact files can be isolated through `test-add` / `test-render`; storage only under `runtime/test_only/slot-02/`, never production sources or `ready_for_review`. Required locks: `do_not_publish=true`, `publication_allowed=false`, `commercial_use_allowed=false`, `rights_verified=false`.

## Tests / CI

Official v3 code added four tests for API discovery/dedupe, official rights evidence, report provenance, and API-key recheck requirement. Prior GitHub CI test job on code head showed **62 passed** and `Verify pilot lock` success. Recheck live CI before making newer final-head CI claims.

Do not merge Draft PR #1 until explicit user approval after visual pilot review.
