# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-30**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний локальный test run: **43 passed**.
- Последний показанный OpenAI ledger: **$0.0340 / $10.00**.
- Slot 1 RU AI Short — manual QUALITY PASS.
- Cat pipeline = local FFmpeg; MPT нужен только `ai_short`.
- Real user meow успешно подхватывается.
- **Impact title-card style принят пользователем; шрифт не менять без новой причины.**

## Slot 2 cats — принятый формат

- Impact `C:\Windows\Fonts\impact.ttf`;
- intro ~0.9s, transitions ~0.75s, end ~1.0s;
- one `#NNN — title` on intro/transitions;
- localized thanks end card;
- real meow;
- no voiceover, no BGM;
- original clip audio retained/normalized;
- minimum 5 unique audible licensed clips, target 6;
- long-run languages 80% EN / 20% RU, no duplicate translations.

Audible-source gate работает, но старый slot 2 footage = 6 Pexels clips и выглядит слишком stock-like. Поэтому текущая работа = community-informed тематический sourcing.

## Google Cloud не использовать

Пользователю не подходит Google Cloud с адресом/картой. `YOUTUBE_API_KEY` не обязателен. YouTube no-key discovery через `yt-dlp` работает без OAuth/account login/media download.

## YouTube no-key discovery — технически работает, quality слабая

Последний фактический результат пользователя:

```text
40 passed in 0.81s
YouTube cat trend candidates: 5 (CC already identified: 0)
```

Только один кандидат имел заметный signal (~55k views / ~6.9k views/day), остальные 4 почти без просмотров; **0/5 CC confirmed**. Поэтому YouTube discovery оставляем как дополнительный signal, но не тюним бесконечно как единственный источник.

Report: `runtime/trends/youtube-cat-cc.json`.

## Reddit/community discovery — подтверждено локально

CLI:

```powershell
vv-cat-community --days 30 --limit 30
```

Пользователь получил:

```text
43 passed in 0.54s
Reddit cat community candidates: 30
Feed warnings: 1
```

Top references включали:

1. `Cat saw the hoop and understood the assignment` — r/Catculations;
2. `Potraits with my three new babies` — r/cats;
3. `Trying to watch TV` — r/CatsAreAssholes;
4. `Supermodel` — r/Catswithjobs;
5. `Hired this cleaning lady but she's doing a terrible job` — r/Catswithjobs;
6. `Dolly with a little orange` — r/OneOrangeBraincell;
7. `My cat won’t stop bringing in nuts??` — r/WhatsWrongWithYourCat;
8. `Not a spa… Disrespectful!` — r/CatsAreAssholes;
9. `Every. Single. Day!` — r/CatsAreAssholes;
10. `Whenever I flip my cat over on my lap his self-cleaning mode is triggered.` — r/WhatsWrongWithYourCat.

Вывод: Reddit заметно полезнее как **brain/trend layer**. Но все Reddit posts остаются `author_permission_required`; media автоматически не импортируется.

Report: `runtime/trends/reddit-cat-trends.json`.

## Trend → Theme — РЕАЛИЗОВАНО

Новый module:

```text
src/vv_knopka/cat_theme.py
```

Новый CLI:

```powershell
vv-cat-theme <animal-slot>
```

Например для текущего RU slot 2:

```powershell
vv-cat-theme 2
```

Он читает `runtime/trends/reddit-cat-trends.json`, без новых OpenAI calls детерминированно ранжирует повторяющиеся community themes и пишет:

```text
runtime/slots/02/trend-theme.json
```

Theme taxonomy сейчас покрывает:

- `cat_mischief` — interruptions / disrespect / household sabotage;
- `important_jobs` — cats with jobs / assignments / supervision;
- `weird_cat_logic` — странные привычки/предметы;
- `orange_chaos` — orange-cat chaos;
- `cat_calculations` — jumps / hoops / balancing;
- `main_character_cats` — posing / dramatic stares / model behavior;
- safe generic fallback `current_cat_chaos`.

Повторяющиеся сигналы суммируются; single viral reference не обязан автоматически победить несколько согласованных community references.

Theme output содержит:

- localized episode title;
- editorial angle;
- 6-8 **licensed-stock search terms**, все anchored на `cat`;
- scene prompts;
- ranked themes + evidence Reddit links/scores;
- stable `theme_signature`;
- rights policy: Reddit = reference only, usable footage = existing license/provenance/audio gates.

## Интеграция темы в render-animal

Если `runtime/slots/XX/trend-theme.json` существует, `vv render-animal XX`:

1. берёт старый `plan.json`, если он есть, или строит cat plan из theme без writer API;
2. применяет theme title/hook/search terms/scene prompts;
3. пишет audit preview `effective-plan.json`;
4. если theme signature изменилась — архивирует старый active `sources.json` и старый `ai_materials.json`, не удаляя media files;
5. принудительно ищет новый themed licensed audible footage вместо старых случайных Pexels clips;
6. после успешного source gate stamps `sources.json` theme id/signature;
7. повторный render той же темы снова может использовать cache;
8. source manifest change автоматически инвалидирует old highlight selection.

Это важно: trend-to-theme теперь влияет **не только на название**, но и на реально искомые клипы.

## Rights / monetization

- Reddit = inspiration/trend signal only, public post не означает reuse permission.
- YouTube unverified = trend reference only; CC должен быть реально подтверждён.
- Pexels/Pixabay footage проходит existing commercial-use + provenance + audible audio gates.
- Human review обязателен; raw social repost workflow не добавлять.

## Следующая точка на ПК

После pull/reinstall:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv-cat-theme.exe 2
```

Ожидаемый test count после новых theme tests: около **47 passed**.

Сначала прислать вывод `vv-cat-theme 2`: выбранную theme, title, evidence и search terms. Если theme выглядит логично, затем:

```powershell
.\.venv\Scripts\vv.exe render-animal 2
```

Этот render намеренно может снова вызвать Luna/source search, потому что старые Pexels clips должны быть заменены тематическими. Если audible-themed stock окажется слишком редким и gate даст <5 clips — не ослаблять gate автоматически; анализировать exact audit.
