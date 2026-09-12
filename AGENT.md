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
Do not manually generate/upload while healthy scheduler is running.
MPT auto-start/wait/stop-own-process is available for AI. Cats use local FFmpeg.
Provenance/commercial-use/audio/geometry/vision/fact-check gates remain fail-closed.
Cat source cooldown=5 episodes, cooled reuse max=2 total / 1 per history episode.
Current source route: animal_audio_sources_v6 (depends on older layers; don't delete blindly).
Eight ACE-Step tracks were listened to/approved; production enabled:
ai_volume=.10, cat_volume=.11, ai_ducking=true, cat_ducking=false.
Conditional synthetic-media disclosure remains enabled. Secrets/tokens local/ignored.
Metadata backfill 1–11 and pre-upload upgrade 12–15 were completed historically.

After substantive work update this file, PROJECT_HANDOFF_RU.md and PROGRESS_RU.md.

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
