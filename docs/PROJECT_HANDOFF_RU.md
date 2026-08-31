# VV_knopka — PROJECT HANDOFF (RU)

GitHub = source of truth. Рабочая ветка `mvp/pilot-scaffold`. Draft PR #1 открыт и **не merge** без отдельного решения пользователя.

## Цель

Автономный long-run pipeline:

`идея/факт -> validation -> render -> metadata -> YouTube upload -> publication verification -> statistics`

Текущий work block = YouTube v2 + AI fact-check + local AI-music. TikTok отложен.

## Реальный checkpoint — 2026-08-31

На Windows ПК подтверждено:

- frozen pilot 15/15 визуально принят;
- slot 16 EN cats / #008 готов локально;
- ready локально: **16**;
- slots **1–11** опубликованы через API и `VERIFIED_PUBLIC`;
- pending = **5**, slots 12–16;
- next generation = slot 17 AI EN after pending=0;
- OpenAI ledger = **$0.1885/$10**;
- scheduler `VV Knopka Long Run` установлен и работает по 01:30/03:30/05:30 MSK.

Реальный unattended run подтвердил: slot 11 auto-uploaded, затем `uploadLimitExceeded` корректно превратился в cooldown/defer без traceback.

## YouTube v2

Реализовано и real-channel validated:

- hashtags + CTA + normalized `snippet.tags`;
- metadata v2;
- real long-run auto-publish semantics;
- conditional `containsSyntheticMedia`;
- graceful upload-limit cooldown;
- `vv-youtube verify`;
- `vv-youtube stats` + history;
- `vv-youtube report` age-aware metrics.

Первый sample пока слишком маленький для оптимизации.

## AI fact-check

Long-run AI plan fail-closed до render:

```text
candidate plan -> bounded web-search evidence check -> PASS/FAIL
```

FAIL = no render/no publish. Стоимость включена в общий `$10` ledger.

## MoneyPrinterTurbo

`MPTProcessManager` может auto-start/wait/stop локальный MPT. Постоянно открытый MPT PowerShell не требуется как product dependency.

## AI background music — all initial tracks approved

ACE-Step 1.5 real local validation на RTX 3060 прошёл. Первый live run обнаружил долгий `/query_result` `httpx.ReadTimeout`; клиент исправлен так, чтобы polling timeout считался transient до общего task deadline. Regression test добавлен.

После fix успешно сгенерированы и пользователем **явно одобрены все 8** initial tracks:

```text
cute_01.wav
cute_02.wav
playful_01.wav
playful_02.wav
curious_01.wav
curious_02.wav
calm_01.wav
calm_02.wav
```

Локально они пока могут ещё лежать в `runtime/assets/music/candidates/`; explicit promotion:

```powershell
.\.venv\Scripts\vv-music.exe approve `
  cute_01.wav cute_02.wav `
  playful_01.wav playful_02.wav `
  curious_01.wav curious_02.wav `
  calm_01.wav calm_02.wav
```

`approve` не включает feature flag.

Production music пока:

```toml
[music]
enabled = false
```

Перед activation добавлен safe `vv-music preview`: он копирует finished MP4 и подмешивает approved track только в копию. Source и config не меняются. После прослушивания проверить уровни `ai_volume=0.10`, `cat_volume=0.07`, `ducking=true`; затем можно отдельно включить production music.

Music pipeline уже поддерживает deterministic rotation/cooldown, pipeline-specific preferences, per-slot SHA256 audit, MPT BGM muting и YouTube disclosure при реально applied AI music.

## Future YouTube comment feedback

Пользователь хочет позже анализировать комментарии и менять музыку при устойчивом негативе именно про BGM.

Plan: `docs/YOUTUBE_COMMENT_FEEDBACK_RU.md`.

Policy:

- topic classification отдельно от sentiment;
- считать только music-related feedback для решения о BGM;
- не реагировать на единичный негатив;
- учитывать несколько комментариев/Shorts + performance metrics;
- first stage = report/recommendation only;
- изменение volume/library/enabled state только с human approval.

## Safety / rules

- OpenAI hard cap = **$10**;
- no new paid providers without explicit approval;
- secrets stay local/ignored;
- source/provenance/audio/geometry/vision gates fail closed;
- PR #1 stays draft/open/unmerged without explicit merge instruction.

## CI

Workflow `33429860042` для ACE-Step timeout fix: Ubuntu PASS, Windows PASS.

Music-preview code добавлен позже; re-check fresh CI before claiming current HEAD fully green.

## Immediate continuation

1. local `git pull`;
2. promote all 8 approved tracks;
3. preview one cat Short + one AI Short;
4. user checks actual mix/ducking;
5. if approved, enable `[music].enabled=true`;
6. scheduler drains slots 12–16;
7. after pending=0 validate slot 17 end-to-end.

TikTok remains out of scope.
