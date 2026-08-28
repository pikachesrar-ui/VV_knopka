# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила остаются в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-28**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish = false`, publication gate = `PASS`.
- OpenAI/Pexels/Pixabay keys настроены локально в `.env`.
- MoneyPrinterTurbo v1.3.5 установлен, API работает на `127.0.0.1:8080`.
- Последний известный OpenAI ledger перед новыми слотами: **`$0.0104 / $10.00`**.

## Slot 1 — Russian AI Short: QUALITY PASS

Тема: «Почему осьминог меняет цвет во сне».

История исправлений:

- первый render скачивал silent intermediate `combined_videos` вместо final `videos` — исправлено;
- blind Pexels selection подмешивал fish/jellyfish/turtle/human skin — заменено на Pexels + Pixabay + GPT-5.6 Luna visual gate;
- 8 unique files оказались завышенным требованием — введён duration-based fallback минимум 3 approved sources / 36 sec reusable footage;
- MPT curated mode использует разные непересекающиеся segments длинных approved sources;
- CJK subtitle font заменён локальным Windows Cyrillic font;
- subtitle size/position/stroke улучшены;
- landscape stock получает 9:16 blur-fill вместо black bars;
- per-clip FadeIn выключен, потому что это был fade-from-black, а не crossfade.

После этих доработок пользователь сообщил: **«Этот результат мне нравится»**. Поэтому slot 1 считается manual **QUALITY PASS**.

## Следующий эксперимент: slot 2 — Russian cats compilation

Пользователь попросил теперь попробовать видео с котиками.

Новый workflow:

1. `vv plan 2 --topic cats` — создаёт русский editorial concept, visual_anchor обязан быть `cat`.
2. `vv render-animal 2` при отсутствии `sources.json` сам:
   - ищет licensed stock через Pexels + Pixabay;
   - Luna visual gate принимает только кадры, где реально видна кошка;
   - требует минимум 5 unique approved clips;
   - берёт до 6 источников;
   - записывает `runtime/slots/02/sources.json` с provider/source URL/creator/license/commercial-use flag;
   - затем запускает локальный FFmpeg animal renderer.
3. Animal target: 6 clips × ~5 sec ≈ 30 sec.
4. Никаких bass/drop/impact/boom SFX.
5. Source audio нормализуется. Если stock clip без audio track, pipeline автоматически добавляет silence вместо FAIL.
6. Visual layout для каждого клипа — 1080x1920 blur-fill + полный sharp source в центре, чтобы не было black bars и жёсткого crop.
7. Переходы — только tiny visual/audio fades; transition SFX отсутствуют.

Это **review-only montage-style test**. Перед публикацией проверить, хватает ли оригинального editorial layer для YouTube reused-content policy; если нет, следующим шагом добавить voiceover/running joke/on-screen commentary. Автопубликация остаётся выключенной.

Лицензии перепроверены 2026-08-28: Pexels License разрешает commercial use; Pixabay Content License разрешает commercial/non-commercial use subject to its restrictions. Provenance всё равно обязателен.

## Параллельный эксперимент: slot 3 — first English AI Short

Slot 3 по frozen manifest = `ai_short`, language `en`.

Workflow:

```powershell
.\.venv\Scripts\vv.exe plan 3
.\.venv\Scripts\vv.exe render-ai 3
```

Он использует тот же quality stack, что уже прошёл slot 1: Terra plan -> Pexels/Pixabay -> Luna visual gate -> local curated MPT -> English Edge TTS -> subtitles -> review MP4.

## Точная следующая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status

.\.venv\Scripts\vv.exe plan 2 --topic cats
.\.venv\Scripts\vv.exe render-animal 2

.\.venv\Scripts\vv.exe plan 3
.\.venv\Scripts\vv.exe render-ai 3

.\.venv\Scripts\vv.exe status
```

Ожидаемые review outputs:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
runtime/ready_for_review/slot-03-en-ai.mp4
```

Не публиковать автоматически. Сначала human review обоих файлов.
