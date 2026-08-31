# VV_knopka — Agent Rules

This file is the mandatory entry point for any new ChatGPT/Codex/agent session working on this repository.

## 1. Read order

Before changing code or giving status claims:

1. Read this file completely.
2. Read `docs/PROJECT_HANDOFF_RU.md`.
3. Read `docs/PROGRESS_RU.md`.
4. For music work read `docs/AI_MUSIC_RU.md`.
5. Check current branch/HEAD/CI and draft PR #1.
6. Treat GitHub as source of truth for code/history.

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

Production flag remains intentionally OFF:

```toml
[music]
enabled = false
```

Implemented:

- local generator target: ACE-Step 1.5;
- local approved library: `runtime/assets/music/`;
- candidates: `runtime/assets/music/candidates/`;
- candidate directory is excluded from production selector;
- `vv-music status/list/generate-library/approve`;
- API auto-start + async polling + audio download;
- deterministic rotation + cooldown;
- quiet AI/cat levels + sidechain ducking;
- per-slot SHA256 audit;
- MPT BGM muted when local music is applied;
- applied AI music can set YouTube synthetic-media disclosure.

### Real local ACE-Step validation

On the user's RTX 3060 PC:

- official ACE-Step 1.5 setup succeeded;
- first real generation exposed `httpx.ReadTimeout` on long `/query_result` polling;
- client was fixed so polling ReadTimeout retries until the overall task deadline;
- regression test added;
- after pull, all 8 candidates generated successfully:

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

User listened to several and said they like them. **This is not approval of all eight.** Before moving files into production, obtain the exact approved filenames.

Promotion command:

```powershell
.\.venv\Scripts\vv-music.exe approve <selected names>
```

Approval does not enable the feature flag automatically.

## 11. Cat rules

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

## 12. Git / CI

Development branch: `mvp/pilot-scaffold`.
Draft PR #1 into `main` must remain draft/open/unmerged without explicit user instruction.

Last fully green checkpoint before runtime timeout fix:

```text
936bd095... | 147 tests | Ubuntu PASS | Windows PASS
```

Runtime fix commits:

```text
795b7f01 — retry ACE-Step polling ReadTimeout
463f2d5d — regression test
```

Workflow `33429860042`: Ubuntu PASS; Windows was still running at last observed check. Re-check current CI before claiming current HEAD fully green.

## 13. Immediate continuation

1. get exact approved candidate names from user;
2. approve only those tracks;
3. keep `music.enabled=false` until separate activation decision;
4. scheduler continues draining slots 12–16;
5. after pending=0 validate slot 17 end-to-end;
6. later run a controlled music ON vs OFF comparison using `vv-youtube report`.

TikTok remains a later block.

## 14. Context persistence

After substantive work update `AGENT.md`, `docs/PROJECT_HANDOFF_RU.md`, and `docs/PROGRESS_RU.md`.
