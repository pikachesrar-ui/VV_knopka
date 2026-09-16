# Analytics storage v3

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
- длительность ролика из Studio export;
- контрольные точки 24, 72 и 168 часов.

Для каждой контрольной точки выбирается первый доступный снимок после нужного
возраста, но не позднее чем через 24 часа после цели. Поэтому снимок ролика
возрастом 180 часов не будет ошибочно называться «24h». Если позже импортирован
более близкий снимок, ссылка обновляется на него.

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


## Импорт ранее накопленной истории

После первого обновления выполните один раз:

```powershell
.\.venv\Scripts\vv-youtube.exe analytics-import-history
.\.venv\Scripts\vv-youtube.exe analytics-status
```

Команду безопасно повторять: одинаковые строки определяются по
`video_id + collected_at + source` и второй раз не вставляются. Повреждённая
строка JSONL учитывается в `invalid`, остальные снимки продолжают импортироваться.

## Расширенные метрики YouTube Analytics API

Один раз включите **YouTube Analytics API** в том же Google Cloud project, где
уже включён YouTube Data API, затем расширьте существующий OAuth token:

```powershell
.\.venv\Scripts\vv-youtube.exe auth-analytics
```

Команда запрашивает только `yt-analytics.readonly`, сохраняя уже выданные upload,
readonly и metadata-edit scopes. После OAuth обязательно проверяется прежний
channel binding; при несовпадении каналов старый token восстанавливается.

Обычный сбор:

```powershell
.\.venv\Scripts\vv-youtube.exe analytics-sync
```

Он получает по каждому опубликованному bot receipt:

- views и engaged views;
- estimated watch time;
- Average View Duration и Average Percentage Viewed;
- likes, comments и shares;
- subscribers gained/lost.

Scheduler вызывает этот сбор как необязательную телеметрию не чаще одного раза
в 20 часов. Ошибка scope/API не останавливает генерацию или публикацию.
YouTube Analytics может отставать от Data API у совсем нового ролика. В таком
случае `videos=0/1` означает «данные ещё не обработаны»: бот не сохраняет
искусственный нулевой снимок, а повторит сбор позже.

Источники трафика и полная кривая удержания требуют отдельных запросов для
каждого ролика, поэтому автоматически трижды в сутки не собираются. Их можно
получить вручную для нужного выпуска:

```powershell
.\.venv\Scripts\vv-youtube.exe analytics-sync --deep --slots 23
```

Без `--slots` deep sync пройдёт по всем bot-видео. Это не расходует OpenAI или
деньги, но делает больше запросов к YouTube Analytics API.

## Импорт ZIP/CSV из YouTube Studio

Некоторые Shorts-поля, включая точное `Stayed to watch / Продолжили смотреть`,
могут отсутствовать в Analytics API. В Advanced Mode YouTube Studio выберите
нужные столбцы, экспортируйте CSV/ZIP и выполните:

```powershell
.\.venv\Scripts\vv-youtube.exe analytics-import-studio "C:\Users\Office\Downloads\youtube-studio.zip"
```

Поддерживаются русские и английские названия основных столбцов. Импортируются
только видео, для которых есть локальный bot receipt; старые посторонние ролики
канала пропускаются. Одинаковый файл определяется по SHA-256 и не дублируется.
`Stayed to watch` никогда не вычисляется из engaged views и остаётся `null`,
если Studio не передал точный столбец.

## Один файл для передачи на анализ

После автоматического sync и/или Studio import выполните:

```powershell
.\.venv\Scripts\vv-youtube.exe analytics-export
```

Команда создаёт:

```text
runtime/analytics/exports/vv-analytics-YYYYMMDD-HHMMSS.zip
```

Этот ZIP можно целиком отправить в чат. Внутри находятся карточки видео, все
снимки, checkpoints 24/72/168h, traffic sources, retention curves, история sync
и доступные локальные признаки сценария (hook/script/category/profile). OAuth
token, client secret и API keys в пакет не включаются.

Рекомендуемый ручной сбор перед отправкой файла:

```powershell
.\.venv\Scripts\vv-youtube.exe stats
.\.venv\Scripts\vv-youtube.exe analytics-sync --deep --slots 23
.\.venv\Scripts\vv-youtube.exe analytics-export
```

Стоимость OpenAI API всех этих команд: `$0`.

## Проверка на реальных данных 2026-09-15

Первый пользовательский bundle содержал 23 видео и 557 снимков. Slot 23 имел
174 Studio views через 13.6 часа против прежнего максимума 22, однако Analytics
API ещё не вернул owner-only строку, поэтому AVD/APV, traffic и retention пока
отсутствовали. Реальный прогон выявил и устранил два искажения: synthetic zero
при задержке Analytics API и слишком поздние checkpoints. Schema v3 также
сохраняет `duration_seconds`, уже присутствующую в Studio CSV.
