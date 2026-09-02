# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Рабочая ветка `mvp/pilot-scaffold`. Draft PR #1 остаётся **open/draft/unmerged** до явного решения пользователя.

## Цель
Автономный long-run pipeline:
`идея/факт -> validation -> render -> metadata -> YouTube upload -> verification -> statistics`.
TikTok пока не трогать.

## Реальный checkpoint — 2026-09-02
- frozen pilot slots 1–15 визуально принят; MP4 slots 1–15 не ререндерить;
- slots 1–11 опубликованы и `VERIFIED_PUBLIC`;
- slots 1–11 metadata backfill завершён и финальный dry-run был UNCHANGED;
- slots 12–15 были upgraded locally to metadata v2 before first upload;
- replacement slot 16 прошёл source/music/metadata audits;
- pending сейчас: slots 12–16, ровно 5 uploads;
- slot 17 ещё не создан, что корректно при backlog-first;
- next generation after pending=0: slot 17 AI EN;
- OpenAI ledger последний показанный `$0.2024/$10`;
- scheduler `VV Knopka Long Run`: 01:30/03:30/05:30 MSK.

## Scheduler incident — 2026-09-02
Реальные Windows логи показали:
- 2026-08-31 01:30 slot 11 успешно uploaded public;
- 2026-08-31 03:30 slot 12 получил ожидаемый `uploadLimitExceeded`, был создан persisted cooldown;
- после истечения cooldown все последующие unattended triggers успешно делали `verify` slots 1–11, затем падали сразу после verify с первой строкой Python traceback;
- backlog не менялся: slots 12–16 остались pending, slot 17 не генерировался.

Manual `vv-youtube stats` 2026-09-02 успешно получил и сохранил статистику для 11 videos. Snapshot содержит Unicode titles с кириллицей и emoji (`😹`). Следовательно API/statistics path исправен; проблема локализована в Windows Task Scheduler/native stdout-stderr encoding/PowerShell pipeline handling.

Исправление в ветке:
- `scripts/run-longrun-task.ps1` теперь force-ит `PYTHONIOENCODING=utf-8` и `PYTHONUTF8=1`;
- PowerShell output encoding выставляется UTF-8 where possible;
- redirected native stderr собирается при временном `ErrorActionPreference=Continue`, после чего решение принимается по реальному `$LASTEXITCODE`;
- stats остаётся best-effort: даже если stats/output упал, scheduler пишет WARN и продолжает backlog publication;
- verify/pending/upload/generation gates остаются fail-closed.

Добавлен regression test `tests/test_scheduler_runner.py`.

ВАЖНО: installed Windows task делает **no git pull**. Поэтому перед следующей локальной проверкой пользователь должен получить latest `mvp/pilot-scaffold` через `git pull --ff-only`. Никакого reinstall task не требуется: task указывает на тот же `scripts/run-longrun-task.ps1`, поэтому после pull автоматически использует исправленный файл.

## First real stats sample — only telemetry
Manual snapshot 2026-09-02:
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

### Ещё не опубликованные slots 12–15 — DONE
Пользователь выполнил:
```powershell
vv-youtube upgrade-pending-metadata --slots 12-15 --apply
```

Реальный результат:
```text
APPLY summary: 4 pending sidecars | changed=4 | applied=4
```

Команда:
- работает только с ready `.upload.json` без YouTube receipt;
- добавляет/merge-ит hidden `youtube_tags`;
- дописывает отсутствующие hashtags в `youtube_description`;
- записывает `youtube_hashtags` и `metadata_version=2`;
- сохраняет all unrelated sidecar fields;
- не трогает MP4;
- делает backup исходного sidecar в `runtime/youtube/pending-metadata-backups/`;
- published slots автоматически пропускает.

## Autonomous scheduler behavior
Каждый trigger:
1. status;
2. verify receipts;
3. best-effort stats;
4. если pending > 0 — upload ровно одного oldest и выход;
5. если pending == 0 — `longrun-next`;
6. render одного следующего slot;
7. upload только нового newest slot.

Таким образом backlog не растёт. Когда текущие готовые ролики закончатся, pipeline сам начнёт генерировать новые.

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
1. pull latest `mvp/pilot-scaffold` locally so the installed scheduler sees the UTF-8 fix;
2. verify one real scheduler run reaches `youtube-stats`, then `youtube-pending`, then uploads oldest pending slot 12;
3. leave scheduler autonomous after that;
4. it drains 12–16 oldest-first;
5. after pending=0 generates slot 17 AI EN automatically;
6. do not manually generate slot 17 while backlog remains.
