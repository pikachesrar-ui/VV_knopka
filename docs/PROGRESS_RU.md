# VV_knopka — LIVE PROGRESS

Обновлено 2026-09-06.

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
Следом — локальный git pull, тесты и обычный scheduler цикл; не запускать manual batch.
Пилот 1–15 и ранее готовые видео сохраняются. TikTok вне scope. PR #1 не merge.
