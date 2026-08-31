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
- финальная проверка backfill: **все 1–11 UNCHANGED**, tags/hashtags уже присутствуют;
- slots 12–15 на момент upgrade ещё не были опубликованы;
- user real-run `upgrade-pending-metadata --slots 12-15 --apply`: **4/4 pending sidecars UPDATED**;
- сразу после этого `backfill-metadata --slots 12-15 --apply` вернул `No uploaded receipt videos matched`, подтверждая, что 12–15 всё ещё pending и уйдут на YouTube уже с новой metadata с первой загрузки;
- replacement slot 16 успешно пересобран и прошёл source/music/metadata audits;
- active pending queue на этом checkpoint: slots 12–16;
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

### Ещё не опубликованные slots 12–15 — DONE
Пользователь сначала проверил dry-run. Предложенный diff был нормальным:
- slot 12 cats: cat discovery tags/hashtags;
- slot 13 dog: Dogs/DogFacts/AnimalCuriosities/NatureFacts/shorts + generic animal tags;
- slot 14 cats: cat discovery tags/hashtags;
- slot 15 elephants: Elephants/AnimalFacts/NatureCuriosities/Wildlife/AnimalBehavior + generic animal tags.

Затем пользователь выполнил:
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
- вообще не трогает MP4;
- делает backup исходного sidecar в `runtime/youtube/pending-metadata-backups/`;
- пишет audit `runtime/youtube/pending-metadata-upgrade-latest.json`;
- published slots автоматически пропускает.

Сразу после apply пользователь также выполнил `backfill-metadata --slots 12-15 --apply`; receipts не нашлись. Значит ни один из 12–15 не успел опубликоваться до upgrade.

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
1. metadata cleanup block закрыт: published 1–11 и pending 12–15 готовы;
2. оставить scheduler автономно работать несколько дней;
3. он drains 12–16 oldest-first;
4. после pending=0 сам генерирует slot 17 AI EN;
5. далее long-run продолжается автоматически до safety/failure gate или исчерпания `$10` generation budget;
6. не делать manual slot17 пока backlog не обнулится.
