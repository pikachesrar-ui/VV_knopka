# VV_knopka — LIVE PROGRESS

Обновлено 2026-09-16.

## Подтверждено файлами пользователя 2026-09-05

20 опубликованных видео со статусом public; pending=0; 66 просмотров проекта.
AI: 39 на 10 видео; cats: 27 на 10 видео. Комментариев нет.
Slots 17–20 созданы/загружены. Следующий ожидаемый на момент снимка — 21 AI EN.
Текущий расход API не получен; бюджет $10 сохраняется.

## Реализовано в коде

- direct_v1 для новых renders со slot 21;
- котики: 3–4 сильных клипа из проверенного pool, без карточек;
- конкретные подписи и title/description из существующего highlight review;
- сильный первый/последний момент; quality gate вместо заполнения слабым материалом;
- AI: exact hook opens script, ранний ответ, opening metadata heuristic,
  sequential curated materials / 4 seconds;
- защита существующих MP4 от ручного overwrite через plan/render CLI;
- editorial_profile в upload sidecar и stats;
- output cap planner=1800 tokens, учёт расхода до разбора/валидации ответа;
- новых платных стадий нет.

178 tests PASS; FFmpeg smoke PASS (video/audio/captions/no cards).
Реальный MPT/Windows новый выпуск ещё не проверен. Это не подтверждение роста просмотров.

Команды применения, ограничения и анализ: [EDITORIAL_RU.md](EDITORIAL_RU.md).
Следом — локальный git pull, тесты и обычный scheduler цикл; сырые ручные
`longrun-next`/`upload-ready` не использовать, для серии есть поддерживаемый ярлык.
Пилот 1–15 и ранее готовые видео сохраняются. TikTok вне scope. PR #1 не merge.

## Получены slot 21/22 и выровнен звук будущих cats

- 21 готов 2026-09-06 00:35 UTC, 22 — 02:54 UTC, оба до коммита direct_v1
  (09:56 UTC), поэтому по ним новый монтаж ещё не оценить.
- У 22 ~5.7 секунд чёрных карточек; пики кошачьих клипов ~-1 dBTP,
  мяуканья ~-8 dBTP; средний звук большинства фрагментов близок к -16 LUFS.
- Для будущих cats: умеренная компрессия перед loudnorm, пик -8 dBTP,
  дополнительный limiter. Исходный тихий clip не усиливаем до громкого шума.
- Реальный FFmpeg-тест на звуке slot 22: пик тихого фрагмента снизился
  с ~-1 до ~-7.6 dBTP; 179 тестов PASS; новые опубликованные MP4 не трогали.
- Windows Python 3.11 не прочитал тестовый WAVE_FORMAT_EXTENSIBLE через stdlib
  `wave`; production filter успешно выполнился. Тест длительности переведён на
  ffprobe для Windows/Linux. Расход пользователя: $0.3087 / $10, gate PASS.


## 2026-09-14 — analytics storage v0

- Slot 23 повторно спланирован вручную после временного OpenAI 403; fact-check PASS,
  `runtime/slots/23/plan.json` создан. Ключ и модели Terra/Luna доступны.
- Добавлено теневое SQLite-хранилище всех снимков `vv-youtube stats`.
- Контрольные точки 24/72/168 часов выбирают первый доступный снимок после цели.
- Ошибка SQLite не блокирует публикацию; JSON/JSONL остаются резервным журналом.
- Новый этап не вызывает OpenAI и стоит $0 API.


- Добавлен идемпотентный `analytics-import-history`: переносит накопленный
  `statistics-history.jsonl` в SQLite, пропускает повреждённые строки и не
  дублирует уже импортированные снимки.


## 2026-09-14 — Auto-QA v0

- Локальные FFmpeg/ffprobe-проверки добавлены перед scheduler upload в shadow mode.
- QA пишет `*.qa.json`, но пока не блокирует уже работающую публикацию.
- Проверяются stream/resolution/duration, dark borders/opening/tail, loudness/peak,
  конфигурация voice/music, safe-zone снизу, SRT, outro CTA, pacing и source markers.
- Правая safe zone, pixel watermark и точный voice/music ratio честно отмечаются
  как SKIP, пока нет надёжного локального CV/OCR/stem анализа.
- OpenAI API не используется; стоимость этапа $0.

## 2026-09-15 — rich analytics v1

- Добавлен безопасный OAuth upgrade `auth-analytics` с проверкой старого channel binding.
- Core sync сохраняет engaged views, watch time, AVD/APV, реакции и подписки.
- Scheduler запускает его best-effort максимум раз в 20 часов; публикация не блокируется.
- Ручной `--deep` получает источники трафика и точки audience retention.
- Русские/английские Studio CSV/ZIP импортируются локально и идемпотентно.
- `analytics-export` собирает один secret-free ZIP для передачи на будущий анализ.
- SQLite schema v2 обновляла базу без удаления 465 уже импортированных snapshots.
- 193 tests PASS; OpenAI API и платные провайдеры не вызываются ($0).

## 2026-09-15 — проверка первого analytics bundle

- Bundle валиден: 23 bot-видео, 557 snapshots; secrets отсутствуют.
- Slot 23: 174 Studio views к 13.6h и 9 likes; прежний максимум — 22 views.
- YouTube Analytics API вернул 0 строк для свежего ролика, поэтому AVD/APV,
  traffic и retention пока честно остаются отсутствующими.
- Удалена запись ложного zero snapshot при API lag; старые такие строки
  очищаются автоматически.
- Checkpoints принимают снимок только в пределах 24h после цели; слишком поздние
  старые значения очищаются.
- Schema v3 хранит duration из Studio; cat-fact slot 23 получает category `cats`
  после повторного импорта/снимка. 198 tests PASS, OpenAI cost $0.

## 2026-09-16 — ручная серия и slot 24

- Trigger 01:30 дошёл до slot 24, но Pexels оборвал чтение по timeout; pending=0.
- Ручной повтор нормального runner восстановился без специальных обходов.
- Slot 24 опубликован public в 03:45: `https://www.youtube.com/watch?v=TujKlWJL-Eo`.
- QA: WARN, critical=0, warnings=6. Перед циклом slots 1–23 VERIFIED_PUBLIC.
- Ledger после планирования/рендера: $0.3314 / $10.
- Добавлен `start-three-video-batch.ps1`: три последовательных безопасных цикла,
  целевой интервал публикаций 60 минут, общий runner lock и fail-closed остановка.
- Успешная ручная серия подавляет ночные 01:30/03:30/05:30 до 06:30; при ошибке
  ночное восстановление снова разрешено.
- `install-manual-batch-shortcut.ps1` создаёт Desktop/Start Menu ярлыки для
  последующего закрепления кнопки на панели задач.
