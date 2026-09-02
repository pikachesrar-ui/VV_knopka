# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Рабочая ветка `mvp/pilot-scaffold`. Draft PR #1 остаётся **open/draft/unmerged** до явного решения пользователя.

## Цель
Автономный long-run pipeline:
`идея/факт -> validation -> render -> metadata -> YouTube upload -> verification -> statistics`.
TikTok пока не трогать.

## Реальный checkpoint — 2026-09-02
- frozen pilot slots 1–15 визуально принят; MP4 slots 1–15 не ререндерить;
- slots 1–12 опубликованы; slots 1–11 были `VERIFIED_PUBLIC` до последнего upload, slot 12 успешно загружен `public` в реальном scheduler run 2026-09-02 03:35 MSK;
- slots 1–11 metadata backfill завершён и финальный dry-run был UNCHANGED;
- slots 12–15 были upgraded locally to metadata v2 before first upload;
- replacement slot 16 прошёл source/music/metadata audits;
- pending после успешного recovery run: slots 13–16, ровно 4 uploads;
- slot 17 ещё не создан, что корректно при backlog-first;
- next generation after pending=0: slot 17 AI EN;
- OpenAI ledger последний показанный `$0.2024/$10`;
- scheduler `VV Knopka Long Run`: 01:30/03:30/05:30 MSK.

Slot 12 real upload after fix:
`https://www.youtube.com/watch?v=nrGanPLeVps`
requested=`public`, actual=`public`.

## Scheduler incident — 2026-09-02 — REAL FIX VALIDATED
Реальные Windows логи показали:
- 2026-08-31 01:30 slot 11 успешно uploaded public;
- 2026-08-31 03:30 slot 12 получил ожидаемый `uploadLimitExceeded`, был создан persisted cooldown;
- после истечения cooldown unattended triggers успешно делали `verify` slots 1–11, затем падали сразу после verify с первой строкой Python traceback;
- backlog не менялся: slots 12–16 оставались pending, slot 17 не генерировался.

Manual `vv-youtube stats` 2026-09-02 успешно получил и сохранил статистику для 11 videos. Snapshot содержал Unicode titles с кириллицей и emoji (`😹`). Проблема была локализована в Windows Task Scheduler/native stdout-stderr encoding/PowerShell pipeline handling.

Исправление в ветке:
- `scripts/run-longrun-task.ps1` force-ит `PYTHONIOENCODING=utf-8` и `PYTHONUTF8=1`;
- PowerShell output encoding выставляется UTF-8 where possible;
- redirected native stderr собирается при временном `ErrorActionPreference=Continue`, после чего решение принимается по реальному `$LASTEXITCODE`;
- stats остаётся best-effort: даже если stats/output упал, scheduler пишет WARN и продолжает backlog publication;
- verify/pending/upload/generation gates остаются fail-closed.

Regression test: `tests/test_scheduler_runner.py`.

Реальная валидация после локального `git pull --ff-only`:
```text
2026-09-02 03:34:54 START
verify slots 1–11: VERIFIED_PUBLIC
stats: SUCCESS, 11 videos
pending before: 5
youtube-backlog: UPLOADED slot 12 ... requested=public actual=public
pending after: 4
BACKLOG: handled one pending upload; 4 remain
```
То есть incident закрыт: scheduler снова проходит observability и реально drains backlog oldest-first.

В одном scheduler-log title slot 10 emoji отобразился как replacement glyph (`�`), но это cosmetic log rendering only: процесс не упал, stats snapshot и upload продолжились. Не считать это publication blocker.

## First real stats sample — only telemetry
Snapshot 2026-09-02 перед slot 12 upload:
```text
slot 1: 0 views
slot 2: 6
slot 3: 2
slot 4: 1
slot 5: 18
slot 6: 2
slot 7: 1
slot 8: 1
slot 9: 1
slot 10: 3
slot 11: 8
```
Do not optimize content strategy from this tiny/young sample.

## YouTube discovery metadata
### Уже опубликованные slots 1–11 — DONE
Пользователь выполнил `auth-metadata` и `backfill-metadata --slots 1-11 --apply`.

Реальный итог:
- 11/11 обновлены;
- slot 7 имел краткую read-after-write задержку YouTube, затем тоже стал UNCHANGED;
- final dry-run по каждому slot 1–11: tags none, hashtags none to add.

Backfill не меняет video bytes, URL, views, privacy/status или title.

### Legacy pending slots 12–15 — metadata upgrade DONE
Пользователь выполнил:
```powershell
vv-youtube upgrade-pending-metadata --slots 12-15 --apply
```

Реальный результат:
```text
APPLY summary: 4 pending sidecars | changed=4 | applied=4
```

Команда изменила только sidecars, сохранила MP4 bytes и подготовила metadata v2 до первой публикации. Slot 12 уже был успешно опубликован scheduler после этого upgrade; slots 13–15 остаются в pending queue вместе со slot 16.

## Autonomous scheduler behavior
Каждый trigger:
1. status;
2. verify receipts;
3. best-effort stats;
4. если pending > 0 — upload ровно одного oldest и выход;
5. если pending == 0 — `longrun-next`;
6. render одного следующего slot;
7. upload только нового newest slot.

Текущий ожидаемый drain после recovery:
`13 -> 14 -> 15 -> 16`, затем pending=0 и automatic slot 17 AI EN.

AI slots:
- план + fact-check;
- MPT auto-start/wait/render/stop-own-process;
- ACE-Step approved music;
- metadata v2 + tags/hashtags;
- YouTube upload.

Cat slots:
- fresh stock first;
- audio/geometry/provenance/vision gates;
- anti-repeat policy;
- FFmpeg render;
- ACE-Step approved music;
- metadata v2 + tags/hashtags;
- YouTube upload.

OpenAI generation hard cap = `$10`; при достижении cap новые generation attempts fail closed. Existing pending uploads могут продолжить выгружаться, потому что backlog обрабатывается до generation.

## Cat slot 16 incident — fixed
Original #008: 5/6 clips reused from #001.
Current policy:
```toml
cat_source_cooldown_episodes = 5
cat_cooled_reuse_max_sources = 2
cat_cooled_reuse_max_per_history_episode = 1
```

Replacement #008:
```text
6 unique
4 fresh
2 cooled total
1 from slot 2
1 from slot 4
protected-window overlap: 0
source reuse audit: PASS
```

## Cat source v6
Audio-first / fail-closed source pipeline is active.
Real replacement run:
```text
Pexels candidates: 54
vision reviewed: 54
vision approved: 51
new Pexels audio accepted: 3
Pixabay candidates: 0
```
Later optimization target: reduce Luna reviews per accepted fresh audible clip without weakening gates.

## Music
All 8 local ACE-Step tracks approved.
Production:
```toml
[music]
enabled = true
ai_volume = 0.10
cat_volume = 0.11
ai_ducking = true
cat_ducking = false
```
Replacement slot 16 used `curious_02.wav`, volume 0.11, ducking false.

## Safety
- `$10` OpenAI hard cap;
- no new paid providers without explicit approval;
- secrets runtime-only;
- source/provenance/audio/geometry/vision/fact-check gates fail closed;
- Draft PR #1 не merge автоматически;
- TikTok out of current scope.

## Immediate continuation
1. не делать manual upload/generation без новой ошибки;
2. оставить scheduler автономно drains slots 13–16 oldest-first;
3. после pending=0 он должен автоматически создать slot 17 AI EN и затем загрузить его;
4. через несколько triggers проверить receipts/logs/OpenAI ledger/stats;
5. не merge Draft PR #1 без явной команды пользователя.
