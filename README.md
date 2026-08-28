# VV_knopka

Review-first AI-assisted short-form video studio for a small YouTube Shorts experiment.

## Continue in a new chat / agent session

Before doing any project work, read these two files completely:

1. [`AGENT.md`](AGENT.md) — mandatory rules and frozen pilot constraints.
2. [`docs/PROJECT_HANDOFF_RU.md`](docs/PROJECT_HANDOFF_RU.md) — detailed current status, completed work, blockers, commands, and next steps.

Then verify the live GitHub state of `main`, `mvp/pilot-scaffold`, and draft PR #1.

## Pilot

Produce **15 review-ready Shorts** on one test channel:

- 8 AI-assisted animal/nature curiosity Shorts;
- 7 cute/funny animal compilation Shorts;
- slot 1 = Russian AI Short;
- slot 2 = Russian animal compilation;
- remaining 13 videos = English;
- hard project-side OpenAI budget = **$10 USD**;
- automatic publishing = **OFF** for the pilot;
- animal compilation transition SFX = **none** (no bass/drop/impact/boom).

The shared niche is **Animals / Nature Curiosities**, so AI explainers and real-animal compilations target broadly the same audience instead of mixing unrelated fact niches on one channel.

## Architecture

```text
AI short
idea + script (OpenAI)
        -> footage terms
        -> MoneyPrinterTurbo API
        -> Edge TTS + stock footage + subtitles
        -> runtime/ready_for_review/*.mp4

Animal compilation
editorial concept (OpenAI)
        -> licensed/local clips + sources.json
        -> FFmpeg normalize/crop/micro-fade
        -> runtime/ready_for_review/*.mp4
```

MoneyPrinterTurbo remains a separate upstream service. VV_knopka calls its current `/api/v1` API instead of copying/forking its internals.

## Windows quick start

### 1. Clone this repository and checkout the pilot branch

```powershell
git clone https://github.com/pikachesrar-ui/VV_knopka.git
cd VV_knopka
git checkout mvp/pilot-scaffold
```

### 2. Bootstrap VV_knopka

Python 3.11+ is required.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

The script creates `.venv`, installs the project, copies `.env.example` to `.env`, creates the 15-slot manifest, and runs tests.

### 3. Put the OpenAI API key into `.env`

```text
OPENAI_API_KEY=...
```

Do **not** commit `.env`. The local ledger refuses new calls when the configured $10 pilot budget would be exceeded.

### 4. Install/start MoneyPrinterTurbo

Use its current Windows package or clone it separately. Its API must be reachable at:

```text
http://127.0.0.1:8080/docs
```

Configure **Pexels** (or another supported footage provider) inside MoneyPrinterTurbo. Edge TTS does not need a separate paid TTS key.

### 5. Check the pilot lock

```powershell
.\.venv\Scripts\vv.exe status
```

Expected:

```text
OpenAI spent: $0.0000 / $10.00
auto_publish: False
publication gate: PASS
```

### 6. Generate the first Russian AI plan

```powershell
.\.venv\Scripts\vv.exe plan 1
```

This writes:

```text
runtime/slots/01/plan.json
```

Review its factual claims before rendering.

### 7. Render slot 1 through MoneyPrinterTurbo

```powershell
.\.venv\Scripts\vv.exe render-ai 1
```

The finished file is downloaded to:

```text
runtime/ready_for_review/slot-01-ru-ai.mp4
```

Nothing is uploaded to YouTube automatically.

## Animal compilation input

Each animal slot requires `runtime/slots/XX/sources.json` and at least three local clips. Example:

```json
{
  "clips": [
    {
      "file": "clip-01.mp4",
      "source_url": "https://example.com/original-source",
      "license": "provider license / creator permission",
      "commercial_use_allowed": true,
      "creator": "optional credit"
    }
  ]
}
```

The renderer refuses incomplete provenance or clips not explicitly marked for commercial use. Raw social-media downloads without usable rights metadata are intentionally not accepted.

Render the Russian animal test (slot 2):

```powershell
.\.venv\Scripts\vv.exe plan 2
.\.venv\Scripts\vv.exe render-animal 2
```

## Pilot safeguards

- human review before publishing;
- no automatic uploader in v0.1;
- OpenAI cost ledger and hard $10 project budget;
- source provenance gate for animal compilations;
- duplicate-script detection helper;
- no transition bass/impact SFX;
- runtime files/API keys ignored by Git.

See [`docs/PILOT_PLAN.md`](docs/PILOT_PLAN.md) for the fixed 15-video slot plan.
