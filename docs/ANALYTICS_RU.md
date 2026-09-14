# Analytics storage v0

## Назначение

Этот этап сохраняет каждый уже существующий снимок `vv-youtube stats` в локальную
SQLite-базу `runtime/analytics/analytics.sqlite3`. Он не меняет генерацию,
очередь публикации или YouTube metadata и не выполняет LLM-запросы.

JSON-файлы `runtime/youtube/statistics.json` и
`runtime/youtube/statistics-history.jsonl` остаются резервным читаемым журналом.

## Что хранится

- стабильная карточка видео: slot, video_id, pipeline, category, язык, профиль,
  название и время публикации;
- все снимки views/likes/comments и возраст видео на момент измерения;
- nullable-поля для будущего импорта YouTube Analytics:
  engaged views, AVD, APV, подписки и shares;
- nullable `stayed_to_watch_percentage`: API сейчас его не заполняет и система
  не подменяет эту метрику другими показателями;
- контрольные точки 24, 72 и 168 часов.

Для каждой контрольной точки выбирается первый доступный снимок после нужного
возраста. Если позже импортирован более близкий снимок, ссылка обновляется на него.

Старые `animal_compilation` временно классифицируются как `cats`, старые
`ai_short` — как `animals`. Явная категория будущих выпусков имеет приоритет.

## Теневой режим

Ошибка SQLite добавляется как warning в JSON-снимок, но не прерывает YouTube
workflow. Это особенно важно для уже работающего планировщика: статистика остаётся
телеметрией, а не publication gate.

Проверка состояния:

```powershell
.\.venv\Scripts\vv-youtube.exe analytics-status
```

Первичное заполнение текущими данными:

```powershell
.\.venv\Scripts\vv-youtube.exe stats
.\.venv\Scripts\vv-youtube.exe analytics-status
```

Стоимость OpenAI API этого этапа: `$0`.
