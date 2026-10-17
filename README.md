# yap-editor

Turn raw talking-to-camera takes into a finished 9:16 reel: transcribe the footage, plan the cut, assemble it, render it, review it on your phone, approve it.

The finished frame is black, with the 16:9 clip as a band across the middle at 31.7% of the height, a persistent headline above it, and lowercase karaoke captions on the lower third of the band.

## Install the dependencies

Three things have to exist before anything here runs: **ffmpeg**, **Python 3**, and **Node 18+**. Remotion is not installed globally; it comes in with `npm install` inside `render/`.

**macOS** (Homebrew, from [brew.sh](https://brew.sh)):

```bash
brew install ffmpeg python node
```

**Debian / Ubuntu:**

```bash
sudo apt update && sudo apt install -y ffmpeg python3 python3-pip
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs
```

**Windows:** use [WSL2](https://learn.microsoft.com/windows/wsl/install) and follow the Debian steps inside it. The Remotion renderer wants a Linux or macOS environment.

Check all three answer:

```bash
ffmpeg -version | head -1
python3 --version
node --version
```

Then install Remotion and its dependencies. This is the only build step in the repo, and it pulls Remotion, React, and the renderer into `render/node_modules`:

```bash
cd render
npm install
cd ..
```

On the **first render only**, Remotion downloads its own headless Chrome (a few hundred MB). That is why the first run takes minutes and later runs take seconds. Nothing else needs installing to produce a reel: transcription, cutout, and publishing are optional extras listed in `pipeline/requirements.txt`.

## The five-minute quickstart

```bash
git clone https://github.com/NulightJens/yap-editor.git
cd yap-editor
cd render && npm install && cd ..
make quickstart
open out/sample-reel.mp4
```

`make quickstart` runs `cut` then `render` against the committed `sample/cuts.json`. It needs no transcription backend and no API keys.

## The worked example

`sample/sample-16x9.mp4` is 31.333 seconds of deliberately badly structured narration. It opens on wind-up, buries the hook at about 0:06, and contains a restart at about 0:18 that resolves at 0:22. That is the raw material the method exists to fix.

`sample/cuts.json` moves the hook to 0:00, drops the wind-up, keeps the later attempt of the restart, and lands at about 17 seconds. Five segments survive, at 4.687s, 5.721s, 4.088s, 2.154s and 0.954s after word-boundary padding.

Verified from a clean clone:

| Measurement | Result |
| --- | ---: |
| Planned duration | 17.604s |
| Cut duration | 17.610s |
| Loudness | -14.55 LUFS (target -14 ±1) |
| Join integrity | 56 words match the planned keep-text |
| Pixel format | yuv420p |
| Reel dimensions | 1080x1920 |

Join integrity is the one that matters: `verify.py` re-transcribes the finished file and diffs it against what the plan said should be there, so a cut that clipped a word at a join fails rather than shipping. It reports `SKIPPED` rather than `PASS` when no transcription backend is installed.

## Bring your own footage

Transcribe the footage:

```bash
python3 pipeline/transcribe.py media/take-a.mp4 -o build/take-a.words.json
```

Draft the mechanical passes:

```bash
python3 pipeline/plan.py build/take-a.words.json -o build/take-a.cuts.draft.json --media media/take-a.mp4
```

Edit `cuts.json` by hand. It is the decision file: put the best take per beat, tangent trims, hook surgery, and structural reasons there.

Assemble and stage the cut:

```bash
python3 pipeline/assemble.py build/take-a.cuts.json
```

Render and verify:

```bash
cd render
npx remotion render src/index.ts LandscapeOnBlack ../out/take-a-reel.mp4 --props=public/reels/take-a/props.json
cd ..
python3 pipeline/verify.py build/take-a/cut.mp4
```

## What's in here

| Directory | Purpose |
| --- | --- |
| `agent/` | Editing method, craft references, execution protocol, and quality bar. |
| `pipeline/` | Transcription, mechanical planning, FFmpeg assembly, captions, and verification. |
| `render/` | Standalone Remotion app. The `LandscapeOnBlack` composition is the reel layout. |
| `cutout/` | Apple-Silicon `mlx-sam` greenscreen segmentation and compositing path. |
| `review/` | Static phone review page, publishing, decision collection, and approval gate. |

## The method

The editing method is documented in `agent/AGENT.md` and the linked knowledge files. `pipeline/CUTS-SCHEMA.md` is the contract between editorial judgement and deterministic assembly.

## Jesemm fork: branding and Social Studio

This fork is branded for Jesemm Home Ventures and sends finished reels to the dashboard's Social Studio.

**Branding.** `render/src/brand.ts` holds the palette, tagline and URL; `render/public/brand/logo.png` is the logo (shown on a white card at the top); the fonts are Archivo and Source Sans 3 (the same as jesemmhomeventures.com), inlined by `python3 scripts/inline_brand_fonts.py`. The layout is a gradient indigo ground, the logo card, the headline, the video band between a blue-teal-sun line, and a call-to-action pill. A reel can override any brand field with a `"brand": {...}` object in its `props.json` (for example to render a reel for another brand).

**Send to Social Studio.** Put the three lines from Social Studio -> Setup -> Connections -> "Reel editor (Yap)" in `.env` (see `.env.example`), then:

```bash
python3 review/publish_social.py out/take-a-reel.mp4 --headline "the line on screen" \
  --caption "The post text" --hashtags "realestate,sellinghouses" --platforms facebook,instagram
```

The video is uploaded straight to storage and added to the brand's library, and one draft per channel appears in Social Studio -> Review & approve. Nothing is posted until a person approves and schedules it there (the brand's banned-phrase and Fair Housing rules are checked on the caption). This replaces the S3/R2 phone review page for our use; `review/` is left in place.

**Dispo deal walkthroughs.** `scripts/deal_video.py` cleans up a property walkthrough (trim, even out the sound, 1920x1080), adds the branded intro (address or area, facts, price, spread, rent) and outro (offer deadline and link), renders it with the `DealWalkthrough` composition, and attaches it to the deal on the dashboard:

```bash
python3 scripts/deal_video.py --list                                  # active deals and their ids
python3 scripts/deal_video.py raw-walkthrough.mp4 --deal <deal-id> --trim 4.5-96 --normalize
```

Facts come from the deal (a hidden address is never put in the intro). Add `--no-publish` to only render, or pass `--headline/--price/--spread/--url` by hand. An AI-generated intro clip (for example from Higgsfield) can be dropped in as the footage's first seconds before running this.

**The reel editor (no commands after setup).** In the dashboard, Social Studio -> Create -> **Reel editor**: add raw videos, optionally write instructions, and press Edit my video. This repo's **worker** does the editing in the background: it downloads the videos, has the dashboard transcribe them (OpenAI Whisper), asks the AI editor for the cut (hook first, tangents and flubs out, following `agent/`), cuts and renders the branded reel, uploads it, and the dashboard puts drafts in Review & approve. Tell it what to change ("start with the second story") and it re-edits without re-listening. Dispo walkthroughs work the same way and attach to the deal.

One-time setup on the computer that will do the editing:

```bash
python3 scripts/worker.py --install     # checks ffmpeg and Node, installs the renderer, starts the worker, and starts it at every login
```

The dashboard shows a green "online" light when it is running. Remove it with `--uninstall`. To run it on a server instead (so your own computer can be off), use the `Dockerfile`: it needs only SOCIAL_STUDIO_URL and SOCIAL_STUDIO_TOKEN. Cloudflare Containers can host it (4 vCPU / 12 GiB at most, so renders are slower than on a Mac); Fly.io, Railway or Render work too.

**Rendering tip.** If Remotion's own browser download stalls, render with the Chrome you already have: add `--browser-executable="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"`.

## Optional extras

`plan.py`, `assemble.py`, `verify.py`, and every script in `review/` run on Python's standard library plus `ffmpeg` and `ffprobe`. Nothing else is required to make a reel.

The extras, each a commented line in `pipeline/requirements.txt`:

| Want | Install | Enables |
| --- | --- | --- |
| Transcription | `pip3 install faster-whisper` (or `mlx-whisper` on Apple Silicon) | `transcribe.py`, and the join-integrity check in `verify.py` |
| Greenscreen cutout | `pip3 install mlx-sam pillow numpy scipy fastapi uvicorn` | `cutout/` (Apple Silicon only) |
| Publishing to object storage | `pip3 install boto3` | `review/publish.py` |

## Licence

MIT. See `LICENSE`.

## Credits

The editing method and source references are listed in `CREDITS.md`.
