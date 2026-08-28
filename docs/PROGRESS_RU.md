# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила остаются в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-28**.

## Уже подтверждено на ПК пользователя

- Windows bootstrap исправлен и успешно завершён.
- Project Python: `3.11.0`.
- Локальные тесты после bootstrap: `4 passed`.
- `auto_publish = false`.
- publication gate: `PASS`.
- OpenAI API key настроен локально в `.env` и не передавался в чат/GitHub.
- `vv plan 1` успешно создал `runtime/slots/01/plan.json`.
- Первый реальный OpenAI вызов стоил **$0.0051**.
- Project budget remains **$10.00**; spent: **$0.0051**.
- Slot 1: русский `ai_short` про изменение окраски осьминога во сне.
- Fact-check slot 1: PASS с обязательной осторожностью — не утверждать, что сновидения осьминогов доказаны.
- Временная диагностика ошибочного 401 полностью убрана после выяснения, что пользователь изначально неверно вставил API key.
- Удалён оставшийся `tests/test_openai_auth.py`, который импортировал уже удалённый временный модуль.

## Что добавлено для MoneyPrinterTurbo

В ветке `mvp/pilot-scaffold` добавлены:

- `scripts/setup-mpt-windows.ps1` — локально клонирует официальный `harry0703/MoneyPrinterTurbo` в игнорируемую папку `MoneyPrinterTurbo`, ставит `uv`, Python 3.11 и locked dependencies;
- `scripts/configure-mpt-windows.ps1` — берёт `PEXELS_API_KEY` из локального `VV_knopka/.env`, настраивает Pexels, Edge subtitles, `127.0.0.1:8080` и оставляет cross-posting выключенным;
- `scripts/start-mpt-api.ps1` — запускает локальный MPT API и должен оставаться открытым во время рендера.

MoneyPrinterTurbo не вендорится и не коммитится в наш репозиторий; папка уже игнорируется `.gitignore`.

## Точная следующая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
powershell -ExecutionPolicy Bypass -File .\scripts\setup-mpt-windows.ps1
```

Затем получить бесплатный Pexels API key и добавить в локальный `.env`:

```text
PEXELS_API_KEY=...
```

После этого:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\configure-mpt-windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-mpt-api.ps1
```

Проверить в браузере:

```text
http://127.0.0.1:8080/docs
```

Когда API поднят, в другом PowerShell из `D:\KiraS\VV_knopka`:

```powershell
.\.venv\Scripts\vv.exe render-ai 1
```

Ожидаемый output:

```text
runtime/ready_for_review/slot-01-ru-ai.mp4
```

Никакой автоматической публикации на YouTube на этом этапе нет.
