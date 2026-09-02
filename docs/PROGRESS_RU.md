# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-09-02**.

## Current YouTube state
```text
published + VERIFIED_PUBLIC: slots 1–11
published metadata backfill: slots 1–11 DONE and final dry-run UNCHANGED
pending metadata upgrade: slots 12–15 DONE locally before first upload
ready local: through slot 16
pending now: slots 12–16 (5 uploads)
next generation after pending=0: slot 17 AI EN
OpenAI spent last shown: $0.2024 / $10.00
scheduler: 01:30 / 03:30 / 05:30 MSK
```

Scheduler is backlog-first: one oldest upload per trigger; only when pending reaches zero does it generate one next slot and upload it.

## Scheduler incident 2026-09-02 — FIXED IN BRANCH, LOCAL PULL REQUIRED
Real unattended logs showed:
- 2026-08-31 01:30: slot 11 uploaded successfully;
- 2026-08-31 03:30: slot 12 correctly deferred by YouTube `uploadLimitExceeded` and a persisted cooldown was written;
- after the cooldown expired, triggers on 2026-09-01 and 2026-09-02 verified slots 1–11 as `VERIFIED_PUBLIC` but then terminated immediately after verification with `ERROR: Traceback (most recent call last):`;
- pending remained exactly 5, so slots 12–16 were not uploaded and slot 17 was not generated.

Manual `vv-youtube stats` on 2026-09-02 succeeded and wrote a fresh `runtime/youtube/statistics.json`. The snapshot contained Cyrillic and emoji titles (for example cat titles with `😹`). This isolates the unattended failure to Windows Task Scheduler/native-output handling rather than the YouTube statistics API itself.

Fix in `scripts/run-longrun-task.ps1`:
- force `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` for scheduled `vv`/`vv-youtube` processes;
- set PowerShell output encoding to UTF-8 where the host permits it;
- capture native stderr with temporary `ErrorActionPreference=Continue`, then make fail-closed decisions from the real process exit code;
- preserve `stats` as best-effort: a stats/output failure logs `WARN` and must not block backlog publication;
- `verify`, pending-count, generation and upload failures remain blocking exactly as before.

Regression coverage: `tests/test_scheduler_runner.py` checks the UTF-8/best-effort invariants.

Because the installed scheduled task explicitly does **no git pull**, the Windows checkout must pull the latest `mvp/pilot-scaffold` before the fixed runner is used locally.

## First real statistics sample — do not optimize yet
Manual snapshot on 2026-09-02:
```text
slot 1: 0 views
slot 2: 6
slot 3: 2
slot 4: 1
slot 5: 18
slot 6: 2
slot 7: 1
slot 8: 1
slot 9: 1
slot 10: 3
slot 11: 8
```
This sample is still too small/young for content-strategy conclusions.

## Published metadata backfill — REAL COMPLETE
User ran real apply for slots 1–11.
Initial result: 11/11 UPDATED.
Second validation:
- slots 1–6, 8–11 immediately UNCHANGED;
- slot 7 briefly re-reported missing hidden tags due to YouTube propagation;
- subsequent apply/dry-run for slot 7 returned UNCHANGED;
- final state: all slots 1–11 require no further tags/hashtags changes.

No reuploads occurred. URL/views/privacy/status/video bytes remained untouched.

## Pending slots 12–15 discovery metadata — REAL COMPLETE
User ran the sidecar-only upgrade before any of these four videos had a YouTube receipt.

```text
APPLY summary: 4 pending sidecars | changed=4 | applied=4
```

A subsequent published backfill attempt for slots 12–15 returned:
```text
No uploaded receipt videos matched the requested slots.
```
So none of 12–15 had been published before the sidecar upgrade. Their first normal scheduler uploads will include metadata v2 hidden tags + hashtags directly.

## Slot 16 — fixed and accepted
Bad first #008 archived at:
`runtime/backups/slot-16-before-rebuild-20260831-231504`.

Corrected replacement:
```text
6 unique clips
4 fresh
2 cooled total
1 cooled from slot 2
1 cooled from slot 4
0 protected-window repeats
source audit: PASS
music: curious_02.wav @ 0.11, ducking false
metadata_version: 2
contains_synthetic_media: true
```

## Cat anti-repeat / audio-first
Current limits:
```toml
cat_source_cooldown_episodes = 5
cat_cooled_reuse_max_sources = 2
cat_cooled_reuse_max_per_history_episode = 1
```

Current source pipeline uses audio-first gating and fails closed instead of creating near-remakes.
Later non-blocking optimization: reduce Luna reviews per accepted fresh audible clip.

## Music
All 8 ACE-Step tracks approved and production-enabled.
```toml
[music]
enabled = true
ai_volume = 0.10
cat_volume = 0.11
ai_ducking = true
cat_ducking = false
```

## Autonomous continuation
After the local checkout receives the scheduler fix:
- scheduler should resume draining pending slots 12–16 oldest-first;
- when pending becomes zero, it generates slot 17 AI EN;
- AI uses fact-check + automatic MoneyPrinterTurbo lifecycle;
- cats use local FFmpeg + source gates;
- both get approved ACE-Step music and metadata v2 tags/hashtags;
- upload/verify/stats continue automatically;
- process repeats until a safety/failure gate stops it or OpenAI ledger reaches `$10`.

Already-ready backlog can still upload after generation budget is exhausted because backlog handling occurs before new generation.

TikTok remains out of scope.
Draft PR #1 remains open/draft/unmerged.
