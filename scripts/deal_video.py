#!/usr/bin/env python3
"""Clean up a Dispo walkthrough video, add the branded intro and outro, and attach it to the deal.

    python3 scripts/deal_video.py --list                              # active deals and their ids
    python3 scripts/deal_video.py raw-walkthrough.mp4 --deal <id>     # facts come from the deal; result is attached to it
    python3 scripts/deal_video.py raw.mp4 --deal <id> --trim 4.5-96 --normalize
    python3 scripts/deal_video.py raw.mp4 --headline "123 Main St" --price '$185,000' --url deals.example.com --no-publish

What it does: trims the footage (--trim start-end in seconds), evens out the loudness (--normalize), scales it to 1920x1080 with
ffmpeg, renders the DealWalkthrough composition with Remotion (branded intro with the address or area, facts, price and spread; your
footage with a small logo; outro with the offer deadline and link), then uploads the MP4 and sets it as the deal's walkthrough video.
A hidden address is never put in the intro. Settings come from .env (SOCIAL_STUDIO_URL, SOCIAL_STUDIO_TOKEN; see .env.example).
Set REMOTION_BROWSER to a Chrome path if Remotion's own browser download stalls. Standard library only; needs ffmpeg and render/ installed.
"""
from __future__ import annotations

import argparse, json, os, re, shutil, subprocess, sys, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def env() -> dict:
    local = {}
    f = ROOT / ".env"
    if f.exists():
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                local[k.strip()] = v.strip().strip("\"'")
    return {k: os.environ.get(k, local.get(k, "")) for k in ("SOCIAL_STUDIO_URL", "SOCIAL_STUDIO_TOKEN", "REMOTION_BROWSER")}


