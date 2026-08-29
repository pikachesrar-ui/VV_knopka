# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для кода/commit/CI; этот файл хранит продуктовые решения и точку продолжения.

Последнее содержательное обновление: **2026-08-29**.

## 1. Frozen pilot

Репозиторий: `pikachesrar-ui/VV_knopka`.
Рабочая ветка: `mvp/pilot-scaffold`.
Draft PR #1 открыт, не merge без отдельного решения пользователя.

Pilot:
- 15 Shorts;
- 8 × `ai_short`;
- 7 × `animal_compilation`;
- slot 1 = RU AI Short;
- slot 2 = RU cat compilation test;
- остальные 13 = EN;
- один YouTube channel;
- OpenAI hard budget = `$10`;
- `auto_publish=false`, human review обязателен;
- outputs только в `runtime/ready_for_review`.

## 2. Подтверждённая локальная среда

Путь: `D:\KiraS\VV_knopka`.

- `.venv` Python `3.11.0`;
- OpenAI/Pexels/Pixabay keys локально в `.env`;
- MoneyPrinterTurbo v1.3.5 установлен отдельно;
- MPT API работает, но **animal/cat renderer MPT не использует**;
- cat videos рендерятся локально через FFmpeg;
- последний подтверждённый локальный run перед текущей style-edit: `25 passed`, publication gate PASS;
- последний показанный OpenAI ledger: `$0.0281 / $10.00`;
- slot 1 («Почему осьминог меняет цвет во сне») — manual QUALITY PASS.

## 3. AI short architecture

Terra plan -> Pexels/Pixabay -> GPT-5.6 Luna relevance gate -> local stock -> MPT local render -> Edge TTS/subtitles -> review output.

Ключевые fixes: final MPT `videos`, anchor-aware cache, Luna visual relevance, stock-friendly topic picker, landscape blur-fill, Cyrillic font, subtitle size 52 / position 74%, no per-clip FadeIn.

## 4. Cat pipeline history

### v1
6 stock clips, первые куски, почти без звука.

### v2
Luna выбирает highlights, source audio where available + BGM + procedural meow. Стало лучше, но montage всё ещё выглядел случайным.

### v3
Black cards + unique numbered title + Edge voice. Review: title overflow, voice/long intro не нужны.

### Текущая редактура
Пользователь хочет:

- no voiceover;
- no BGM;
- intro короткий;
- transition black card заметнее/дольше;
- intro + transitions показывают один title;
- end `Спасибо за просмотр` / `Thanks for watching`;
- настоящий постоянный meow;
- только clips с настоящим source audio;
- title text крупнее и визуально интереснее;
- footage меньше должно выглядеть как stock;
- в перспективе искать popular/current user cat videos из TikTok/Shorts/etc.

## 5. Cat renderer — актуальная реализация

`src/vv_knopka/animal_v3.py`:

- local FFmpeg only;
- no voice;
- no BGM;
- intro ~0.9s;
- transition ~0.75s;
- end ~1.0s;
- cat clips без overlay text;
- source audio нормализуется;
- title sizes: intro **84**, transition **78**, end **82**;
- wrap ~18 chars;
- каждая строка title рендерится отдельным `drawtext`, поэтому индивидуально центрируется;
- `#NNN` оформляется отдельным белым badge с чёрным номером;
- предпочитается более тяжёлый локальный Windows font: Arial Rounded MT Bold / Segoe UI Black / Trebuchet Bold / Impact fallback;
- local font можно переопределить `CAT_CARD_FONT` или `[animal].card_font_file`; font files не коммитить/не распространять.

`src/vv_knopka/animal_episode.py`:

- stable episode numbering;
- unique `#NNN — title`;
- запрещено `Daily Dose of Cats`;
- transitions повторяют display title;
- localized end text;
- intro voice metadata удалён.

## 6. Real meow — текущая политика

Предыдущий meow не подхватился, потому что resolver ожидал слишком точное имя/extension.

Теперь `_resolve_meow` пробует:

1. `CAT_MEOW_FILE`;
2. configured `meow_file`;
3. тот же basename с `.mp3/.wav/.m4a/.aac/.ogg/.flac/.opus`;
4. `runtime/assets/cat-transition-meow.*`;
5. `runtime/assets/cat-meow.*`;
6. `runtime/assets/meow.*`;
7. любой audio file с `meow` в имени в `runtime/assets`;
8. friendly meow names в корне repo как дополнительный fallback.

Renderer печатает:

```text
Cat meow asset: <actual path>
```

Если real file не найден — явный procedural fallback message.

## 7. Audible stock gate — подтверждён на ПК

Пользователь прислал `animal_audio_sources.json` после запуска gate.

Подтверждено:

- required minimum = 5;
- target = 6;
- **selected = 6**;
- Pexels candidates = 60;
- vision-approved = 54;
- audio-accepted = 6;
- Pixabay не понадобился;
- множество Pexels clips reject как no audio stream / effectively silent;
- accepted mean volumes примерно от `-54.5 dB` до `-12.2 dB`.

То есть audio gate работает: source обязан иметь stream и `volumedetect` signal выше default `-55 dB`.

Audit:

```text
runtime/slots/02/animal_audio_sources.json
```

## 8. Trend / UGC sourcing — важное направление

Пользователь хочет меньше stock-looking footage и больше актуальных viral/user clips.

Архитектурное решение: **discovery отдельно от ingest**.

### Discovery candidates

Можно собирать URLs/metadata из:

- TikTok;
- YouTube / Shorts;
- Instagram / Reels;
- Reddit;
- других публичных источников.

Хранить: URL, creator, publish time, views/likes/shares if available, topic, rights status.

### Rights gate обязателен

Не превращать default workflow в автоматический TikTok/social downloader.

Почему:

- TikTok Display API читает videos только у авторизованного user; это не global trending search.
- TikTok Research API умеет query public videos/metrics, но intended for approved non-profit research, не production sourcing.
- YouTube Data API умеет `videoLicense=creativeCommon`; это один из clean discovery signals.
- YouTube reused-content policy прямо относит короткие compilations из других social media с минимальной трансформацией к monetization risk; permission itself не гарантирует eligibility.

Рекомендуемый future module:

```text
trend_discovery -> candidate queue -> rights/license/permission gate -> download/ingest -> Luna highlight -> renderer
```

TikTok/Instagram links могут входить в discovery queue, но не auto-ingest без explicit reusable rights. Для viral licensed UGC можно позже оценить paid licensing providers, но frozen pilot запрещает подключать новый paid provider без explicit user decision.

## 9. Language policy

- никаких RU/EN дублей одного ролика;
- long-run cadence: `en, en, en, en, ru` = 80/20 originals;
- frozen pilot: slot 2 RU, остальные animal slots EN.

## 10. MoneyPrinterTurbo note

Если MPT/browser закрыты, но `render-animal` работает — это ожидаемо. MPT нужен только `render-ai`.

## 11. Следующая точка

На ПК:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

Проверить console lines:

```text
Cat card font: ...
Cat meow asset: ...
```

Если meow снова fallback — прислать точное имя и полный local path выбранного sound file.

Expected review output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

После style review решить: внедрять `trend_discovery` первым этапом через YouTube/Creative Commons + public social URL queue, либо сначала ещё раз довести card/meow.
