# VV_knopka — AI background music (RU)

## Цель

Добавлять в будущие long-run Shorts очень тихую приятную инструментальную музыку, не забивая voiceover AI facts, оригинальный звук cat clips и meow на black cards.

Музыка не генерируется заново для каждого ролика. Используется небольшая curated local library с deterministic rotation и cooldown.

## Current state — 2026-08-31

Реальный локальный ACE-Step flow подтверждён на RTX 3060 пользователя:

- official ACE-Step 1.5 setup — PASS;
- local API auto-start — PASS;
- first-run long polling bug (`httpx.ReadTimeout`) найден и исправлен;
- regression test добавлен;
- после fix успешно сгенерированы все 8 initial WAV candidates;
- пользователь прослушал набор и **явно одобрил все 8** для production library.

Approved set:

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

Local promotion command:

```powershell
.\.venv\Scripts\vv-music.exe approve `
  cute_01.wav cute_02.wav `
  playful_01.wav playful_02.wav `
  curious_01.wav curious_02.wav `
  calm_01.wav calm_02.wav
```

Promotion moves files from `runtime/assets/music/candidates/` to `runtime/assets/music/` and marks the manifest approved. It **does not** turn production music on.

## Safety state

Until a real mixed-video preview is listened to, production flag remains intentionally:

```toml
[music]
enabled = false
```

Candidate/approved separation remains important:

```text
runtime/assets/music/
  candidates/          # generated but not production-visible
  cute_01.wav          # approved root files are production-visible
  ...
```

## Safe preview before activation

`vv-music preview` creates a copy of an existing finished Short and mixes one approved track into the copy. The source MP4 and `music.enabled` are unchanged.

Example for a cat Short:

```powershell
.\.venv\Scripts\vv-music.exe preview `
  --video <finished-short.mp4> `
  --track cute_01.wav `
  --pipeline animal_compilation
```

Example for an AI fact:

```powershell
.\.venv\Scripts\vv-music.exe preview `
  --video <finished-short.mp4> `
  --track curious_01.wav `
  --pipeline ai_short
```

Default preview output:

```text
runtime/music/previews/<source>.<pipeline>.<track>.preview.mp4
```

After listening to a real preview, decide whether current `ai_volume=0.10` / `cat_volume=0.07` and ducking are appropriate. Only then switch `[music].enabled=true`.

## Production rotation

Once enabled:

- AI facts prefer `curious_*`, then `calm_*`;
- cats prefer `cute_*`, then `playful_*`, then `calm_*`;
- recent tracks are blocked by `cooldown_shorts=5` when possible;
- selection stays deterministic;
- each slot writes `music.json` with track name, SHA256, generator, volume, ducking and applied state;
- MPT BGM is muted when approved local music is applied, avoiding double music;
- AI-generated music can propagate YouTube synthetic-media disclosure.

Current target levels:

```toml
ai_volume = 0.10
cat_volume = 0.07
ducking = true
```

## ACE-Step generation

Initial generation command:

```powershell
.\.venv\Scripts\vv-music.exe generate-library --count 8 --duration 45
```

The client uses ACE-Step async REST flow:

```text
POST /release_task -> task_id
POST /query_result -> status 0/1/2
GET /v1/audio?... -> WAV
```

Polling read timeouts are treated as transient while the overall task deadline is still active, because first-run/model initialization can hold requests longer than a normal HTTP timeout.

## Feedback loop later

Пользователь предложил в будущем анализировать YouTube comments и менять музыку, если зрители устойчиво жалуются именно на BGM.

Это добавлено в план: `docs/YOUTUBE_COMMENT_FEEDBACK_RU.md`.

На первом этапе comment feedback должен быть observational/recommendation-only. Единичный негативный комментарий не должен автоматически менять production configuration.
