# VV_knopka — Agent Rules

Mandatory read order:
1. AGENT.md
2. docs/PROJECT_HANDOFF_RU.md
3. docs/PROGRESS_RU.md
4. docs/AI_MUSIC_RU.md for music
5. docs/YOUTUBE_COMMENT_FEEDBACK_RU.md for comment feedback
6. Check branch/HEAD/CI and Draft PR #1.

GitHub is source of truth. Development branch: mvp/pilot-scaffold.
Draft PR #1 must stay open/draft/unmerged until the user explicitly authorizes merge.
TikTok is out of scope. No new paid providers without approval. OpenAI total budget $10.

## Checkpoint supplied by user — 2026-09-05

20 videos in statistics.json, all privacy_status=public; pending ready uploads=0.
66 project views: AI=39, cats=27. Slots 17–20 have now been generated/uploaded.
This is not a new processing-verification run or direct inspection of the Windows task.
Next expected slot at this checkpoint: 21 AI EN; determine live next slot before action.
Current local API spend is unknown; last historical $0.2024 is NOT a current balance.
User had one subscriber (their own second channel), did not share video links.

## Editorial change — 2026-09-06

User authorized implementation following analysis of uploaded statistics and MP4s.
Read docs/EDITORIAL_RU.md for scope, limitations, tests and local update commands.
New renders from slot 21 use direct_v1 under [editorial]. Slots 1–20 remain historical.
Never rerender or overwrite existing MP4s; frozen pilot 1–15 is immutable.
Cats: existing source gates, then 3–4 strong reviewed moments, no black cards,
short captions, content-derived title, strong first/last clips. Keep original audio/music.
AI: exact short hook opens script, answer early, sequential curated stock with a
metadata-based opening heuristic. This is not full semantic scene alignment.
No additional paid stages. Tests/development made no paid API calls.

## Autonomy and safety

Backlog-first scheduler, 01:30/03:30/05:30 MSK:
status -> receipt verify -> best-effort stats -> one oldest pending upload and stop;
only pending=0 -> generate one next slot -> upload that slot.
Upload-limit cooldown persists; deferred/failure prevents backlog growth.
Do not manually generate/upload with raw CLI commands while healthy scheduler is running.
The supported exception is `start-three-video-batch.ps1`: it reuses the same
runner/locks, spaces publications by 60 minutes and suppresses that night's
regular triggers until 06:30. See docs/MANUAL_BATCH_RU.md.
MPT auto-start/wait/stop-own-process is available for AI. Cats use local FFmpeg.
Provenance/commercial-use/audio/geometry/vision/fact-check gates remain fail-closed.
Cat source cooldown=5 episodes, cooled reuse max=2 total / 1 per history episode.
Current source route: animal_audio_sources_v6 (depends on older layers; don't delete blindly).
Eight ACE-Step tracks were listened to/approved; production enabled:
ai_volume=.10, cat_volume=.11, ai_ducking=true, cat_ducking=false.
Conditional synthetic-media disclosure remains enabled. Secrets/tokens local/ignored.
Metadata backfill 1–11 and pre-upload upgrade 12–15 were completed historically.

After substantive work update this file, PROJECT_HANDOFF_RU.md and PROGRESS_RU.md.

## Bounded AI subject recovery — 2026-09-19

Long-run AI slots now distinguish a fresh failed fact-check and fully exhausted
Pexels+Pixabay audit (including insufficient reusable seconds) from transient
failures. One alternative broad visual anchor is allowed per slot, subject to
the existing $10 ledger and an estimated $0.55 per-slot reserve ceiling. The
original plan/audits are archived under `runtime/slots/NN/auto-recovery/`;
`auto-recovery.json` tracks state. After another terminal failure or insufficient
budget the slot is marked blocked, and the next runner selects the next slot.
Unknown/network failures do not qualify for subject skipping. The first
replacement's temporary failure stays retryable. The existing scheduler,
backlog-first publication and receipt gates are unchanged. `vv recovery-status`
lists blocked slots; restoring one requires a different fact-checked plan and
`vv recovery-unblock NN`. A blocked slot is never silently republished.

For new direct_v1 cat reviews, the model sees the images without the prewritten
concept title/hook. The public title still comes from the reviewed first
window's caption, with no additional API call. Existing cached highlights or
rendered MP4s are not modified. This prompt is not an independent vision QA.
The user currently has a manual batch running on their Windows checkout: do
not request an update or claim new slots are public until that batch finishes.

## Stock exhaustion / topic change — 2026-09-19

User logs: slot 30 is public, but slot 31 stalled: octopus footage had only two
vision-approved unique sources versus the three-source quality minimum. A later
cat-box candidate failed fact-check on an unverified paw-gland claim and did not
replace plan.json. The user backed up slot 31 plan/fact-check/material audit under
runtime/recovery. Do not treat a failed batch as successful; slots 1–30 verified
public and pending uploads were zero in the supplied logs.
When a new plan has a different visual anchor, the old exhausted material audit
must not suppress the new anchor's Pexels search. This is now fixed and locally
tested (no paid API calls). Neither the vision gate nor fact-check was relaxed.
The user must pull this change before retrying a new-topic plan and batch on the
Windows PC. Do not claim slot 31 is published without new receipts/verification.

## Rich analytics — 2026-09-15

Owner-only YouTube Analytics is an additive telemetry layer. `auth-analytics`
keeps upload/edit scopes and verifies the existing channel binding. Scheduler
runs core `analytics-sync --if-due-hours 20` best-effort; failure never blocks
generation/upload. Deep traffic/retention collection is manual because it needs
per-video queries. Russian/English Studio CSV/ZIP can be imported idempotently;
exact Stayed-to-watch is never inferred. `analytics-export` creates a secret-free
ZIP for the user to share. No OpenAI calls or paid providers are involved.
Real bundle validation hardened this layer: Analytics API lag no longer creates
false zero snapshots, checkpoints more than 24h late are omitted, Studio duration
is persisted, and AI shorts explicitly about cats infer the `cats` category.

## Manual three-video batch — 2026-09-16

User may launch three safe generation/publication cycles from a Windows shortcut.
The manual batch is sequential, uses the normal runner and receipts, targets one
hour between successful uploads, and cannot overlap itself. A failed attempt
does not count toward the requested three publications: the same missing
publication is retried at most three times, without bypassing any gate. While
running and after successful completion, regular 01:30/03:30/05:30 triggers are
suppressed until the nearest 06:30. Exhausted retries remove suppression so
night recovery remains. Keep retries bounded because OpenAI planning retries
can add cost.

## Audio review — 2026-09-12

User supplied slot 21/22 MP4s. Their local state confirms both were rendered
2026-09-06 00:35/02:54 UTC, before direct_v1 commit at 09:56 UTC. Neither has
the editorial marker; slot 22 has no cat-edit.json. Do not interpret these as
the first direct_v1 outputs or rerender them.
Measured slot 22: five cat clips around -14.6 to -16 LUFS, one quiet clip
-21.6 LUFS, cat peaks near -1 dBTP, transition meows near -8 dBTP.
Future cat sources now use gentle compression, -16 LUFS / -8 dBTP target and
a final peak limiter before approved background music. Silence stays quiet to
avoid boosting background noise. No paid API stages; check a future MP4 by ear.
Windows Python 3.11 exposed that its stdlib wave reader rejects FFmpeg's
WAVE_FORMAT_EXTENSIBLE output. The regression test now validates duration with
ffprobe instead; production audio processing was unaffected. User ledger at
2026-09-13 checkpoint: $0.3087 / $10, publication gate PASS.
