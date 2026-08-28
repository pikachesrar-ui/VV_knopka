# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила — в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-29**.

## Подтверждённая среда

- Windows, project Python `3.11.0`.
- `auto_publish=false`.
- OpenAI/Pexels/Pixabay keys локально в `.env`.
- MoneyPrinterTurbo v1.3.5 установлен локально, API `127.0.0.1:8080`.
- Последний пользовательский ledger: **$0.0268 / $10.00**.

## Slot 1 — Russian AI Short: QUALITY PASS

Тема: «Почему осьминог меняет цвет во сне».

Подтверждено пользователем: итоговая версия нравится.

Зафиксированные quality-настройки:

- final MPT video, не silent intermediate;
- Pexels + Pixabay + Luna visual relevance gate;
- duration fallback для узких stock-тем;
- 9:16 blur-fill;
- Windows Cyrillic font;
- subtitle size `52`;
- subtitle custom position `74%`;
- MPT per-clip FadeIn выключен.

## Slot 2 — Russian cats compilation: v1 REVIEW FAIL, v2 в работе

Первая компиляция успешно отрендерилась, но пользователь отметил:

- фактически нет слышимого звука;
- показываются случайные первые моменты клипов;
- ролик скучный;
- пользователь хочет приятный `meow` на переходах вместо неприятного bass hit.

Лог подтвердил первопричину тишины: большинство выбранных stock clips не имели audio stream; старый renderer подставлял `anullsrc`, поэтому финальный AAC был почти полностью silent.

### Cat montage v2

Реализовано:

1. `sources.json` переиспользуется, заново искать котов не нужно.
2. Для каждого source clip строятся до 4 candidate windows по всей длине.
3. На каждый candidate создаётся 3-frame contact sheet.
4. GPT-5.6 Luna выбирает лучший action/cute/funny момент, пишет короткую подпись и задаёт порядок клипов.
5. Renderer использует выбранный `start`, а не первые 5 секунд.
6. Сохраняется оригинальный source audio, если он есть.
7. На весь ролик добавляется тихий процедурный playful BGM.
8. На каждом cut добавляется короткий процедурный soft meow (3 pitch variants).
9. Никаких bass/drop/impact/boom SFX.
10. Короткая caption выводится поверх каждого highlight.

### Реальный FAIL после первой попытки v2

Пользователь выполнил pull/test/render и получил:

```text
1 failed, 21 passed
publication gate: FAIL
OpenAI spent: $0.0268 / $10.00
HTTP 403 Forbidden /v1/responses
```

Причины разделены:

- publication gate FAIL был нашим config bug: глобальный `[audio].transition_sfx` ошибочно поменяли с `none` на `soft_meow`;
- 403 появился на новом большом highlight vision request с множеством локальных Base64 contact sheets.

### Исправления 2026-08-29

- глобальный `[audio].transition_sfx` снова **`none`**;
- animal-only `[animal].transition_sfx = "soft_meow"`;
- старый publication gate не ослаблялся;
- highlight contact sheets уменьшены, чтобы снизить Base64 payload;
- основной one-request highlight review сохранён;
- если основной request получает HTTP 403, код автоматически переключается на per-clip fallback: максимум 4 маленьких images/request;
- если даже per-clip fallback получает 403, CLI выводит безопасный `message/type/code/param` из OpenAI error body, не показывая API key;
- failed 403 не записывается в usage ledger как успешный inference.

OpenAI docs на 2026-08-29 подтверждают, что Responses API поддерживает Base64 image input и multiple images; GPT-5.6 поддерживает image input. Поэтому формат не является запрещённым сам по себе.

## Slot 3 — English AI Short

Первый plan выбрал stock-poor `superb lyrebird` и был fail-closed из-за только 2 approved sources. Planner после этого ограничен broad stock-friendly anchors, stale stock cache стал anchor-aware.

Пользователь решил пока остановить работу над English slot и сначала довести котиков.

## Точная следующая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-animal 2
```

`plan 2` заново НЕ запускать. `sources.json` НЕ удалять.

Если render успешно создаст `highlights.json`, затем:

```powershell
.\.venv\Scripts\vv.exe status
Get-Content .\runtime\slots\02\highlights.json -Raw
```

Review output:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
```

Проверить глазами/на слух: качество выбранных моментов, captions, BGM volume, synthetic meow quality, source audio.

Автопубликация остаётся запрещённой до human review.
