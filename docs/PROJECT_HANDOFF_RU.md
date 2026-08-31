# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Рабочая ветка `mvp/pilot-scaffold`. Draft PR #1 остаётся **open/draft/unmerged** до явного решения пользователя.

## Цель
Автономный long-run pipeline:
`идея/факт -> validation -> render -> metadata -> YouTube upload -> verification -> statistics`.
TikTok пока не трогать.

## Реальный checkpoint — 2026-08-31
- frozen pilot slots 1–15 визуально принят и immutable;
- slots 1–11 опубликованы и `VERIFIED_PUBLIC`;
- перед пересборкой slot 16 локально было 16 ready Shorts, pending slots 12–16;
- OpenAI ledger `$0.1885/$10`;
- scheduler `VV Knopka Long Run` реально работает по 01:30/03:30/05:30 MSK;
- unattended run auto-uploaded slot 11, затем корректно обработал YouTube `uploadLimitExceeded` через cooldown/defer.

## Cat slot 16 reuse incident — diagnosed
Пользователь заметил, что cat episode #008 / slot 16 повторяет много котов из #001.
Локальные audits подтвердили:

```text
slot 16 final sources: 6
fresh: 1
cooled-down reused: 5
all 5 reused clips came from slot 2 / cat #001
cooled_history_local_fallback: enabled
seeded_sources: 8
source_slots: 2,4
```

`source_reuse_audit.json` показывал 5 cooled overlaps и всё равно `passed=true`, потому что старая gate ограничивала recent-window repeats, но не концентрацию cooled history.

### Исправленная policy
```toml
[long_run]
cat_source_cooldown_episodes = 5
cat_cooled_reuse_max_sources = 2
cat_cooled_reuse_max_per_history_episode = 1
```

Теперь:
- fresh discovery всегда первая;
- предыдущие 5 cat episodes защищены;
- cooled fallback максимум 2 клипа на новый Short;
- максимум 1 клип из одного старого episode;
- fallback идёт newest-cooled-first, а не начинает с самого старого #001;
- если после fresh + bounded fallback не достигается minimum usable source count, генерация fail closed;
- audit пишет `cooled_reuse_by_history_slot` и отдельно валидирует total/per-episode limits.

Существующий slot 16 ещё не опубликован и должен быть архивирован/пересобран до upload turn. Slots 1–15 не трогать.

## AI music — approved and enabled for future long-run
ACE-Step real local path на RTX 3060 полностью подтверждён. Все 8 initial tracks одобрены и promoted в local approved library.

Preview results:
- AI mix нормальный при `ai_volume=0.10`, ducking ON;
- первый cat mix был слишком тихим;
- cat v2 принят при `cat_volume=0.11`, cat ducking OFF.

Current target config:
```toml
[music]
enabled = true
ai_volume = 0.10
cat_volume = 0.11
ai_ducking = true
cat_ducking = false
```

Для rebuilt slot 16 использовать `vv longrun-next`, а не только `render-animal`, чтобы conveyor после render применил reviewed music, записал `music.json` и пересобрал final upload metadata / synthetic-media disclosure.

## YouTube v2
Реализовано и проверено на реальном канале:
- metadata v2;
- hashtags/CTA/tags;
- conditional `containsSyntheticMedia`;
- graceful upload-limit cooldown;
- `vv-youtube verify`;
- `vv-youtube stats` + history;
- `vv-youtube report` age-aware metrics.

Первый stats sample очень маленький — не оптимизировать policy по нему.

## AI fact-check / MPT
- AI plan fail-closed через bounded evidence check;
- FAIL = no render/no publish;
- стоимость входит в `$10` ledger;
- MPT умеет auto-start/wait/stop через conveyor.

## Future comment feedback
`docs/YOUTUBE_COMMENT_FEEDBACK_RU.md`: в будущем собирать comments, отдельно классифицировать music-topic и sentiment, реагировать только на устойчивый сигнал по нескольким комментариям/videos. First stage recommendation-only.

## Safety
- `$10` OpenAI hard cap;
- никаких новых платных providers без explicit approval;
- secrets runtime-only;
- source/provenance/audio/geometry/vision gates fail closed;
- PR #1 не merge автоматически.

## Immediate continuation
1. дождаться green CI после anti-remake + music enable;
2. user local `git pull`;
3. убедиться, что slot 16 не имеет YouTube receipt;
4. безопасно архивировать старый `runtime/slots/16` + `slot-16-en-animals.mp4` + sidecar;
5. запустить `vv longrun-next` — он должен снова выбрать slot 16;
6. проверить `source_reuse_audit.json`, `animal_audio_sources.json`, `music.json` и preview;
7. после принятия нового slot 16 продолжать backlog-first uploads;
8. slot 17 не генерировать, пока pending backlog не станет 0.
