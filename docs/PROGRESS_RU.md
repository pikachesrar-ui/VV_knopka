# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-08-31**.

## YouTube / scheduler
```text
published + VERIFIED_PUBLIC: slots 1–11
pending before slot-16 rebuild: slots 12–16
OpenAI spent: $0.1885 / $10.00
scheduler: 01:30 / 03:30 / 05:30 MSK
```

Real unattended validation passed: slot 11 auto-uploaded; later `uploadLimitExceeded` was converted to persisted cooldown/defer without traceback.

## Music — REAL LOCAL APPROVAL COMPLETE
ACE-Step setup/generation works on user's RTX 3060.
All 8 tracks are approved locally:
`cute_01/02`, `playful_01/02`, `curious_01/02`, `calm_01/02`.

Real preview feedback:
- AI: `0.10` + ducking = accepted;
- cats: initial `0.07` + ducking = far too quiet;
- cats v2: `0.11` + no cat sidechain ducking = accepted.

Production config now:
```toml
[music]
enabled = true
ai_volume = 0.10
cat_volume = 0.11
ai_ducking = true
cat_ducking = false
```

Future long-run renders may use deterministic approved music rotation. Applied AI-generated music must set synthetic-media disclosure.

## Cat source repetition — REAL BUG FOUND
User visually noticed cat #008 / slot 16 repeats several cats from #001.
Audits proved the issue exactly:

```text
slot 16 unique sources: 6
reused recent-window sources: 0
reused cooled-down sources: 5
all five cooled-down sources came from slot 2 / cat #001
fresh final source: only 1
cooled fallback was enabled
```

Old fallback seeded old local stock oldest-first and had no total/per-history-episode cooled reuse cap. Therefore it could legally make most of a new Short from one old episode.

### FIXED POLICY
```toml
cat_source_cooldown_episodes = 5
cat_cooled_reuse_max_sources = 2
cat_cooled_reuse_max_per_history_episode = 1
```

Implementation now:
- fresh stock first;
- recent five cat episodes protected;
- max 2 cooled clips total;
- max 1 from one old episode;
- newest-cooled episode first;
- fail closed if source minimum cannot be reached under these limits;
- `source_reuse_audit.json` reports cooled reuse by history slot and rejects concentration.

Regression suite on anti-remake HEAD: **155 passed in 0.99s** on Ubuntu. Windows CI still needed/was running at the time of this documentation update.

## Slot 16 action
Current slot 16 is **not published** and should not be allowed to reach YouTube in its current form.
Do not touch frozen slots 1–15.

Next local procedure after green CI:
1. `git pull`;
2. verify no YouTube receipt for slot 16;
3. archive existing `runtime/slots/16`, ready MP4 and upload sidecar (no destructive delete);
4. run `vv longrun-next` so deterministic next missing slot is again 16;
5. this full conveyor render will use strict cat-source policy + approved music + final metadata;
6. inspect new source audits/music audit and preview output;
7. only then leave slot 16 in pending upload queue.

## Other completed blocks
- YouTube metadata v2 / tags / hashtags / CTA;
- upload-limit cooldown;
- verify/stats/history/report;
- fail-closed AI fact-check;
- MPT auto lifecycle;
- ACE-Step timeout retry;
- future comment-music feedback plan in `docs/YOUTUBE_COMMENT_FEEDBACK_RU.md`.

TikTok remains out of scope.
Draft PR #1 remains open/draft/unmerged.
