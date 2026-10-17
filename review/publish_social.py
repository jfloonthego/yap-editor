#!/usr/bin/env python3
"""Send a finished reel to Social Studio (the Jesemm dashboard) as drafts in Review & approve.

Nothing is posted: the dashboard adds the video to the brand's library and makes one draft per
channel, and a person approves and schedules them there. Standard library only.

    python3 review/publish_social.py out/take-a-reel.mp4 \
        --headline "the edit is not the hard part" --caption "Why does every edit take 3 hours? ..." \
        --hashtags "realestate,wholesaling" --platforms facebook,instagram

Settings come from the environment or .env (see .env.example):
    SOCIAL_STUDIO_URL    https://rei.jesemm.com
    SOCIAL_STUDIO_TOKEN  copy from Social Studio -> Setup -> Connections -> Reel editor (Yap)
    SOCIAL_BRAND         the brand's name in Social Studio, e.g. "Jesemm Home Ventures"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

NAMES = ("SOCIAL_STUDIO_URL", "SOCIAL_STUDIO_TOKEN", "SOCIAL_BRAND")
MAX_BYTES = 200 * 1024 * 1024


def config() -> dict:
    local = {}
    env = Path(".env")
    if env.exists():
        for raw in env.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                local[k.strip()] = v.strip().strip("\"'")
    return {n: os.environ.get(n, local.get(n, "")) for n in NAMES}


def call(url: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error", "")
        except Exception:
            msg = ""
        raise SystemExit(f"Social Studio said {e.code}: {msg or e.reason}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--headline", default="")
    ap.add_argument("--caption", default="", help="post text; without it only the video is added to the library")
    ap.add_argument("--hashtags", default="", help="comma or space separated")
    ap.add_argument("--platforms", default="facebook,instagram")
    ap.add_argument("--brand", default=None, help="overrides SOCIAL_BRAND")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = config()
    brand = a.brand or cfg["SOCIAL_BRAND"]
    missing = [n for n in ("SOCIAL_STUDIO_URL", "SOCIAL_STUDIO_TOKEN") if not cfg[n]] + ([] if brand else ["SOCIAL_BRAND"])
    if missing:
        raise SystemExit("Missing settings: " + ", ".join(missing) + " (set them in .env)")
    if not a.video.is_file() or a.video.suffix.lower() != ".mp4":
        raise SystemExit(f"Not an .mp4 file: {a.video}")
    size = a.video.stat().st_size
    if size > MAX_BYTES:
        raise SystemExit(f"{a.video} is {size/1e6:.0f} MB; the limit is 200 MB.")
    base = cfg["SOCIAL_STUDIO_URL"].rstrip("/") + "/api/social/yap"
    tok = cfg["SOCIAL_STUDIO_TOKEN"]
    platforms = [p.strip() for p in a.platforms.split(",") if p.strip()]
    if a.dry_run:
        print(f"Would upload {a.video} ({size/1e6:.1f} MB) to {base} for brand {brand!r}, platforms {platforms}")
        return 0

    prep = call(base, tok, {"action": "prepare", "brand": brand})
    up = urllib.request.Request(prep["signed_url"], data=a.video.read_bytes(), method="PUT",
                                headers={"Content-Type": "video/mp4", "x-upsert": "false"})
    try:
        urllib.request.urlopen(up, timeout=600).read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Upload failed: {e.code} {e.read().decode()[:200]}")
    res = call(base, tok, {"action": "register", "brand": brand, "path": prep["path"], "headline": a.headline,
                           "caption": a.caption, "hashtags": a.hashtags, "platforms": platforms})
    print(f"Added to Social Studio: {res.get('drafts', 0)} draft(s) for {', '.join(res.get('platforms', []) or ['no channels'])}.")
    if res.get("note"):
        print("Note:", res["note"])
    print("Review and approve:", res.get("review_url"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
