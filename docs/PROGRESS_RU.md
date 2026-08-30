# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-30**. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

## Подтверждено на ПК пользователя

- Python `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний показанный OpenAI ledger: **$0.0509 / $10.00**.
- Последний локальный pytest: **62 passed in 0.48s**.
- Slot 1 RU AI Short = manual QUALITY PASS.
- Cat renderer = local FFmpeg; real meow + Impact; no voiceover/BGM.
- Generic slot 2 `#001 — Котики` пользователь оценил как нормальный.
- Vertical gate локально подтверждён: 6/6 selected Pexels sources = **720x1280 / aspect 0.5625**.

## YouTube Creative Commons — OFFICIAL API WORKS LOCALLY

Пользователь успешно включил YouTube Data API v3, создал API key и хранит его локально в `.env` как `YOUTUBE_API_KEY`. Ключ никогда не просить вставлять в чат и не коммитить.

Локальный запуск:

```text
vv-cat-youtube cc-search
YouTube CC search: official YouTube Data API (videoLicense=creativeCommon)
Public metadata only; no OAuth, no channel login, no media download
Creative Commons cat candidates: 15
```

Report:

```text
runtime/trends/youtube-cat-cc-official.json
```

Top candidates from the successful run:

```text
01  9,490,575  Never about drinking water! 😼
02 27,067,392  Bichinhos que nos entendem -gatos e pássaros
03 58,256,969  Bichinhos que nos entendem - gatos e caixas
04 34,953,145  Bichinhos que nos entendem - mamãe gata
05  9,947,315  Wind swept rescue mission! 🤯
06 10,979,204  Bichinhos que nos entendem -gatos e água
07 33,876,469  Bichinhos que nos entendem -gatos e suas patinhas
08 13,067,369  What was the reason for this? 👀
09  9,894,205  Bichinhos que nos entendem-gatos e aspiradores
10 27,289,448  Bichinhos que nos entendem -dando tilt nos gatos
11 36,424,618  Bichinhos que nos entendem - gatos laranjas
12  7,944,733  Ranking Best Big Cats Moments
13 20,034,233  Bichinhos que nos entendem - gatos com fobia social
14 10,244,613  What was this cat trying to do 🤔🐾
15 20,670,771  Bichinhos que nos entendem - gatitos e brinquedos
```

All 15 were returned through official `videoLicense=creativeCommon` discovery and `videos.status.license=creativeCommon` verification.

## Current recommended quality test

First test should prefer candidates that appear from their titles to be single-scene Shorts rather than already-edited compilations:

- candidate **1** — `Never about drinking water! 😼`
- candidate **8** — `What was the reason for this? 👀`
- candidate **14** — `What was this cat trying to do 🤔🐾`

The repeated `Bichinhos que nos entendem` series may still be useful later, but first-pass concern is that these may already be compilations; avoid a compilation-inside-compilation until manually inspected. Candidate 12 is big cats and is not suitable for the domestic-cat compilation target.

Run imports one by one:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 1
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 8
.\.venv\Scripts\vv-cat-youtube.exe cc-import 2 --candidate 14
```

Each import rechecks current API `status.license == creativeCommon`, downloads only after that, then requires near-9:16, minimum duration and audible source audio. Failures on orientation/audio are expected and should be reported rather than bypassed.

If at least 2–3 are accepted, run:

```powershell
.\.venv\Scripts\vv.exe render-animal 2
```

The YouTube CC imports should be prioritized in production `sources.json`; Pexels/Pixabay fill remaining target slots to six.

## Test-only ordinary YouTube remains isolated

Standard/unverified YouTube clips are not production-safe. Already-local exact files may only be used under `runtime/test_only/slot-02/` with `do_not_publish=true`, `publication_allowed=false`, `commercial_use_allowed=false`, `rights_verified=false`.

Draft PR #1 remains review-only; do not merge without explicit user decision after visual review.
