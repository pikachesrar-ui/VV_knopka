# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Ветка `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя.

## Что завершено

- Frozen pilot: 15/15 Shorts, визуально принят пользователем.
- Первый real long-run slot 16 EN cats / #008 успешно завершён.
- Следующий deterministic target = slot 17 AI EN.
- Long-run scheduler = до 3 запусков за ночь: 01:30, 03:30, 05:30 МСК.
- Последний показанный ledger: `$0.1885 / $10.00`.

## Новое явное решение пользователя: auto-publish

Пользователь попросил:

1. будущие generated Shorts сразу выкладывать на YouTube;
2. уже готовые ролики тоже выложить.

Поэтому pilot исторически остаётся `auto_publish=false`, но новая секция `[youtube]` намеренно:

```toml
enabled = true
auto_publish = true
privacy_status = "public"
category_id = "15"
made_for_kids = false
notify_subscribers = false
```

Не откатывать это обратно в review-only без нового решения пользователя.

## YouTube uploader — реализован

Новые файлы/CLI:

```text
src/vv_knopka/youtube_uploader.py
src/vv_knopka/youtube_cli.py
docs/YOUTUBE_PUBLISHING_RU.md
vv-youtube
```

Команды:

```powershell
.\.venv\Scripts\vv-youtube.exe status
.\.venv\Scripts\vv-youtube.exe auth
.\.venv\Scripts\vv-youtube.exe upload-ready --dry-run
.\.venv\Scripts\vv-youtube.exe upload-ready
```

Поведение:

- OAuth Desktop app JSON: `runtime/youtube/client_secret.json`.
- Token: `runtime/youtube/token.json`.
- Channel binding: `runtime/youtube/channel.json`.
- scopes = `youtube.upload` + `youtube.readonly`.
- `auth` открывает browser OAuth и печатает channel title + ID.
- uploader fail-closed, если текущий OAuth channel ID отличается от сохранённого binding.
- каждый successful upload пишет `<slot...upload>.youtube.json` receipt.
- receipt предотвращает duplicate upload при retry.
- `upload-ready` идёт по slot order; `--newest --limit 1` используется scheduler для только что созданного ролика.
- requested и actual privacy сохраняются отдельно.

Важно: официальный YouTube `videos.insert` может принудительно ограничить upload до `private` для API projects, подпадающих под YouTube audit requirement. Не утверждать, что ролик public, если API response вернул private.

## Existing backlog

На пользовательском ПК ready backlog сейчас минимум slots 1–16. После OAuth:

```powershell
.\.venv\Scripts\vv-youtube.exe upload-ready --dry-run
.\.venv\Scripts\vv-youtube.exe upload-ready
```

Первый вызов preview-only. Второй загружает все pending по возрастанию slot. При interruption уже успешные slots будут пропущены по receipts.

## Scheduler после auto-publish

`run-longrun-task.ps1` теперь:

1. lock;
2. `vv status`;
3. `vv-youtube status`;
4. retry одного старого pending upload;
5. `vv longrun-next`;
6. upload newest pending ready video;
7. log.

Если pending YouTube retry не прошёл, scheduler не создаёт новый slot до восстановления публикации. Если generation прошёл, а post-upload упал, следующий trigger сначала повторяет pending upload.

Installer остаётся одной Windows task с default triggers:

```text
01:30
03:30
05:30
```

## Long-run cat sourcing

- last 5 rendered cat episodes source IDs protected;
- fresh remote Pexels/Pixabay first;
- cooled old stock fallback only;
- local cooled history can seed after fresh minimum failure;
- local history revalidated 9:16 + audible audio;
- provenance/commercial-use/Luna/minimum-count gates unchanged.

## Budget / safety

- OpenAI hard cap `$10` unchanged.
- Не добавлять paid providers без explicit approval.
- OAuth/token/client secret не коммитить и не просить пользователя вставлять в чат.
- `runtime/` ignored.
- PR #1 stays draft/open/unmerged.

## Tests / CI

YouTube uploader regressions добавлены для:

- numeric slot-order backlog;
- newest dry-run selection without OAuth/network;
- idempotent receipt skip.

После uploader code Ubuntu job прошёл **117 tests**. Windows job для этого head нужно recheck live перед утверждением полного workflow success.

## Immediate continuation

Нужна только локальная OAuth-настройка:

1. `git pull`;
2. `pip install -e ".[dev]"`;
3. Google Cloud: enable YouTube Data API v3, создать OAuth client типа Desktop app;
4. сохранить JSON в `runtime/youtube/client_secret.json`;
5. `vv-youtube auth`;
6. пользователь присылает только напечатанные channel title + ID, НЕ JSON/token;
7. после подтверждения канала — dry-run backlog и реальный backlog upload;
8. затем install scheduler.
