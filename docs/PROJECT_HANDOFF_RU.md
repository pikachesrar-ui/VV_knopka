# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Рабочая ветка `mvp/pilot-scaffold`. Draft PR #1 остаётся **open/draft/unmerged** до явного решения пользователя.

## Цель
Автономный long-run pipeline:
`идея/факт -> validation -> render -> metadata -> YouTube upload -> verification -> statistics`.
TikTok пока не трогать.

## Реальный checkpoint — 2026-09-01
- frozen pilot slots 1–15 визуально принят и immutable;
- slots 1–11 опубликованы и `VERIFIED_PUBLIC`;
- OpenAI ledger последний показанный `$0.1885/$10`;
- scheduler `VV Knopka Long Run` реально работает по 01:30/03:30/05:30 MSK;
- unattended run auto-uploaded slot 11, затем корректно обработал YouTube `uploadLimitExceeded` через cooldown/defer.

Плохой, но ещё не опубликованный slot 16 / cat #008 был безопасно архивирован в:
`runtime/backups/slot-16-before-rebuild-20260831-231504`.
В active ready queue после этого остаются slots 12–15; replacement slot 16 снова является следующим long-run generation target.

## Cat slot 16 reuse incident — diagnosed
Первый slot 16 повторял почти весь первый кошачий выпуск:

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

Теперь максимум два old clips total и максимум один из одного старого episode; при нехватке fresh stock pipeline fail closed.

## Real replacement attempt — correct fail-closed
После архивирования старого slot 16 пользователь запустил `vv longrun-next`.
Результат:

```text
fresh usable: 1/5
fresh + bounded cooled fallback: 3/5
render stopped; no replacement MP4
```

Audit показал точный bottleneck:

```text
Pexels candidates: 59
vision reviewed: 59
vision approved: 56
new Pexels audio accepted: 0
56 rejects: downloaded file is missing audible audio
selected pool after fallback: 3
Pixabay candidates: 0
```

То есть geometry и visual relevance почти не ограничивают выбор; проблема — stock files без реально слышимого source audio.

## Cat source v6 — audio first, vision second
`vv` теперь маршрутизирует cat sourcing через `animal_audio_sources_v6`.

Новая policy:
- до Luna проверяется remote audio stream;
- при наличии stream FFmpeg измеряет реальный mean volume первых секунд;
- confirmed-silent stock не расходует vision calls;
- unmeasurable CDN candidates допускаются только маленьким bounded tail;
- remote cooled history полностью исключена из discovery, historical reuse идёт только через bounded local v5 fallback;
- retry не может добавить ещё один cooled batch поверх уже существующего;
- deep/audibility audit записывается даже на fail;
- audit показывает наличие `PEXELS_API_KEY` / `PIXABAY_API_KEY` только boolean-ами, без секретов.

Config:
```toml
[animal]
remote_audio_probe_seconds = 6.0
remote_audio_unknown_max_candidates = 12
```

Если replacement slot 16 снова fail closed, сначала смотреть `provider_availability` и `remote_audibility_gate`; не ослаблять anti-repeat/audio/9:16 gates вслепую.

## AI music — approved and enabled
ACE-Step real local path на RTX 3060 подтверждён. Все 8 initial tracks одобрены и promoted в local approved library.

Preview results:
- AI `0.10` + ducking = accepted;
- cats `0.11` + cat ducking OFF = accepted.

Current config:
```toml
[music]
enabled = true
ai_volume = 0.10
cat_volume = 0.11
ai_ducking = true
cat_ducking = false
```

Replacement slot 16 запускать через `vv longrun-next`, чтобы после render применились reviewed music, `music.json` и final upload metadata / synthetic-media disclosure.

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
`docs/YOUTUBE_COMMENT_FEEDBACK_RU.md`: позже собирать comments, отдельно классифицировать music-topic и sentiment, реагировать только на устойчивый сигнал по нескольким комментариям/videos. First stage recommendation-only.

## Safety
- `$10` OpenAI hard cap;
- никаких новых платных providers без explicit approval;
- secrets runtime-only;
- source/provenance/audio/geometry/vision gates fail closed;
- PR #1 не merge автоматически.

## Immediate continuation
1. дождаться green CI для v6;
2. user local `git pull`;
3. проверить boolean provider availability без вывода ключей;
4. снова `vv longrun-next` для slot 16;
5. при success проверить source audits + `music.json` + preview;
6. при fail использовать новый audit для решения, нужен ли Pixabay key / другой safe provider path / deeper fresh strategy;
7. scheduler продолжает draining slots 12–15;
8. slot 17 не генерировать, пока replacement slot 16 и backlog policy не завершены.
