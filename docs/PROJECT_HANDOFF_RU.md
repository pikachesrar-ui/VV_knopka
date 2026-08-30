# VV_knopka — PROJECT HANDOFF (RU)

Актуальный контекст для нового чата. GitHub — source of truth для code/commit/CI. Рабочая ветка: `mvp/pilot-scaffold`. Draft PR #1 открыт; не merge без отдельного решения пользователя.

## Frozen pilot

15 Shorts: 8 × `ai_short`, 7 × `animal_compilation`; slot 1 RU AI, slot 2 RU cats, остальные 13 EN; one channel; OpenAI project cap `$10`; `auto_publish=false`; human review; production outputs only `runtime/ready_for_review`.

Manifest:

```text
AI slots:     1,3,5,7,9,11,13,15
Animal slots: 2,4,6,8,10,12,14
RU slots:     1,2
```

## Manual quality / local state

User visually accepted proof pair in both branches:

- slot 1 RU AI facts = QUALITY PASS;
- slot 2 RU cats = QUALITY PASS;
- slot 3 EN AI facts = QUALITY PASS;
- slot 4 EN cats = QUALITY PASS.

Last explicitly shown local OpenAI ledger was `$0.1036 / $10.00`; do not guess newer value without new `vv status` output.

## Frozen pilot generation — COMPLETE 15/15

User has now confirmed final ready outputs for every manifest slot. The final batch produced:

```text
runtime/ready_for_review/slot-14-en-animals.mp4
runtime/ready_for_review/slot-15-en-ai.mp4
```

Therefore slots 1–15 all have final `ready_for_review` MP4s on the user's machine.

Successful conveyor progression included:

- slot 5 EN AI — SUCCESS;
- slot 6 EN cats — SUCCESS;
- slot 7 EN AI — SUCCESS;
- slot 8 EN cats — SUCCESS after Pixabay helper fix;
- slot 9 EN AI — SUCCESS;
- slot 10 EN cats — SUCCESS after remote-audio prefilter improvement;
- slot 11 EN AI — SUCCESS;
- slot 12 EN cats — SUCCESS;
- slot 13 EN AI — SUCCESS;
- slot 14 EN cats — SUCCESS;
- slot 15 EN AI — SUCCESS.

This is strong end-to-end evidence that the review-first conveyor can sequence both pipelines, resume after safe failures/code fixes, and finish the fixed manifest without regenerating completed slots.

Important distinction: **generation complete != publication approved**. Explicit manual QUALITY PASS is recorded only for slots 1–4. The remaining generated videos still need human visual review before publication.

## Cat sourcing architecture

Keep all current gates:

- licensed/commercial-use provenance;
- source already near 9:16;
- audible source audio;
- vision relevance;
- cross-episode history;
- fail closed below 5 usable clips.

Remote-audio prefilter in `animal_audio_sources_v4.py` runs before Luna/candidate-cap accounting so confirmed-silent stock no longer wastes finite vision capacity. Pexels/Pixabay search uses history exclusion, deeper pagination/query diversity, and Pixabay `popular` + `latest` ordering.

Cross-episode final reuse gate permits at most one incidental repeated `provider + provider_id`; 2+ reused identities fail closed.

YouTube reference `I_pdwiLlvuc` / Kawaiipets passed project metadata/license-declaration + geometry/audio/clean-footage gates and slot 2 preserves attribution. Do not describe this as proof that YouTube acquisition itself is platform-compliant or that full chain-of-title is established. YouTube Data API is discovery/license metadata, not an official media-download endpoint. Long-run production acquisition should prefer explicitly downloadable/licensed stock or independently authorized source files.

## Review-first conveyor

```powershell
.\.venv\Scripts\vv.exe pilot-next
.\.venv\Scripts\vv.exe pilot-batch --count N
```

- strict manifest order;
- non-empty expected MP4 = completion marker/resume boundary;
- state: `runtime/conveyor/state.json`;
- AI: plan-on-demand + managed/check MPT + render;
- cats: licensed sourcing + geometry/audio/vision/history gates + local FFmpeg;
- stop on first failure;
- outputs only `runtime/ready_for_review`;
- `$10` OpenAI hard guard;
- `auto_publish=false`; no uploader/OAuth yet.

Each successful render creates `.upload.json` with proposed title/description, language/pipeline/video path, required attribution, `review_required=true`, `auto_publish=false`, `publication_allowed_by_conveyor=false`.

## Metadata review first 10

User uploaded sidecars for slots 1–10. Review found:

- cat series numbering is correct (`#001` slot 2 through `#005` slot 10);
- AI titles are specific to the fact topic rather than a generic repeated template;
- safety/review flags are preserved;
- slot 2 attribution is present;
- long-run improvements worth adding after pilot review: subject cooldown for AI facts and non-identical cat descriptions.

Do not rebuild the frozen pilot solely for these metadata refinements.

## Immediate continuation

The frozen 15-slot generation phase is done. Next work should **not** be another `pilot-batch`.

Recommended sequence:

1. Human visual review of the generated set, especially later unattended outputs (cats and AI facts).
2. Run `vv status` for final local budget/state checkpoint.
3. If quality is acceptable, mark conveyor validation complete.
4. Implement long-run/unbounded generation mode instead of the finite 15-slot manifest, including durable episode numbering/history, fact-subject cooldown, cat-description variation, and shared source history/pool behavior.
5. Configure Windows Task Scheduler only after long-run mode is ready.
6. YouTube uploader/OAuth remains a separate explicit phase; keep review-first/manual publication until the user explicitly changes policy.

## Git / release

Continue on `mvp/pilot-scaffold`, Draft PR #1. Do not merge until separate user decision after review. PR remains the review vehicle for the pilot work.
