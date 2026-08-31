# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Рабочая ветка `mvp/pilot-scaffold`. Draft PR #1 остаётся **open/draft/unmerged** до явного решения пользователя.

## Цель
Автономный long-run pipeline:
`идея/факт -> validation -> render -> metadata -> YouTube upload -> verification -> statistics`.
TikTok пока не трогать.

## Реальный checkpoint — 2026-09-01
- frozen pilot slots 1–15 визуально принят и immutable;
- slots 1–11 опубликованы и `VERIFIED_PUBLIC`;
- replacement slot 16 успешно пересобран;
- ready локально снова **16**;
- active pending queue: **slots 12–16 (5)**;
- next generation after pending=0: **slot 17 AI EN**;
- OpenAI ledger последний показанный `$0.1885/$10`;
- scheduler `VV Knopka Long Run` реально работает по 01:30/03:30/05:30 MSK;
- unattended run auto-uploaded slot 11, затем корректно обработал YouTube `uploadLimitExceeded` через cooldown/defer.

Плохой первый slot 16 / cat #008 безопасно архивирован в:
`runtime/backups/slot-16-before-rebuild-20260831-231504`.
Он не имеет YouTube receipt и больше не находится в active ready queue.

## Cat slot 16 reuse incident — fixed and real-validated
Первый slot 16 имел:
```text
final sources: 6
fresh: 1
cooled reused: 5
all 5 reused clips from slot 2 / cat #001
```

Исправленная anti-remake policy:
```toml
[long_run]
cat_source_cooldown_episodes = 5
cat_cooled_reuse_max_sources = 2
cat_cooled_reuse_max_per_history_episode = 1
```

Теперь:
- fresh discovery первая;
- previous 5 cat episodes защищены;
- cooled fallback максимум 2 clips total;
- максимум 1 clip из одного старого episode;
- newest-cooled-first;
- при нехватке fresh + bounded fallback generation fail closed;
- `source_reuse_audit.json` валидирует total/per-episode concentration.

### Реальный replacement slot 16
Новый `vv longrun-next` завершился успешно.

Final source composition:
```text
6 unique sources
4 fresh Pexels
2 cooled total
cooled slot 2: 1
cooled slot 4: 1
protected-window overlap: 0
source reuse audit: PASS
```

Fresh IDs:
`4427731`, `10467051`, `14326398`, `14927525`.

Cooled IDs:
- `10358235` from slot 2;
- `5335581` from slot 4.

Таким образом новая #008 больше не является near-remake #001.

## Cat source v6 — audio first, vision second
`vv` маршрутизирует cat sourcing через `animal_audio_sources_v6`.

Policy:
- remote audio-stream check до Luna;
- FFmpeg mean-volume check до Luna, если stream подтверждён;
- confirmed-silent stock не расходует vision review;
- unmeasurable fresh CDN candidates допускаются только bounded tail;
- remote cooled history исключена из discovery;
- old clips приходят только через explicit bounded local fallback;
- retry не может stack-нуть второй cooled batch;
- failure diagnostics сохраняются;
- provider availability записывается boolean-ами, без секретов.

Config:
```toml
[animal]
remote_audio_probe_seconds = 6.0
remote_audio_unknown_max_candidates = 12
```

Real replacement audit:
```text
PEXELS_API_KEY present: true
PIXABAY_API_KEY present: true
reused_audio_sources: 3
Pexels candidates: 54
vision reviewed: 54
vision approved: 51
new Pexels audio accepted: 3
Pixabay candidates: 0
```

Pixabay не понадобился, потому что Pexels после recovery/accepted fresh clips довёл pool до target раньше fallback provider.
`vision_reviewed=54` всё ещё выглядит дороже, чем хотелось бы; это отдельная efficiency optimization, не blocker корректности slot 16.

Latest green code checkpoint для v6: `6e94b5d54309955a10ae2c499bd36e3db91f4320`, Ubuntu PASS + Windows PASS, **160 tests passed**.

## AI music — approved, enabled and real-applied
ACE-Step real local path на RTX 3060 подтверждён. Все 8 initial tracks одобрены и promoted.

Accepted profiles:
- AI `0.10` + ducking ON;
- cats `0.11` + cat ducking OFF.

Current config:
```toml
[music]
enabled = true
ai_volume = 0.10
cat_volume = 0.11
ai_ducking = true
cat_ducking = false
```

Replacement slot 16 music audit:
```text
track_name: curious_02.wav
applied_to_video: true
music_volume_applied: 0.11
ducking: false
```

Final upload metadata:
```text
slot: 16
pipeline: animal_compilation
language: en
metadata_version: 2
contains_synthetic_media: true
```

## YouTube v2
Реализовано и проверено на реальном канале:
- metadata v2;
- hashtags/CTA/tags;
- conditional `containsSyntheticMedia`;
- graceful upload-limit cooldown;
- `vv-youtube verify`;
- `vv-youtube stats` + history;
- `vv-youtube report` age-aware metrics.

Первый stats sample маленький — не оптимизировать content policy по нему.

## AI fact-check / MPT
- AI plan fail-closed через bounded evidence check;
- FAIL = no render/no publish;
- стоимость входит в `$10` ledger;
- MPT умеет auto-start/wait/stop через conveyor.

## Future comment feedback
`docs/YOUTUBE_COMMENT_FEEDBACK_RU.md`: позже собирать comments, отдельно классифицировать music-topic и sentiment, реагировать только на устойчивый сигнал по нескольким комментариям/videos. First stage recommendation-only.

## Safety
- `$10` OpenAI hard cap;
- никаких новых платных providers без explicit approval;
- secrets runtime-only;
- source/provenance/audio/geometry/vision gates fail closed;
- PR #1 не merge автоматически.

## Immediate continuation
1. corrected slot 16 оставить в pending queue;
2. scheduler drains slots 12–16 oldest-first;
3. slot 17 не генерировать пока pending != 0;
4. после полного drain проверить slot 17 AI EN end-to-end;
5. позже уменьшить число Luna reviews на каждый реально audible fresh cat clip без ослабления quality gates.
