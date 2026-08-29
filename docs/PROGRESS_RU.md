# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст — `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-29**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish=false`; publication gate = `PASS`.
- Последний локальный test run до текущей редактуры: **25 passed**.
- Последний показанный OpenAI ledger: **$0.0281 / $10.00**.
- Slot 1 Russian AI Short («Почему осьминог меняет цвет во сне») — manual QUALITY PASS.
- MoneyPrinterTurbo нужен для `ai_short`, но **не нужен для cat/animal pipeline**: котики рендерятся локально через FFmpeg.

## Slot 2 cats — подтверждённый audio sourcing

Пользователь прислал `animal_audio_sources.json` после нового source-audio gate.

Результат:

- target = 6;
- selected = **6**;
- Pexels candidates = 60;
- Luna vision-approved = 54;
- audible accepted = 6;
- Pixabay не понадобился;
- десятки stock clips были отброшены как `remote file has no audio stream` или `missing/effectively silent audio`;
- принятые clips имеют измеренный `mean_volume_db` примерно от `-54.5` до `-12.2 dB`.

То есть audible-source gate реально работает и больше не должен молча собирать почти немой montage.

## Последний визуальный review

После предыдущей редактуры пользователь отметил:

- fit текста уже лучше;
- title-card всё ещё выглядит слишком просто/скучно;
- текст хочется крупнее;
- пользовательский meow не был подхвачен;
- Pexels footage всё ещё выглядит слишком «stock»;
- хочется уметь находить актуальные пользовательские/viral cat clips из TikTok/Shorts/других площадок.

## Cat card — текущая редактура в ветке

Реализовано:

- title size: **84**;
- transition title size: **78**;
- end size: **82**;
- wrap target: ~18 chars;
- каждая строка теперь рендерится отдельным FFmpeg `drawtext`, поэтому строки центрируются **индивидуально**, а не левым краем внутри общего блока;
- `#NNN` оформляется отдельным белым badge с чёрным номером;
- renderer предпочитает более тяжёлый локальный Windows font (Arial Rounded MT Bold / Segoe UI Black / Trebuchet Bold / Impact fallback), без коммита/распространения font files;
- можно переопределить локальный font через `CAT_CARD_FONT` или `[animal].card_font_file`.

## Meow fix

Причина прошлого failure: renderer ожидал слишком точное имя `runtime/assets/cat-transition-meow.mp3`.

Теперь он автоматически пробует:

- `CAT_MEOW_FILE`;
- configured `meow_file`;
- тот же basename с `.mp3/.wav/.m4a/.aac/.ogg/.flac/.opus`;
- `runtime/assets/cat-transition-meow.*`;
- `runtime/assets/cat-meow.*`;
- `runtime/assets/meow.*`;
- любой audio file с `meow` в имени в `runtime/assets`;
- те же friendly names в корне repo как дополнительный fallback.

При render обязательно печатается:

```text
Cat meow asset: <actual path>
```

или явное сообщение о procedural fallback.

## Trend / UGC sourcing — исследование

Цель пользователя: уйти от ощущения stock footage и учитывать популярные сейчас cat clips.

Решение: **разделить discovery и ingest**.

### Discovery можно расширить

Можно собирать candidates из:

- TikTok;
- YouTube / Shorts;
- Instagram / Reels;
- Reddit и других публичных источников.

Хранить: source URL, creator, publish time, views/likes/shares when available, topic/theme, rights status.

### Но default auto-download/repost нельзя делать без rights gate

- Official TikTok Display API читает public videos только авторизованного пользователя, а не весь TikTok.
- TikTok Research API умеет query public videos + metrics, но доступ предназначен для approved non-profit research use; это не нормальный production API для нашего канала.
- YouTube Data API умеет искать `videoLicense=creativeCommon`, что полезно как один clean discovery signal.
- YouTube monetization policy отдельно предупреждает о reused content: compilations из других social platforms с минимальной трансформацией могут быть неeligible даже при разрешении автора.

Поэтому рекомендуемый следующий слой: `trend_discovery` создаёт очередь candidates, но в renderer идут только clips с explicit reusable license / creator permission / owned upload. Direct social scraper не становится default.

Для по-настоящему viral licensed UGC позже можно отдельно оценить коммерческие licensing providers (не подключать без explicit user decision, т.к. pilot запрещает новые paid providers).

## Текущий cat format

- no voiceover;
- no BGM;
- intro black card ~0.9s;
- transition black card ~0.75s;
- end card ~1.0s;
- intro + transitions показывают один `#NNN — title`;
- end: `Спасибо за просмотр` / `Thanks for watching`;
- исходный clip audio сохраняется и нормализуется;
- minimum 5 unique audible licensed clips, target 6;
- real meow preferred; procedural only fail-safe.

## Языки

- никакого RU/EN дубля одного и того же ролика;
- long-run cadence: `en, en, en, en, ru` = 80/20;
- frozen pilot: slot 2 RU, остальные animal slots EN.

## Следующая точка на ПК

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

При render обратить внимание на строки:

```text
Cat card font: ...
Cat meow asset: ...
```

Если вместо второй строки виден procedural fallback, прислать точное имя/путь локального meow file.

Review output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

После этого решить, делаем ли отдельный `trend_discovery` слой (первый практичный provider — YouTube discovery + Creative Commons/rights metadata, TikTok/Instagram как discovery URLs without automatic ingest).
