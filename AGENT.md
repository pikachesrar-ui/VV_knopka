# VV_knopka — Agent Rules

This file is the mandatory entry point for any new ChatGPT/Codex/agent session working on this repository.

## 1. Read order

Before changing code or giving status claims:

1. Read this file completely.
2. Read `docs/PROJECT_HANDOFF_RU.md`.
3. Read `docs/PROGRESS_RU.md`.
4. For music work read `docs/AI_MUSIC_RU.md`.
5. For future comment-feedback work read `docs/YOUTUBE_COMMENT_FEEDBACK_RU.md`.
6. Check current branch/HEAD/CI and draft PR #1.
7. Treat GitHub as source of truth for code/history.

## 2. Project goal

Automated short-form animal/nature pipeline with:

- `ai_short`: original fact/story Short through MoneyPrinterTurbo;
- `animal_compilation`: cat compilation via local FFmpeg.

Current phase: unattended long-run generation + user-authorized YouTube publishing + verification/statistics + curated local AI music. TikTok is out of the current block.

## 3. Frozen pilot

- 15 Shorts total: 8 AI + 7 cats.
- slot 1 RU AI, slot 2 RU cats, slots 3–15 EN.
- all 15 generated and visually accepted.
- frozen pilot stays immutable/review-first (`pilot.auto_publish=false`).
- do not rebuild pilot just for newer metadata.

## 4. Real local checkpoint — 2026-08-31

Confirmed on the user's Windows PC:

- ready local Shorts: **16**;
- YouTube receipts: **11**, slots 1–11;
- slots 1–11 = `VERIFIED_PUBLIC`;
- pending uploads: **5**, slots 12–16;
- next generation target: **slot 17 AI EN**, blocked until pending=0;
- OpenAI ledger: **$0.1885/$10**;
- Task Scheduler `VV Knopka Long Run` installed and Ready;
- triggers: 01:30 / 03:30 / 05:30 MSK.

Real scheduler validation passed: slot 11 was automatically published, then next upload hit `uploadLimitExceeded`, which was converted to clean cooldown/defer behavior.

## 5. Authorization / safety

User explicitly authorized:

- automatic future YouTube publishing;
- uploading current ready backlog;
- YouTube metadata/discovery improvements;
- fail-closed AI fact checking;
- preparation/use of a curated rotating AI-generated music library after track approval.

Current YouTube config intentionally:

```toml
[youtube]
enabled = true
auto_publish = true
privacy_status = "public"
```

Mandatory constraints:

- OpenAI hard cap = **$10**;
- no new paid provider or raised cap without explicit approval;
- secrets/tokens stay local/ignored;
- source/provenance/audio/geometry/vision gates remain fail-closed;
- channel binding and upload receipts remain idempotency/safety requirements;
- draft PR #1 stays **open/draft/unmerged** until explicit user decision.

## 6. Long-run schedule

Starts at slot 16:

- cycle cats, AI, cats, AI...;
- AI EN;
- cat languages `en,en,en,en,ru`;
- AI subject cooldown 6;
- cat source cooldown 5 episodes.

Each scheduler trigger is backlog-first:

1. status;
2. verify existing receipts;
3. best-effort stats;
4. if pending > 0: upload exactly one oldest and stop;
5. if pending == 0: generate one next slot;
6. upload only that newest video;
7. deferred/failure blocks backlog growth.

## 7. YouTube v2

Implemented and real-channel validated:

- hashtags + CTA + normalized `snippet.tags`;
- metadata v2 for long-run;
- real auto-publish semantics;
- conditional `containsSyntheticMedia`;
- graceful daily upload cooldown (`DEFERRED`, exit 75);
- `vv-youtube verify`;
- `vv-youtube stats` + history;
- `vv-youtube report` age-aware metrics.

Do not optimize from the first tiny 11-video stats sample.

## 8. AI fact-check

Long-run AI plan fail-closed before render:

```text
candidate plan -> bounded web-search evidence check -> PASS/FAIL
```

PASS promotes to `plan.json`; FAIL means no render/no publish. Cost is included in project-side `$10` ledger.

## 9. MoneyPrinterTurbo

`MPTProcessManager` can start/wait/stop local MPT automatically. A permanently open MPT PowerShell window is not a product requirement.

## 10. AI background music

Production flag remains OFF until a real mixed-video preview is approved:

```toml
[music]
enabled = false
```

Implemented:

- local generator target: ACE-Step 1.5;
- local approved library: `runtime/assets/music/`;
- candidates: `runtime/assets/music/candidates/`;
- `vv-music status/list/generate-library/approve/preview`;
- API auto-start + async polling + WAV download;
- transient polling `ReadTimeout` retry until overall deadline;
- deterministic rotation + cooldown;
- quiet AI/cat levels + sidechain ducking;
- per-slot SHA256 audit;
- MPT BGM muted when local music is applied;
- applied AI music can set YouTube synthetic-media disclosure.

### Real local ACE-Step validation

On the user's RTX 3060 PC:

- official ACE-Step 1.5 setup succeeded;
- real long `/query_result` timeout bug was found and fixed;
- all 8 candidates generated successfully;
- user explicitly approved **all eight**:

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

Promotion command:

```powershell
.\.venv\Scripts\vv-music.exe approve `
  cute_01.wav cute_02.wav `
  playful_01.wav playful_02.wav `
  curious_01.wav curious_02.wav `
  calm_01.wav calm_02.wav
```

Approval does not enable production automatically.

`vv-music preview` must be used to listen to the real FFmpeg mix on a copy of a finished Short before switching `music.enabled=true`.

## 11. Future YouTube comment feedback

User wants a later feedback loop that detects sustained negative feedback specifically about BGM and then recommends lowering/changing/disabling music.

Rules are in `docs/YOUTUBE_COMMENT_FEEDBACK_RU.md`:

- classify topic separately from sentiment;
- music policy uses only music-related comments;
- do not react to one comment;
- aggregate across multiple comments/videos/time;
- first stage recommendation-only;
- no automatic production config mutation without human approval.

## 12. Cat rules

- local FFmpeg renderer;
- generic cats, no voiceover;
- original source audio primary;
- real meow on cards;
- no bass/drop/impact/boom SFX;
- commercial-use provenance + audible audio + near-9:16 fail-closed;
- minimum 5 unique usable clips;
- Pexels/Pixabay normal automated sources;
- frozen pilot all-history reuse protection;
- long-run previous-5-episodes cooldown.

## 13. Git / CI

Development branch: `mvp/pilot-scaffold`.
Draft PR #1 into `main` must remain draft/open/unmerged without explicit user instruction.

Workflow `33429860042` for ACE-Step timeout fix: Ubuntu PASS, Windows PASS.

Music-preview code was added after that workflow; check fresh CI before claiming current HEAD fully green.

## 14. Immediate continuation

1. local `git pull`;
2. approve all eight tracks;
3. run safe preview on at least one cat and one AI finished Short;
4. user listens to actual volume/ducking;
5. only after approval enable `[music].enabled=true`;
6. scheduler continues draining slots 12–16;
7. after pending=0 validate slot 17 end-to-end.

TikTok remains a later block.

## 15. Context persistence

After substantive work update `AGENT.md`, `docs/PROJECT_HANDOFF_RU.md`, and `docs/PROGRESS_RU.md`.
