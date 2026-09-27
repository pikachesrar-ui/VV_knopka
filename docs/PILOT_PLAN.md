# 15-video pilot

## Fixed decisions

- One YouTube channel for the pilot.
- Niche: **Animals / Nature Curiosities**.
- 15 Shorts total: 8 AI-assisted fact/story Shorts + 7 animal compilations.
- Exactly one Russian test in each pipeline; the other 13 are English.
- OpenAI project-side hard budget: $10.
- Automatic publishing is disabled until the pilot output is reviewed.
- Animal transitions use no injected bass/impact/boom SFX.

## Slot order

| Slot | Pipeline | Language |
|---:|---|---|
| 1 | AI short | RU |
| 2 | Animal compilation | RU |
| 3 | AI short | EN |
| 4 | Animal compilation | EN |
| 5 | AI short | EN |
| 6 | Animal compilation | EN |
| 7 | AI short | EN |
| 8 | Animal compilation | EN |
| 9 | AI short | EN |
| 10 | Animal compilation | EN |
| 11 | AI short | EN |
| 12 | Animal compilation | EN |
| 13 | AI short | EN |
| 14 | Animal compilation | EN |
| 15 | AI short | EN |

## Review-first workflow

1. Generate `plan.json` for a slot with GPT.
2. Verify factual claims and editorial framing.
3. AI-short branch sends the approved script/search terms to MoneyPrinterTurbo.
4. Animal branch requires a `sources.json` with provenance and commercial-use permission for every clip, then renders locally with FFmpeg.
5. Finished files go to `runtime/ready_for_review/` only.
6. Human review covers audio comfort, crop, captions, source rights, factual accuracy, duplicate risk, and AI disclosure.
7. Publishing integration is deliberately deferred.

## Animal source manifest format

```json
{
  "clips": [
    {
      "file": "clip-01.mp4",
      "source_url": "https://example.com/source",
      "license": "provider license / creator permission",
      "commercial_use_allowed": true,
      "creator": "optional credit"
    }
  ]
}
```

At least three clips are required. Raw social-media downloads without usable rights metadata are not accepted by the renderer.

## MoneyPrinterTurbo integration

Run MoneyPrinterTurbo separately and expose its API on `http://127.0.0.1:8080`. VV_knopka talks to the current `/api/v1/videos` and `/api/v1/tasks/{task_id}` endpoints instead of forking upstream internals. This keeps upstream updates replaceable.
