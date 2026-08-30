# YouTube publishing — local setup (RU)

## Что уже делает проект

- `vv-youtube auth` — один раз открывает Google OAuth в браузере, сохраняет refreshable token локально и привязывает конкретный YouTube channel ID.
- `vv-youtube status` — показывает состояние OAuth/channel binding и число pending ready uploads.
- `vv-youtube upload-ready --dry-run` — показывает очередь без загрузки.
- `vv-youtube upload-ready` — загружает все ещё не загруженные ready videos по slot order.
- `vv-youtube upload-ready --limit 1 --newest` — загружает самый новый pending ready video.
- каждый успешный upload пишет рядом `<name>.upload.youtube.json`; наличие receipt предотвращает повторную загрузку того же local sidecar.
- scheduler перед новым render сначала лечит один старый pending upload, затем рендерит новый slot и публикует newest pending video.

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

Команда ничего не загружает. Она должна перечислить готовые `slot-*.upload.json`, для которых ещё нет `.youtube.json` receipt.

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

## Ночной scheduler

После того как backlog успешно загружен и OAuth token работает, установить scheduler обычной командой:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-longrun-task.ps1
```

Default triggers:

```text
01:30 MSK
03:30 MSK
05:30 MSK
```

Каждый trigger:

1. проверяет generation status;
2. проверяет YouTube uploader status;
3. пытается дозалить один старый pending upload;
4. генерирует ровно один следующий slot;
5. загружает newest pending video;
6. пишет всё в `runtime/scheduler/longrun-task.log`.

При upload failure новый MP4 остаётся локально; следующий trigger сначала повторяет pending publication, прежде чем создавать следующий slot.
