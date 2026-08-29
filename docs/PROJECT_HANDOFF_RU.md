# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл хранит продуктовые решения и точку продолжения.

Последнее содержательное обновление: **2026-08-30**.

## 1. Frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.
Рабочая ветка: `mvp/pilot-scaffold`.
Draft PR #1 открыт, не merge без отдельного решения пользователя.

Pilot: 15 Shorts; 8 × `ai_short`; 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cat test, остальные 13 EN; one channel; OpenAI hard budget `$10`; `auto_publish=false`; human review; outputs only `runtime/ready_for_review`.

## 2. Локально подтверждено

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- OpenAI/Pexels/Pixabay keys local `.env`;
- MPT only for `ai_short`; cats = local FFmpeg;
- latest user test: **43 passed**;
- publication gate **PASS**;
- latest OpenAI ledger **$0.0340 / $10.00**;
- slot 1 octopus manual QUALITY PASS;
- real user meow works;
- slot 2 audible gate previously found 6/6 Pexels clips with real audio;
- **Impact title-card style approved**.

## 3. Cat format — approved checkpoint

- no voiceover / no BGM;
- real meow on black cards;
- intro ~0.9s, transitions ~0.75s, end ~1.0s;
- intro + transitions repeat one `#NNN — title`;
- localized thanks end card;
- clean cat clips, original source audio retained/normalized;
- minimum 5 unique audible licensed clips, target 6;
- long-run `en,en,en,en,ru` = 80/20 originals, no translated duplicates;
- Windows card font pinned to `C:\Windows\Fonts\impact.ttf`, sizes 84/78/82;
- never use `Daily Dose of Cats` or close imitation.

## 4. Why trend/community sourcing exists

The stock audio gate works, but old slot 2 footage still looks like generic Pexels stock. User wants current/popular cat content closer to real Shorts/TikTok/community aesthetics.

Safe architecture:

```text
public trend/reference discovery -> theme extraction -> licensed-footage search -> source/audio/Luna gates -> highlight edit -> renderer
```

Do NOT default to raw social scraper/repost.

## 5. Google Cloud rejected by user

Initial YouTube discovery required `YOUTUBE_API_KEY`. User tried Google Cloud but it asked for address/card and explicitly said this does not suit them.

Decision: **Google Cloud/API key is not required/default. Do not tell user to add billing/card/address.**

## 6. YouTube no-key discovery — working but weak

Dependency: `yt-dlp>=2026.1,<2027`.
CLI: `vv-cat-trends --days 30 --limit 30`.
No OAuth/account login/media download.

Runtime fixes already made:

1. removed broken `ytsearchdate` usage -> ordinary `ytsearchN:`;
2. flat search results lacked dates -> added full metadata hydration (`download=False`);
3. current-year multi-query search added;
4. local recency/duration filters + views/day ranking;
5. rights fail closed.

Latest actual user output:

```text
40 passed in 0.81s
YouTube cat trend candidates: 5 (CC already identified: 0)
```

Only one candidate had meaningful traction (~55k views / ~6.9k views/day), other 4 had 23/7/5/2 views. **0/5 Creative Commons confirmed.** Verdict: YouTube no-key discovery technically works but is not good enough as the only trend source. Keep it as a secondary signal.

Report: `runtime/trends/youtube-cat-cc.json`.

## 7. Reddit/community discovery — locally confirmed useful

Module: `src/vv_knopka/reddit_trend_discovery.py`.
CLI:

```powershell
vv-cat-community --days 30 --limit 30
```

Default communities:

- cats
- WhatsWrongWithYourCat
- OneOrangeBraincell
- CatsAreAssholes
- Catculations
- Catswithjobs

Mechanics: public Reddit RSS (`top/week` + `hot`), no API key/login, www + old fallback, rank/recency community score, feed diagnostics instead of total failure, media hint extraction only for reference.

Actual user run:

```text
43 passed in 0.54s
Reddit cat community candidates: 30
Feed warnings: 1
```

Actual top references included:

1. Cat saw the hoop and understood the assignment — r/Catculations;
2. Potraits with my three new babies — r/cats;
3. Trying to watch TV — r/CatsAreAssholes;
4. Supermodel — r/Catswithjobs;
5. Hired this cleaning lady but she's doing a terrible job — r/Catswithjobs;
6. Dolly with a little orange — r/OneOrangeBraincell;
7. My cat won’t stop bringing in nuts?? — r/WhatsWrongWithYourCat;
8. Not a spa… Disrespectful! — r/CatsAreAssholes;
9. Every. Single. Day! — r/CatsAreAssholes;
10. Whenever I flip my cat over on my lap his self-cleaning mode is triggered. — r/WhatsWrongWithYourCat.

Rights remain:

```text
rights_status = author_permission_required
import_status = trend_reference_only_until_author_permission
auto_download = false
```

Reddit is now the primary **trend brain**, not a reusable-media provider.

