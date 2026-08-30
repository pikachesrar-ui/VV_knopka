# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-30**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний явно показанный локальный test run перед текущим YouTube-source кодом: **47 passed**.
- Последний показанный OpenAI ledger: **$0.0340 / $10.00**.
- Slot 1 RU AI Short — manual QUALITY PASS.
- Cat pipeline = local FFmpeg; MPT нужен только `ai_short`.
- Real user meow работает.
- Impact title-card style принят.

## Slot 2 generic + vertical — MANUAL PASS

После отказа от narrow theme пользователь собрал generic `#001 — Котики` render и сказал **«да, норм»**.

Проверка `animal_audio_sources.json` показала 6/6 selected sources:

```text
pexels 10358235  720x1280  aspect 0.5625
pexels 19306625  720x1280  aspect 0.5625
pexels 10231519  720x1280  aspect 0.5625
pexels 5335581   720x1280  aspect 0.5625
pexels 15769301  720x1280  aspect 0.5625
pexels 17536779  720x1280  aspect 0.5625
```

Вывод: **near-9:16 gate работает локально как задумано**; landscape 16:9 проблема закрыта для текущего stock pipeline.

Accepted presentation остаётся:

- generic cat compilation, без обязательной темы;
- Impact;
- real meow;
- no voiceover / no BGM;
- source audio retained/normalized;
- source footage near 9:16;
- target 6, minimum 5 unique production sources.

## Новый текущий эксперимент — YouTube Creative Commons

Пользователь хочет проверить, будут ли YouTube CC клипы заметно смешнее/живее Pexels.

Добавлен CLI:

```powershell
vv-cat-youtube
```

### 1. CC search

```powershell
vv-cat-youtube cc-search
```

- no Google Cloud;
- no API key;
- no account login;
- metadata-only search;
- более широкий historical window, потому что recent-only поиск раньше дал 0 CC;
- defaults: `funny cat shorts`, `cats being cats`, `funny kittens shorts`;
- показывает только candidates, где yt-dlp metadata реально сообщает Creative Commons.

Можно расширить:

```powershell
vv-cat-youtube cc-search --days 6000 --limit 15 --scan-per-query 20
```

### 2. Verified CC URL -> production source

```powershell
vv-cat-youtube cc 2 --url "https://www.youtube.com/watch?v=..."
```

Flow:

```text
metadata -> require CC -> yt-dlp download -> ffprobe near-9:16 -> audible audio -> sources.json -> attribution.json
```

CC clip gets:

- `rights_verified=true`;
- `rights_status=creative_commons_attribution_required`;
- `commercial_use_allowed=true`;
- `attribution_required=true`;
- creator/title/source URL/license preserved.

If license is not verified, source is not downloaded by this mode. If downloaded media is not near 9:16 / audible / >= clip length, it is rejected.

After importing one or more CC sources, normal:

```powershell
vv render-animal 2
```

uses imported YouTube sources first and Pexels/Pixabay fill remaining slots.

## Ordinary YouTube — isolated test-only comparison

User also wants to compare ordinary funny YouTube cats privately without treating them as publishable media.

We do **not** auto-download standard/unverified YouTube media. Instead an already-local exact file can be added to a hard-isolated pool:

```powershell
vv-cat-youtube test-add 2 --url "https://youtube..." --file "D:\path\cat.mp4" --confirm-match
```

It goes only under:

```text
runtime/test_only/slot-02/
```

and gets:

- `do_not_publish=true`;
- `publication_allowed=false`;
- `commercial_use_allowed=false`;
- `rights_verified=false`;
- `rights_status=test_only_unverified`.

It never enters `runtime/slots/02/sources.json` or `runtime/ready_for_review`.

After at least 3 test-only clips:

```powershell
vv-cat-youtube test-render 2
```

Output:

```text
runtime/test_only/slot-02/render-test-only.mp4
```

Cards say `ТЕСТ — Котики`; render refuses if publication locks are missing.

## Rights notes

- YouTube CC Attribution permits reuse subject to CC BY / attribution, but metadata is rechecked fail-closed.
- Standard/unverified YouTube is not converted into permission merely by being a local experiment.
- YouTube Terms also restrict downloading content outside authorized mechanisms; therefore automatic download in our new tool is limited to the explicitly verified CC path, while ordinary-video comparison requires an already-local file.
- Creative Commons alone still does not guarantee YouTube monetization under reused-content policy; human review/editorial transformation remain relevant.

## Tests in current YouTube source change

Added regression coverage for:

- standard license rejected by CC production mode;
- CC search keeps only verified CC metadata and dedupes;
- test-only import remains under `runtime/test_only` and never creates production sources;
- test-only render refuses a missing publication lock.

GitHub CI `test` job passed on the first YouTube-source code head; a newer head including `cc-search` is still to be checked before claiming full CI success.

## Next local checkpoint

After CI/current pull:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-youtube.exe cc-search
```

Send the CC-search output first. If it finds a useful vertical-looking cat candidate, import that URL with `cc` and rerender slot 2 to compare against the Pexels-only version.
