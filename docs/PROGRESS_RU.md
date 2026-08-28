# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила остаются в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-28**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish = false`, publication gate = `PASS`.
- OpenAI/Pexels keys настроены локально в `.env`.
- MoneyPrinterTurbo v1.3.5 установлен, API работает на `127.0.0.1:8080`.
- `vv plan 1` создан: русский Short «Почему осьминог меняет цвет во сне».
- Первый plan-вызов OpenAI стоил `$0.0051`; общий hard cap пилота `$10`.
- Первый MPT render завершился, но review = FAIL: скачивался silent `combined-1.mp4`, а Pexels подмешал fish/jellyfish/turtle/human-skin filler.
- Sound bug исправлен: VV_knopka теперь скачивает MPT `videos` (final output) и только fallback-ит на `combined_videos`.
- Pacing: 6 секунд на источник.

## Material relevance: что уже проверено

### Strict URL gate

Первый фикс требовал `octopus` в Pexels page slug. Он fail-closed с `2/8`: безопасно, но слишком низкий recall.

### Luna visual gate

Затем URL стал только metadata signal, а GPT-5.6 Luna начал смотреть Pexels preview images.

Локальный прогон пользователя:

```text
9 passed in 0.10s
OpenAI spent before vision run: $0.0051 / $10.00
RuntimeError: Pexels visual relevance gate found only 2/8 usable clips after reviewing 30 previews for visible anchor 'octopus'.
```

Вывод: visual gate работает, но **Pexels сам по себе недостаточен для этой темы**. Ослаблять confidence/relevance нельзя.

## Текущий дизайн: Pexels + Pixabay

В ветке `mvp/pilot-scaffold` добавлен multi-source fallback:

1. `visual_anchor=octopus` остаётся обязательным.
2. Уже одобренные и скачанные Pexels clips из `runtime/slots/01/ai_materials.json` переиспользуются как cache seed.
3. Если предыдущий audit уже просмотрел 30 Pexels previews, эти Pexels кандидаты **не проверяются повторно** и OpenAI budget на них повторно не тратится.
4. Недостающие clips ищутся через официальный Pixabay Video API.
5. Pixabay candidates также проходят тот же Luna visual gate, `accepted=true` и confidence >= `0.72`.
6. Pixabay metadata/tags — только дополнительный signal; решение остаётся визуальным.
7. При успехе 8 Pexels+Pixabay clips скачиваются в `MoneyPrinterTurbo/storage/local_videos` и передаются MPT как explicit local materials.
8. Provenance обоих providers сохраняется в `runtime/slots/01/ai_materials.json`.
9. Если Pexels + Pixabay всё равно не дают 8, pipeline снова FAILS CLOSED; filler footage запрещён.

Pixabay config: `pixabay_per_page=100`, максимум 40 preview-кандидатов на vision review. `.env.example` уже содержит `PIXABAY_API_KEY=`.

## Точная следующая точка

До следующего `render-ai 1` нужен бесплатный Pixabay API key. Добавить только локально:

```text
PIXABAY_API_KEY=...
```

Затем:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
.\.venv\Scripts\vv.exe render-ai 1
```

`vv plan 1` повторно НЕ запускать.

Успешный material stage должен вывести:

```text
Curated stock materials: 8
Material audit: D:\KiraS\VV_knopka\runtime\slots\01\ai_materials.json
MPT task: ...
```

После render проверить `runtime/ready_for_review/slot-01-ru-ai.mp4`:

- русская озвучка слышна;
- субтитры есть;
- каждый клип содержит реально видимого осьминога;
- нет human skin / random fish / jellyfish / turtle filler;
- pacing приемлемый.

Только после ручного PASS slot 1 переходить к slot 2. Автопубликация остаётся выключена.