Report: `runtime/trends/reddit-cat-trends.json`.

## 8. Trend → Theme layer — IMPLEMENTED

New module:

```text
src/vv_knopka/cat_theme.py
```

New entry point:

```powershell
vv-cat-theme <animal-slot>
```

Default report input:

```text
runtime/trends/reddit-cat-trends.json
```

For current slot 2:

```powershell
vv-cat-theme 2
```

No OpenAI writer call is used for theme extraction; ranking is deterministic and free.

Current theme taxonomy:

- `cat_mischief`: interruptions / disrespect / household sabotage;
- `important_jobs`: jobs / assignments / supervision;
- `weird_cat_logic`: odd habits / objects / self-cleaning style behavior;
- `orange_chaos`: orange-cat chaos;
- `cat_calculations`: jumps / hoops / balance / catches;
- `main_character_cats`: posing / model / dramatic stare behavior;
- fallback `current_cat_chaos`.

Scoring combines each Reddit candidate's `community_score`, keyword matches, subreddit fit and a repeat-signal bonus. This intentionally favors repeated community patterns over a single isolated reference.

Generated `trend-theme.json` contains:

- selected `theme_id` + stable `theme_signature`;
- localized episode title;
- localized editorial angle;
- 6-8 EN stock search terms anchored on exact word `cat`;
- localized scene prompts;
- ranked themes;
- evidence rows with Reddit title/subreddit/url/community score;
- explicit rights policy: Reddit media not auto imported; final footage must pass existing license/provenance/audio gates.

Output for slot 2:

```text
runtime/slots/02/trend-theme.json
```

Optional manual theme override exists:

```powershell
vv-cat-theme 2 --theme weird_cat_logic
```

## 9. render-animal theme integration — IMPLEMENTED

`src/vv_knopka/cli.py` now detects `runtime/slots/XX/trend-theme.json`.

Behavior:

1. If normal `plan.json` exists, theme overrides title/hook/search terms/scene prompts in-memory.
2. If plan is absent, a complete animal plan can be built from theme without OpenAI writer API.
3. Effective themed plan is written to:

```text
runtime/slots/XX/effective-plan.json
```

4. Theme affects highlight editorial context and episode title.
5. Most importantly, theme affects source search terms, so it is not just cosmetic.

## 10. Theme-aware source cache invalidation

Critical implementation detail: old Pexels clips must not silently survive a new trend theme.

`prepare_theme_source_refresh()`:

- compares current `theme_id` + `theme_signature` with active `sources.json`;
- if different, archives old source manifest as `sources-before-theme-<hash>.json`;
- archives old generic `ai_materials.json` as `ai_materials-before-theme-<hash>.json` and removes only the active audit file;
- does **not** delete actual media files;
- writes an empty active source manifest so the next `ensure_audio_animal_sources()` must perform a fresh themed search.

After successful source gate, `stamp_source_manifest_theme()` writes:

- `trend_theme_id`;
- `trend_theme_signature`;
- `trend_theme_search_terms`.

Therefore:

- new/different theme -> fresh stock search;
- same theme -> cached themed sources can be reused;
- source manifest changes still invalidate highlight signature automatically.

## 11. Controlled UGC import

`vv-cat-import` remains YouTube-only for automatic rights mapping and requires actual Creative Commons verification. Reddit candidates are not automatically importable without a separate creator-permission provenance path.

## 12. Rights / monetization constraints

- Public Reddit post is not permission to reuse media.
- YouTube `rights?` is not permission; CC must be verified.
- Pexels/Pixabay clips must preserve commercial-use metadata/provenance.
- Cat sources must pass real-audio gate.
- Human review remains mandatory.
- Creative Commons/permission does not by itself solve YouTube reused-content monetization; editorial transformation still matters.

## 13. Tests added for theme layer

New `tests/test_cat_theme.py` covers:

- repeated mischief signal beating unrelated reference;
- localized title + cat-anchored stock queries;
- building/overriding a cat plan without writer API;
- changed-theme source archive/reset + same-signature cache reuse.

Given confirmed 43 tests before theme layer, expected next local count is around **47 passed**.

## 14. Next local checkpoint

Run:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-theme.exe 2
```

First inspect `vv-cat-theme 2` output: selected theme, title, evidence and search terms. If it looks coherent, then:

```powershell
.\.venv\Scripts\vv.exe render-animal 2
```

Expected first themed render behavior:

- console says old stock cache is archived / fresh themed search forced;
- Luna/source search may spend a small additional amount from the existing `$10` cap;
- old generic Pexels clips are not silently reused;
- final review should check whether footage actually matches selected community-informed theme while retaining real source audio.

If themed audible stock finds fewer than 5 usable clips, do not weaken the gate automatically; inspect `runtime/slots/02/animal_audio_sources.json` and decide next source strategy.

Do not merge Draft PR #1 until explicit pilot quality approval.
