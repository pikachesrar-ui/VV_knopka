# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-30**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний локальный test run: **47 passed**.
- Последний показанный OpenAI ledger: **$0.0340 / $10.00**.
- Slot 1 RU AI Short — manual QUALITY PASS.
- Cat pipeline = local FFmpeg; MPT нужен только `ai_short`.
- Real user meow работает.
- Impact title-card style принят.

## Slot 2 — последний ручной просмотр

Пользователь успешно собрал trend-themed render:

```text
Trend theme: important_jobs
Cat episode: #001 — Важные кошачьи дела
Audible licensed animal sources: 6
...
runtime/ready_for_review/slot-02-ru-animals.mp4
```

Ручная оценка: **«более менее»**, но выявлены две продуктовые проблемы:

1. Иногда source footage горизонтальное 16:9 и плохо выглядит в вертикальном Short.
2. Narrow theme не оправдывает себя: некоторые нормальные cat clips визуально не относятся к заявленной теме, поэтому ролик кажется несвязным.

Лог подтвердил проблему ориентации: среди принятых источников были, например, `1920x1080` и `2560x1440` landscape clips наряду с правильными `720x1280` portrait clips.

## Новое продуктовое решение — ПРОСТАЯ СБОРКА С КОТИКАМИ

Production cat pipeline больше **не использует narrow trend-theme**.

`vv render-animal <slot>` теперь:

- игнорирует старый `runtime/slots/XX/trend-theme.json`;
- автоматически строит generic cat plan без writer API;
- RU title = `Котики`, EN title = `Cats`;
- сохраняет `effective-plan.json` для аудита;
- ищет широкие cat queries: funny reaction / playing / jumping / running / curious / interacting / meowing / purring;
- Luna выбирает хорошие cat moments, но клип не обязан подтверждать узкую сюжетную тему.

`cat_theme.py`, Reddit/community и YouTube trend discovery можно оставить как research/reference tooling, но они **не управляют production render** по текущему решению пользователя.

## Vertical 9:16 source gate — ДОБАВЛЕНО

Cat footage теперь должно быть вертикальным и близким к 9:16 **до монтажа**.

Новый gate:

- target width/height = `9/16`;
- config `source_aspect_tolerance = 0.08`;
- landscape, square и visibly-wide portrait footage reject;
- Pexels search запрашивает `orientation=portrait`;
- Pexels/Pixabay candidate metadata фильтруется до Luna review;
- cached/local/imported files дополнительно проверяются реальным `ffprobe` width/height;
- downloaded file повторно проверяется перед acceptance;
- audit пишет source width/height/aspect;
- если остаётся <5 unique licensed + audible + vertical sources -> fail closed.

То есть старые `1920x1080` / `2560x1440` клипы из предыдущего render больше не должны пройти cache reuse.

## Accepted cat format — не менять без причины

- Impact `C:\Windows\Fonts\impact.ttf`;
- intro ~0.9s, transitions ~0.75s, end ~1.0s;
- numbered title card;
- localized end card;
- real meow;
- no voiceover;
- no BGM;
- original source audio retained/normalized;
- minimum 5 unique usable sources, target 6;
- 80% EN / 20% RU long-run cadence, no translated duplicates.

## Trend research status

YouTube no-key discovery технически работает, но первая полезная выдача была слабой: 5 recent candidates, 0 CC confirmed.

Reddit public-RSS discovery сработал лучше как source of ideas: 30 candidates, 1 feed warning. Но Reddit media остаётся `author_permission_required` и автоматически не импортируется.

Текущий production decision делает этот trend layer необязательным для cat render.

## Rights / monetization

- Reddit/public social post != reuse permission.
- YouTube unverified != permission; CC должен быть подтверждён.
- Pexels/Pixabay source должен сохранять provenance/commercial-use metadata.
- Human review обязателен.
- Raw social repost workflow не добавлять.

## Следующая точка на ПК

После pull/reinstall:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

Не запускать `vv-cat-theme 2`: production render его больше не использует.

Ожидаемый новый console start:

```text
Cat compilation mode: generic | title=Котики | effective plan: ...
Audible vertical licensed cat sources: ...
```

В новом `animal_audio_sources.json` проверить, что `selected_sources` имеют portrait near-9:16 dimensions. Если vertical+audio pool даст <5, gate не ослаблять автоматически — сначала смотреть audit и решать отдельно.
