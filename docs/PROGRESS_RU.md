# VV_knopka — LIVE PROGRESS (RU)

Короткий оперативный статус. Подробный контекст и правила остаются в `AGENT.md` и `docs/PROJECT_HANDOFF_RU.md`.

Последнее обновление: **2026-08-28**.

## Подтверждено на ПК пользователя

- Project Python: `3.11.0`.
- `auto_publish = false`, publication gate = `PASS`.
- OpenAI/Pexels/Pixabay keys настроены локально в `.env`.
- MoneyPrinterTurbo v1.3.5 установлен, API работает на `127.0.0.1:8080`.
- После последних изменений локальный pytest пользователя: **16 passed in 0.15s**.

## Slot 1 — Russian AI Short: QUALITY PASS

Тема: «Почему осьминог меняет цвет во сне».

Основные исправления: final video вместо silent intermediate, Pexels+Pixabay+Luna relevance gate, duration fallback для узких тем, нормальный Cyrillic font, landscape blur-fill, no per-clip FadeIn.

После последнего quality render пользователь сообщил: **«Этот результат мне нравится»**.

Последний subtitle tuning после просмотра кадра:

- font size **52**;
- custom vertical position **74%**;
- stroke остаётся 2.2;
- font остаётся Windows Cyrillic local runtime copy.

## Slot 2 — Russian cats compilation

Цель: review-only монтаж с котиками.

Workflow:

```powershell
.\.venv\Scripts\vv.exe plan 2 --topic cats
.\.venv\Scripts\vv.exe render-animal 2
```

Автоматически: cat anchor -> Pexels+Pixabay -> Luna visible-cat gate -> provenance/license manifest -> 5-6 distinct cat clips -> FFmpeg ~30 sec montage.

Никаких bass/drop/impact/boom SFX. Source audio normalized; missing audio заменяется silence. Aspect mismatch получает 9:16 blur-fill.

Перед реальной публикацией всё равно нужен review editorial transformation / reused-content risk.

## Slot 3 — English AI Short: первый plan оказался stock-poor

Пользователь успешно выполнил:

```text
vv plan 3
```

Первый план выбрал `visual_anchor = "superb lyrebird"`.

`render-ai 3` безопасно остановился:

```text
Multi-source visual relevance gate found only 2/8 usable clips for visible anchor 'superb lyrebird'
Only 2 vision-approved unique sources are cached; need at least 3.
```

Это не renderer bug: редкий вид слишком плохо представлен в бесплатных Pexels/Pixabay для нашего review-first stock workflow.

### Исправление planner

Для автоматических AI slots без явного `--topic` planner теперь обязан выбирать broad stock-friendly subject из ограниченного списка (cat/dog/octopus/bee/ant/penguin/dolphin/elephant/horse/rabbit/fox/owl/parrot/turtle/snake/butterfly/spider/frog/duck/chicken).

Правила:

- не выбирать редкие species/subspecies/scientific names;
- factual claim должен действительно относиться к broad chosen animal;
- нельзя иллюстрировать rare-species fact generic footage;
- уже использованные visual anchors из предыдущих slot plans исключаются, пока есть другие варианты;
- explicit user `--topic` всё ещё имеет приоритет.

### Исправление stale material cache

Старый `ai_materials.json` теперь привязан к `visual_anchor`.

Если slot перегенерирован с другим животным:

- старый audit не переиспользуется;
- старое состояние «Pexels+Pixabay exhausted» не блокирует новый поиск;
- старые footage clips не могут попасть в новый ролик;
- новый anchor запускает новый stock search/vision review.

## Точная следующая точка

На ПК пользователя:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\vv.exe status
```

Для slot 3 **перегенерировать план**, потому что старый `superb lyrebird` намеренно выбрасываем:

```powershell
.\.venv\Scripts\vv.exe plan 3
Get-Content .\runtime\slots\03\plan.json -Raw
.\.venv\Scripts\vv.exe render-ai 3
```

Старый `ai_materials.json` удалять вручную не нужно — anchor-aware cache logic его проигнорирует и новый curator перезапишет audit.

Slot 2 можно запускать независимо:

```powershell
.\.venv\Scripts\vv.exe plan 2 --topic cats
.\.venv\Scripts\vv.exe render-animal 2
```

Ожидаемые outputs:

```text
runtime/ready_for_review/slot-02-ru-animals.mp4
runtime/ready_for_review/slot-03-en-ai.mp4
```

Не публиковать автоматически. Сначала human review обоих файлов.