def call(url: str, token: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method="POST" if body is not None else "GET",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error", "")
        except Exception:
            msg = ""
        raise SystemExit(f"The dashboard said {e.code}: {msg or e.reason}")


def money(v):
    return f"${round(v):,}" if isinstance(v, (int, float)) else None


def facts_line(d: dict) -> str:
    parts = []
    if d.get("beds") is not None: parts.append(f"{d['beds']:g} bed")
    if d.get("baths") is not None: parts.append(f"{d['baths']:g} bath")
    if d.get("sqft"): parts.append(f"{round(d['sqft']):,} sqft")
    return " · ".join(parts)


def probe_seconds(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path, nargs="?")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--deal")
    ap.add_argument("--trim", help="start-end in seconds, e.g. 4.5-96")
    ap.add_argument("--normalize", action="store_true", help="even out the loudness (-16 LUFS)")
    ap.add_argument("--intro", type=float, default=4)
    ap.add_argument("--outro", type=float, default=5)
    ap.add_argument("--headline"); ap.add_argument("--location"); ap.add_argument("--facts"); ap.add_argument("--price"); ap.add_argument("--spread"); ap.add_argument("--rent")
    ap.add_argument("--offer-by"); ap.add_argument("--url")
    ap.add_argument("--no-publish", action="store_true")
    a = ap.parse_args()
    cfg = env()
    base = cfg["SOCIAL_STUDIO_URL"].rstrip("/") + "/api/dispo/yap" if cfg["SOCIAL_STUDIO_URL"] else ""

    if a.list:
        if not base or not cfg["SOCIAL_STUDIO_TOKEN"]: raise SystemExit("Set SOCIAL_STUDIO_URL and SOCIAL_STUDIO_TOKEN in .env first.")
        for d in call(base, cfg["SOCIAL_STUDIO_TOKEN"])["deals"]: print(f"{d['id']}  {d['status']:<10} {d['label']}")
        return 0
    if not a.video or not a.video.is_file(): raise SystemExit("Give the walkthrough video file (or --list).")
    if shutil.which("ffmpeg") is None: raise SystemExit("ffmpeg is not installed.")

    facts = {}
    if a.deal:
        if not base or not cfg["SOCIAL_STUDIO_TOKEN"]: raise SystemExit("Set SOCIAL_STUDIO_URL and SOCIAL_STUDIO_TOKEN in .env to use --deal.")
        facts = call(f"{base}?deal={a.deal}", cfg["SOCIAL_STUDIO_TOKEN"])
    headline = a.headline or facts.get("headline") or "New deal"
    slug = re.sub(r"[^a-z0-9]+", "-", headline.lower()).strip("-")[:40] or "deal"
    stage = ROOT / "render/public/deals" / slug
    stage.mkdir(parents=True, exist_ok=True)

    # 1. clean up: trim, even out the sound, conform to 1920x1080 H.264
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if a.trim:
        m = re.fullmatch(r"([\d.]+)-([\d.]+)", a.trim)
        if not m: raise SystemExit("--trim looks like 4.5-96")
        cmd += ["-ss", m.group(1), "-to", m.group(2)]
    cmd += ["-i", str(a.video), "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=yuv420p"]
    if a.normalize: cmd += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(stage / "clip.mp4")]
    print("Cleaning up the footage…"); subprocess.run(cmd, check=True)
    dur = probe_seconds(stage / "clip.mp4")

    # 2. props for the DealWalkthrough composition
    offer_by = a.offer_by
    if not offer_by and facts.get("offer_deadline"):
        from datetime import datetime, timezone
        try:
            from zoneinfo import ZoneInfo
            t = datetime.fromisoformat(facts["offer_deadline"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/Los_Angeles"))
            offer_by = t.strftime("%b %-d at %-I:%M %p PT")
        except Exception:
            pass
    props = {"clip": f"deals/{slug}/clip.mp4", "headline": headline, "location": a.location or facts.get("location"), "facts": a.facts or facts_line(facts),
             "price": a.price or money(facts.get("price")), "spread": a.spread or money(facts.get("spread")), "rent": a.rent or (money(facts.get("rent")) and money(facts.get("rent")) + "/mo"),
             "offerBy": offer_by, "url": (a.url or facts.get("url") or "jesemmhomeventures.com").replace("https://", "").replace("http://", ""),
             "clipDurationInSeconds": round(dur, 3), "introSeconds": a.intro, "outroSeconds": a.outro}
    props = {k: v for k, v in props.items() if v not in (None, "")}
    (stage / "props.json").write_text(json.dumps(props, indent=2))

    # 3. render
    out = ROOT / "out" / f"{slug}-walkthrough.mp4"
    out.parent.mkdir(exist_ok=True)
    rcmd = ["npx", "remotion", "render", "src/index.ts", "DealWalkthrough", str(out), f"--props=public/deals/{slug}/props.json"]
    if cfg["REMOTION_BROWSER"]: rcmd.append(f"--browser-executable={cfg['REMOTION_BROWSER']}")
    print("Rendering the branded video (a few minutes)…"); subprocess.run(rcmd, cwd=ROOT / "render", check=True)
    print(f"Rendered {out} ({out.stat().st_size/1e6:.1f} MB)")

    # 4. attach it to the deal
    if a.no_publish or not a.deal:
        print("Not published" + ("" if a.no_publish else " (no --deal given)") + ". Upload it from the deal's Video field in Dispo if you want it on the page.")
        return 0
    tok = cfg["SOCIAL_STUDIO_TOKEN"]
    prep = call(base, tok, {"action": "prepare", "deal_id": a.deal})
    req = urllib.request.Request(prep["signed_url"], data=out.read_bytes(), method="PUT", headers={"Content-Type": "video/mp4", "x-upsert": "false"})
    try:
        urllib.request.urlopen(req, timeout=900).read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Upload failed: {e.code} {e.read().decode()[:200]} (the file may be over the storage size limit)")
    res = call(base, tok, {"action": "register", "deal_id": a.deal, "path": prep["path"]})
    print("Attached to the deal as its walkthrough video:", res.get("video_url"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
