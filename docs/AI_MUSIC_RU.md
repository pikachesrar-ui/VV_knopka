# VV_knopka — AI background music (RU)

## Цель

Добавить в будущие long-run Shorts очень тихую приятную инструментальную музыку, не забивая:

- voiceover в AI facts;
- оригинальный звук cat clips;
- meow на black cards.

Музыка не генерируется заново для каждого ролика. Сначала создаётся небольшая локальная библиотека, затем VV_knopka детерминированно ротирует одобренные tracks с cooldown.

## Safety state

Production music по умолчанию выключена:

```toml
[music]
enabled = false
```

Это намеренно. Пока трек не был прослушан и явно promoted из `candidates`, он не может попасть в production rotation.

Структура:

```text
runtime/assets/music/
  candidates/          # generated, но ещё НЕ одобрены
    cute_01.wav
    ...
    generation.json
  curious_01.wav       # только approved tracks лежат прямо в music/
  calm_01.wav
  ...
```

`music_library.available_tracks()` читает только файлы непосредственно в `runtime/assets/music/`; подкаталог `candidates/` игнорируется.

## ACE-Step

Используется локальный open-source ACE-Step 1.5 через его REST API.

Официальный async API flow:

```text
POST /release_task
  -> task_id
POST /query_result
  -> status 0/1/2
GET /v1/audio?... 
  -> generated audio
```

VV_knopka использует instrumental mode (`lyrics=[Instrumental]`, `instrumental=true`), WAV output, один result за task и bounded duration.

Default local API URL:

```text
http://127.0.0.1:8001
```

Override при необходимости:

```text
ACESTEP_BASE_URL=http://127.0.0.1:8001
```

## Windows setup

После `git pull` и reinstall VV_knopka:

```powershell
cd D:\KiraS\VV_knopka
powershell -ExecutionPolicy Bypass -File .\scripts\setup-acestep-windows.ps1
```

Setup:

1. использует локальный `uv` helper;
2. клонирует официальный `ACE-Step/ACE-Step-1.5` в ignored `ACE-Step-1.5/`;
3. устанавливает Python 3.11 environment через `uv sync`;
4. создаёт local candidates directory.

Setup намеренно **не делает auto-update существующего ACE-Step checkout**, чтобы upstream не менялся неожиданно в production.

Первый запуск ACE-Step может скачивать model weights и занять заметное время/место.

## Generate initial candidates

Основной command:

```powershell
.\.venv\Scripts\vv-music.exe generate-library --count 8 --duration 45
```

`vv-music` сам попробует:

1. обнаружить уже запущенный ACE-Step API;
2. если API offline — поднять локальный `acestep-api`;
3. дождаться `/health`;
4. последовательно сгенерировать candidate WAVs;
5. скачать их в `runtime/assets/music/candidates/`;
6. записать generation manifest;
7. остановить только тот ACE-Step process, который VV_knopka запустил сам.

Preset library сейчас включает 8 вариантов:

- `cute_01`, `cute_02`;
- `playful_01`, `playful_02`;
- `curious_01`, `curious_02`;
- `calm_01`, `calm_02`.

Промпты специально запрещают vocals, heavy bass и dramatic drops.

## Status / list

```powershell
.\.venv\Scripts\vv-music.exe status
.\.venv\Scripts\vv-music.exe list
```

## Approval

После прослушивания выбранные кандидаты можно promoted в production library:

```powershell
.\.venv\Scripts\vv-music.exe approve curious_01.wav calm_02.wav cute_01.wav
```

Это только перемещает выбранные WAV из `candidates/` в approved root. Сам feature flag всё ещё остаётся выключенным.

Не включать `[music].enabled=true`, пока пользователь не подтвердил набор одобренных tracks.

## Production rotation

После включения:

- AI facts предпочитают `curious_*`, затем `calm_*`, `facts_*`, `generic_*`;
- cats предпочитают `cute_*`, затем `playful_*`, `calm_*`, `generic_*`;
- предыдущие tracks блокируются cooldown window;
- выбор остаётся deterministic;
- каждый slot сохраняет `music.json` с SHA256, track name, generator и disclosure state.

Default cooldown:

```toml
cooldown_shorts = 5
```

## Audio mix

Current target volumes:

```toml
ai_volume = 0.10
cat_volume = 0.07
ducking = true
```

Main audio всегда важнее BGM. При ducking музыка дополнительно приглушается под voice/source audio.

Когда local music enabled, встроенный random BGM MoneyPrinterTurbo мутится, чтобы две фоновые композиции не играли одновременно.

## YouTube disclosure

Если applied track отмечен как AI-generated, `music.json` сообщает это publication metadata, после чего uploader передаёт `containsSyntheticMedia=true` для конкретного видео.

Если AI music не применялась, сам факт использования AI в других production helpers не заставляет blanket-включать этот flag.

## First production experiment

После выбора библиотеки рекомендуется не сразу включать музыку во все видео, а провести небольшой comparison batch:

```text
music ON vs music OFF
```

Дальше сравнивать YouTube stats snapshots (views/likes/comments; при появлении retention data — retention) и оставить музыку только если она реально помогает или по крайней мере не ухудшает результат.
