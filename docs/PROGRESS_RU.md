# VV_knopka — LIVE PROGRESS (RU)

Последнее обновление: **2026-09-01**.

## YouTube / scheduler
```text
published + VERIFIED_PUBLIC: slots 1–11
active ready backlog after archiving bad slot 16: slots 12–15
replacement long-run target: slot 16 cats EN
OpenAI spent last shown: $0.1885 / $10.00
scheduler: 01:30 / 03:30 / 05:30 MSK
```

Real unattended validation passed: slot 11 auto-uploaded; later `uploadLimitExceeded` was converted to persisted cooldown/defer without traceback.

Bad unuploaded slot 16 is safely archived at:
`runtime/backups/slot-16-before-rebuild-20260831-231504`.

## Music — REAL LOCAL APPROVAL COMPLETE
ACE-Step setup/generation works on user's RTX 3060. All 8 tracks are approved locally.

Accepted real preview profiles:
```toml
[music]
enabled = true
ai_volume = 0.10
cat_volume = 0.11
ai_ducking = true
cat_ducking = false
```

Future long-run renders use deterministic approved rotation; applied AI-generated music propagates synthetic-media disclosure.

## Cat source repetition — fixed anti-remake policy
Original slot 16 / cat #008 had 5/6 clips reused from cat #001.

Current limits:
```toml
cat_source_cooldown_episodes = 5
cat_cooled_reuse_max_sources = 2
cat_cooled_reuse_max_per_history_episode = 1
```

## Replacement attempt — fail-closed worked correctly
After archiving old slot 16, real `vv longrun-next` stopped instead of making another remake:

```text
first pass: 1/5 usable
with bounded cooled fallback: 3/5 usable
no replacement MP4 produced
```

Detailed source audit:
```text
Pexels candidates: 59
vision reviewed: 59
vision approved: 56
audio accepted from those new candidates: 0
rejection reason: 56 × downloaded file is missing audible audio
selected after fallback: 3
Pixabay candidates: 0
```

Conclusion: Luna/visual relevance and 9:16 geometry were not the bottleneck. The dominant problem is silent stock footage.

## Cat source v6 — IMPLEMENTED, CI validation in progress
Current `vv` path now uses `animal_audio_sources_v6`.

Changes:
- actual audibility check happens before Luna vision review;
- FFmpeg measures remote mean volume only after audio stream is confirmed;
- confirmed-silent files never consume Luna review calls;
- remote probe failures are capped to 12 unknown fresh candidates/provider;
- remote cooled-history candidates are excluded; cooled reuse remains only bounded local fallback;
- retry cannot stack a second cooled batch on top of an existing cooled fallback;
- failure audits now include deep-search/audibility diagnostics;
- `provider_availability` records only boolean Pexels/Pixabay key presence.

Config:
```toml
remote_audio_probe_seconds = 6.0
remote_audio_unknown_max_candidates = 12
```

Regression tests for v6 were added. Await final Ubuntu + Windows CI on the latest code/docs HEAD before declaring the checkpoint fully green.

## Next local step after green CI
```powershell
git pull
.\.venv\Scripts\vv.exe longrun-next
```

Before/after the run, check provider availability without printing secrets. If the run fails again, inspect:
- `remote_audibility_gate`;
- `provider_availability`;
- Pexels/Pixabay stats;
- rejection reasons.

Do not loosen anti-repeat, audible-audio or 9:16 gates merely to force a render.

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
