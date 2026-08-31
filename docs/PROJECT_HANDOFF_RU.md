# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Рабочая ветка `mvp/pilot-scaffold`. Draft PR #1 остаётся **open/draft/unmerged** до явного решения пользователя.

## Цель
Автономный long-run pipeline:
`идея/факт -> validation -> render -> metadata -> YouTube upload -> verification -> statistics`.
TikTok пока не трогать.

## Реальный checkpoint — 2026-09-01
- frozen pilot slots 1–15 визуально принят; MP4 slots 1–15 не ререндерить;
- slots 1–11 опубликованы и `VERIFIED_PUBLIC`;
- пользователь реально применил metadata backfill к slots 1–11;
- финальная проверка backfill: **все 1–11 UNCHANGED**, то есть tags/hashtags уже присутствуют;
- replacement slot 16 успешно пересобран и прошёл source/music/metadata audits;
- active pending queue до следующего scheduler-run: slots 12–16;
- next generation after pending=0: slot 17 AI EN;
- OpenAI ledger последний показанный `$0.1885/$10`;
- scheduler `VV Knopka Long Run`: 01:30/03:30/05:30 MSK, backlog-first.

Плохой первый slot 16 безопасно архивирован в:
`runtime/backups/slot-16-before-rebuild-20260831-231504`.

## YouTube discovery metadata
### Уже опубликованные slots 1–11 — DONE
Пользователь выполнил `auth-metadata` и `backfill-metadata --slots 1-11 --apply`.

Реальный итог:
- 11/11 обновлены;
- slot 7 имел краткую read-after-write задержку YouTube, затем тоже стал UNCHANGED;
- final dry-run по каждому slot 1–11: tags none, hashtags none to add.

Backfill не меняет video bytes, URL, views, privacy/status или title.

### Ещё не опубликованные slots 12–15 — final one-time local upgrade
Добавлена отдельная команда:
```powershell
vv-youtube upgrade-pending-metadata --slots 12-15
vv-youtube upgrade-pending-metadata --slots 12-15 --apply
```

Она:
- работает только с ready `.upload.json` без YouTube receipt;
- добавляет/merge-ит hidden `youtube_tags`;
- дописывает отсутствующие hashtags в `youtube_description`;
- записывает `youtube_hashtags` и `metadata_version=2`;
- сохраняет все unrelated sidecar fields;
- вообще не трогает MP4;
- делает backup исходного sidecar в `runtime/youtube/pending-metadata-backups/`;
- пишет audit `runtime/youtube/pending-metadata-upgrade-latest.json`;
- published slots автоматически пропускает.

Если scheduler успеет опубликовать один из 12–15 раньше upgrade, этот slot нужно просто прогнать через уже проверенный `backfill-metadata` как published target.

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
1. дождаться/check CI для pending-sidecar upgrade;
2. `git pull`;
3. dry-run `upgrade-pending-metadata --slots 12-15`;
4. apply;
5. повторить dry-run, ожидая UNCHANGED для всех still-pending slots;
6. после этого оставить scheduler работать автономно несколько дней;
7. не делать manual slot17 пока backlog не обнулится.
