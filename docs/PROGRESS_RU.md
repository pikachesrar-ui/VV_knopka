# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила остаются в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-28**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish = false`, publication gate = `PASS`.
- OpenAI/Pexels/Pixabay keys настроены локально в `.env`.
- MoneyPrinterTurbo v1.3.5 установлен, API работает на `127.0.0.1:8080`.
- `vv plan 1` создан: русский Short «Почему осьминог меняет цвет во сне».
- Первый plan-вызов OpenAI стоил `$0.0051`; общий hard cap пилота `$10`.
- После Pexels + Pixabay vision review общий ledger: **`$0.0104 / $10.00`**.
- Multi-source relevance gate дал 3 реально релевантных source videos.

## Первый render slot 1 — review FAIL

Первый MPT render создал видео, но пользователь увидел две проблемы:

1. review-файл был без звука;
2. Pexels подмешал нерелевантные кадры: fish/jellyfish/turtle/human skin.

Sound root cause исправлен: adapter раньше скачивал `combined_videos` (visual-only), теперь сначала берёт MPT `videos` (final output с TTS/subtitles).

## Material relevance — итог текущего этапа

- Strict Pexels slug gate: `2/8`, безопасно, но слишком низкий recall.
- Luna visual gate на 30 Pexels previews: `2/8`.
- Pexels + Pixabay: `3/8` unique source videos.
- Это подтвердило, что visual filter работает, а требование 8 отдельных stock-файлов завышено для узкой темы.

Теперь quality gate считает usable duration:

- минимум **3** unique vision-approved source videos;
- reusable segment size = **6 sec**;
- максимум **4 сегмента на source** для capacity calculation;
- минимум **36 sec** reusable approved footage;
- confidence остаётся `>=0.72`;
- filler не разрешается.

MPT curated footage использует `random`: сначала по одному segment от каждого unique source, затем непересекающиеся дополнительные segments.

## Второй render slot 1 — TECHNICAL PASS, QUALITY TUNING NEEDED

Пользователь получил второй MP4 и подтвердил:

- **звук есть**;
- содержание/кадры уже в целом достойные;
- результат можно считать технически рабочим;
- quality PASS пока не ставим: нужны визуальные доработки.

MPT task `d4e53d76-3be1-49f3-9dc2-fe6a944967ab`:

- audio duration: ~36.82 sec;
- Edge subtitles созданы;
- использованы 3 approved sources: 2 Pexels portrait + 1 Pixabay landscape;
- MPT сформировал 17 available subsegments и использовал 9 для покрытия narration;
- final video успешно создан.

### Замеченные quality-проблемы

1. **Русские субтитры выглядят плохо:** большой tracking/межбуквенные интервалы, неудачные переносы слов (`хроматофо / ры`).
   - root cause: MPT default `STHeitiMedium.ttc` — CJK font, неудачный выбор для русского.
2. **Landscape Pixabay source имеет большие black bars** в 9:16.
   - root cause: MPT сохраняет mismatched aspect ratio и помещает изображение на чёрный canvas.
3. **Некоторые кадры слишком тёмные при смене.**
   - root cause: `FadeIn` применяется отдельно к каждому 6-sec segment как fade-from-black, а не как crossfade между соседними clips.
4. Один длинный Pixabay source закономерно используется несколькими разными segments. Это допустимо, но дальше нужно следить, чтобы повторяемость визуально не бросалась в глаза.

## Текущий quality-fix в ветке

До следующего render внесено:

- `visual_transition = none`: убран per-clip FadeIn/black fade;
- для русских subtitles VV_knopka локально использует Windows Cyrillic font (приоритет Arial Bold -> Segoe UI Bold -> Arial -> Segoe UI), копируя его только в ignored MPT runtime; font никогда не коммитится;
- Russian subtitle font size = **46**;
- subtitle position = **custom, 68%**, выше нижней UI-зоны Shorts;
- stroke width = **2.2**;
- landscape local stock автоматически pre-rendered в **1080x1920 blur-fill**: размытый zoomed background + полный sharp original frame по центру;
- portrait stock остаётся без лишнего transcoding;
- derived `*-vv916.mp4` cache переиспользуется на следующих renders.

Не менять script/plan и не делать новые vision/API calls для этой quality-проверки.

## Точная следующая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-ai 1
```

`vv plan 1` повторно НЕ запускать.

Следующий render должен использовать тот же approved stock cache и не требовать новых Luna calls. При первом запуске новый code один раз подготовит landscape Pixabay source в `*-vv916.mp4`, поэтому перед MPT task может быть дополнительная локальная FFmpeg-пауза.

Проверить новый `runtime/ready_for_review/slot-01-ru-ai.mp4`:

- звук есть;
- русский subtitle font выглядит нормально, без разреженных букв;
- слова не разрываются так агрессивно;
- subtitles не слишком низко;
- нет black bars на landscape source;
- нет fade-to-black на каждой смене;
- octopus footage остаётся релевантным;
- повторяемость одного long source не раздражает.

Только после ручного quality PASS slot 1 переходить к slot 2. Автопубликация остаётся выключена.
