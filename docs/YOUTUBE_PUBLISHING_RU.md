# YouTube publishing — local setup (RU)

## Что уже делает проект

- `vv-youtube auth` — один раз открывает Google OAuth в браузере, сохраняет refreshable token локально и привязывает конкретный YouTube channel ID.
- `vv-youtube status` — показывает состояние OAuth/channel binding, число pending ready uploads и активный upload-limit cooldown, если он есть.
- `vv-youtube pending-count` — печатает только число pending ready uploads; используется scheduler.
- `vv-youtube upload-ready --dry-run` — показывает очередь без загрузки.
- `vv-youtube upload-ready` — загружает ещё не загруженные ready videos по slot order.
- `vv-youtube upload-ready --limit 1 --newest` — загружает самый новый pending ready video.
- каждый успешный upload пишет рядом `<name>.upload.youtube.json`; наличие receipt предотвращает повторную загрузку того же local sidecar.

OAuth/token/channel files находятся в `runtime/youtube/` и не попадают в Git, потому что весь `runtime/` ignored.

## Один раз в Google Cloud

1. Выбрать/создать Google Cloud project.
2. Включить **YouTube Data API v3**.
3. Настроить OAuth consent screen для своего аккаунта.
4. Создать OAuth Client ID типа **Desktop app**.
5. Скачать JSON credentials.
6. Сохранить его локально как:

```text
D:\KiraS\VV_knopka\runtime\youtube\client_secret.json
```

Не отправлять этот JSON в чат и не коммитить.

## Привязка канала

После `git pull` и reinstall:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\vv-youtube.exe status
.\.venv\Scripts\vv-youtube.exe auth
```

Откроется браузер Google OAuth. Войти именно в аккаунт/канал, на который должны идти Shorts.

Команда после OAuth печатает:

```text
YouTube channel bound: <title> (<channel_id>)
```

Проверить название канала перед первой реальной загрузкой. Uploader сохраняет этот channel ID и на каждом будущем upload fail-closed, если текущий OAuth вдруг указывает на другой channel ID.

## Проверка существующей очереди

```powershell
.\.venv\Scripts\vv-youtube.exe upload-ready --dry-run
```

Команда ничего не загружает. Она перечисляет готовые `slot-*.upload.json`, для которых ещё нет `.youtube.json` receipt.

## Загрузка уже сделанных роликов

После проверки канала и dry-run:

```powershell
.\.venv\Scripts\vv-youtube.exe upload-ready
```

Очередь идёт по возрастанию slot. Если процесс оборвётся, уже успешные uploads имеют receipts и при следующем запуске не дублируются.

Config сейчас запрашивает:

```toml
[youtube]
enabled = true
auto_publish = true
privacy_status = "public"
category_id = "15"
made_for_kids = false
notify_subscribers = false
```

Важно: YouTube может принудительно оставить API upload в `private`, если Google API project подпадает под требование YouTube audit. Receipt сохраняет и requested privacy, и фактически returned privacy.

## Daily upload limit / `uploadLimitExceeded`

YouTube имеет отдельный **channel daily video upload limit**. Это restriction платформы YouTube, а не quota Google Cloud project. Лимит общий для desktop, mobile и YouTube API; точное число зависит от channel/account history и других eligibility signals.

Реальный backlog upload пользователя 2026-08-30 дошёл до:

```text
reason: uploadLimitExceeded
message: The user has exceeded the number of videos they may upload.
```

Официальная рекомендация YouTube после достижения лимита — повторить через 24 часа. Advanced feature access обычно даёт более высокий daily upload limit; проверить можно в YouTube Studio → Settings → Channel → Feature eligibility.

Проект теперь обрабатывает это fail-safe:

- Python traceback не нужен: CLI печатает `DEFERRED` и выходит специальным nonzero code `75`;
- `runtime/youtube/upload-limit.json` фиксирует момент отказа и консервативный 24-hour `retry_not_before`;
- до истечения cooldown uploader не тратит новые upload attempts;
- успешные uploads до лимита уже имеют `.youtube.json` receipts и не будут продублированы;
- `vv-youtube status` показывает active cooldown и pending count.

## Ночной scheduler

Default triggers:

```text
01:30 MSK
03:30 MSK
05:30 MSK
```

Чтобы не биться о дневной limit и быстрее разгребать backlog, scheduler теперь использует **не больше одной публикации на trigger**.

Каждый trigger:

1. проверяет generation status;
2. проверяет YouTube uploader status;
3. считает pending ready uploads;
4. если backlog/pending > 0 — пытается загрузить **ровно один** oldest pending и завершает trigger без нового render;
5. только когда backlog = 0 — генерирует ровно один следующий slot и загружает его;
6. пишет всё в `runtime/scheduler/longrun-task.log`.

Таким образом approved 01:30/03:30/05:30 schedule создаёт upload pressure максимум **3 videos/day**, а старый backlog сначала уменьшается вместо одновременного накопления новых MP4.

Если YouTube возвращает daily limit, scheduler не создаёт новый slot, пока publication не восстановится. Если новый MP4 уже был создан до upload failure, следующий trigger сначала считает его pending backlog и пытается опубликовать его.
