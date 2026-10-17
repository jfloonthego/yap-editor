#!/usr/bin/env python3
"""The Yap worker: edits the videos you add in the dashboard (Social Studio -> Create -> Reel editor).

It waits for jobs from the dashboard, and for each one: downloads your raw video(s), has the dashboard transcribe them,
asks the AI editor for the cut, cuts and renders the branded video, and uploads the result. The dashboard then shows it
(and, for reels, puts drafts in Review & approve). You never run it by hand after the one-time install:

    python3 scripts/worker.py --install      # checks the tools, starts it, and makes it start at every login (macOS)
    python3 scripts/worker.py --uninstall    # stop and remove
    python3 scripts/worker.py                # run in this window (also what a cloud container runs)

Settings come from .env (SOCIAL_STUDIO_URL, SOCIAL_STUDIO_TOKEN; see .env.example). Needs ffmpeg, Node 18+ and Python 3.
Standard library only. The same code runs on a Mac or in the Dockerfile at the top of this repo.
"""
from __future__ import annotations

import argparse, json, os, platform, re, shutil, subprocess, sys, threading, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
POLL = 10          # seconds between checks for work
LABEL = "com.jesemm.yap-worker"


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


CFG = env()
BASE = CFG["SOCIAL_STUDIO_URL"].rstrip("/") + "/api/social/yap"


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def call(path: str, body: dict | None = None, data: bytes | None = None, ctype: str = "application/json", timeout: int = 180) -> dict:
    url = BASE + path
    payload = data if data is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=payload, method="POST" if payload is not None else "GET", headers={"Authorization": f"Bearer {CFG['SOCIAL_STUDIO_TOKEN']}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error", "")
        except Exception:
            msg = ""
        raise RuntimeError(f"The dashboard said {e.code}: {msg or e.reason}")


def run(cmd: list[str], cwd: Path | None = None, extra_env: dict | None = None) -> None:
    e = dict(os.environ, npm_config_cache=str(ROOT / ".npm-cache"))   # a private npm cache: a root-owned ~/.npm cannot break installs
    if extra_env:
        e.update(extra_env)
    r = subprocess.run(cmd, cwd=cwd or ROOT, env=e, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {(r.stderr or r.stdout).strip()[-400:]}")


def probe(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True, check=True).stdout.strip())


def browser_args() -> list[str]:
    b = CFG["REMOTION_BROWSER"]
    if not b and platform.system() == "Darwin" and Path("/Applications/Google Chrome.app").exists():
        b = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    return [f"--browser-executable={b}"] if b else []


def ensure_render_deps() -> None:
    if not (ROOT / "render/node_modules").exists():
        log("First run: installing the video renderer (a few minutes)")
        run(["npm", "install", "--no-audit", "--no-fund"], cwd=ROOT / "render")


def render(composition: str, props_rel: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["npx", "remotion", "render", "src/index.ts", composition, str(out), f"--props={props_rel}", *browser_args()], cwd=ROOT / "render")


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=600) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)


def upload_result(job_id: str, mp4: Path) -> dict:
    prep = call("/jobs", {"action": "prepare", "job_id": job_id})
    req = urllib.request.Request(prep["signed_url"], data=mp4.read_bytes(), method="PUT", headers={"Content-Type": "video/mp4", "x-upsert": "false"})
    try:
        urllib.request.urlopen(req, timeout=900).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Upload failed ({e.code}). The video may be over the storage size limit.")
    return call("/jobs", {"action": "complete", "job_id": job_id, "path": prep["path"]})


def say(job_id: str, msg: str) -> None:
    log(msg)
    try:
        call("/jobs", {"action": "progress", "job_id": job_id, "message": msg})
    except Exception:
        pass


# ---- a social reel -------------------------------------------------------------------------------------------------
def audio_for(video: Path, dest: Path) -> bytes:
    for bitrate, rate in (("32k", "16000"), ("24k", "16000"), ("16k", "12000")):
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", rate, "-b:a", bitrate, str(dest)])
        data = dest.read_bytes()
        if len(data) <= 4_300_000:
            return data
    raise RuntimeError("That video is too long to transcribe (about 20 minutes is the most). Trim it and add it again.")


def venv_python() -> str:
    v = ROOT / ".venv/bin/python"
    return str(v) if v.exists() else sys.executable


def transcribe_take(jid: str, tid: str, video: Path, work: Path) -> list:
    """The dashboard transcribes with OpenAI Whisper; if that fails (for example the account has no credits) a locally installed Whisper is used."""
    try:
        data = audio_for(video, work / f"take-{tid}.mp3")
        return call(f"/jobs/transcribe?job={jid}&take={tid}", data=data, ctype="audio/mpeg")["words"]
    except Exception as first:  # noqa: BLE001
        say(jid, "Online transcription unavailable, trying the Whisper installed on this computer")
        out = work / f"take-{tid}.local.json"
        r = subprocess.run([venv_python(), "pipeline/transcribe.py", str(video), "-o", str(out)], cwd=ROOT, capture_output=True, text=True)
        if r.returncode == 0 and out.exists():
            return json.loads(out.read_text())["words"]
        raise RuntimeError(f"{first} Local transcription isn't installed either. Fix: add credits to the OpenAI account (a few minutes of speech costs a cent or two), or run: python3 scripts/worker.py --install-transcription")


def do_reel(job: dict, work: Path) -> Path:
    jid = job["id"]
    takes = {}
    words: dict = job.get("words") or {}
    for t in job["takes"]:
        if not t.get("url"):
            raise RuntimeError(f"Could not get take {t['id']} from storage.")
        ext = Path(t["name"]).suffix.lower() or ".mp4"
        say(jid, f"Downloading {t['name']}")
        dest = work / f"take-{t['id']}{ext}"
        download(t["url"], dest)
        takes[t["id"]] = dest
        if not words.get(t["id"]):
            say(jid, f"Listening to {t['name']} (transcribing)")
            words[t["id"]] = transcribe_take(jid, t["id"], dest, work)
    say(jid, "The AI editor is deciding the cut")
    plan = call("/jobs", {"action": "plan", "job_id": jid, "words": words})["plan"]
    headline = (job.get("headline") or plan.get("headline") or "").strip()

    slug = f"job-{jid[:8]}"
    cuts = {"version": 1, "slug": slug, "fps": 30, "headline": headline, "takes": {}, "segments": []}
    for tid, path in takes.items():
        wpath = work / f"take-{tid}.words.json"
        wpath.write_text(json.dumps({"version": 1, "words": words.get(tid, [])}))
        cuts["takes"][tid] = {"path": str(path), "words": str(wpath)}
    cuts["segments"] = [{k: v for k, v in s.items() if v is not None} for s in plan["segments"]]
    (work / "cuts.json").write_text(json.dumps(cuts, indent=2))
    say(jid, "Cutting the video")
    run([sys.executable, "pipeline/assemble.py", str(work / "cuts.json")])
    say(jid, "Rendering the branded video (a few minutes)")
    out = ROOT / "out" / f"{slug}.mp4"
    render("LandscapeOnBlack", f"public/reels/{slug}/props.json", out)
    return out


# ---- a Dispo walkthrough -------------------------------------------------------------------------------------------
def do_deal(job: dict, work: Path) -> Path:
    from deal_video import facts_line, money  # same helpers as the command-line tool
    jid = job["id"]
    t = job["takes"][0]
    say(jid, f"Downloading {t['name']}")
    raw = work / ("raw" + (Path(t["name"]).suffix.lower() or ".mp4"))
    download(t["url"], raw)
    slug = f"deal-{jid[:8]}"
    stage = ROOT / "render/public/deals" / slug
    stage.mkdir(parents=True, exist_ok=True)
    say(jid, "Cleaning up the footage")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=yuv420p", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(stage / "clip.mp4")])
    d = job.get("deal") or {}
    offer_by = None
    if d.get("offer_deadline"):
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            offer_by = datetime.fromisoformat(d["offer_deadline"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/Los_Angeles")).strftime("%b %-d at %-I:%M %p PT")
        except Exception:
            pass
    props = {"clip": f"deals/{slug}/clip.mp4", "headline": d.get("headline") or "New deal", "location": d.get("location"), "facts": facts_line(d), "price": money(d.get("price")), "spread": money(d.get("spread")),
             "rent": (money(d.get("rent")) + "/mo") if d.get("rent") else None, "offerBy": offer_by, "url": (d.get("url") or "").replace("https://", "").replace("http://", "") or "jesemmhomeventures.com",
             "clipDurationInSeconds": round(probe(stage / "clip.mp4"), 3), "introSeconds": 4, "outroSeconds": 5}
    (stage / "props.json").write_text(json.dumps({k: v for k, v in props.items() if v not in (None, "")}, indent=2))
    say(jid, "Rendering the branded video (a few minutes)")
    out = ROOT / "out" / f"{slug}.mp4"
    render("DealWalkthrough", f"public/deals/{slug}/props.json", out)
    return out


def process(job: dict) -> None:
    jid = job["id"]
    work = ROOT / "work" / jid
    work.mkdir(parents=True, exist_ok=True)
    try:
        ensure_render_deps()
        out = do_deal(job, work) if job["mode"] == "deal" else do_reel(job, work)
        say(jid, "Uploading the finished video")
        upload_result(jid, out)
        log(f"Job {jid[:8]} done")
    except Exception as e:  # noqa: BLE001  (anything: report it to the dashboard so it shows "Needs attention")
        log(f"Job {jid[:8]} failed: {e}")
        try:
            call("/jobs", {"action": "fail", "job_id": jid, "error": str(e)[:500]})
        except Exception:
            pass
    finally:
        shutil.rmtree(work, ignore_errors=True)


def heartbeat(stop: threading.Event) -> None:
    while not stop.wait(30):
        try:
            call("/jobs", {"action": "ping"}, timeout=20)
        except Exception:
            pass


def loop(once: bool = False) -> int:
    for need in ("ffmpeg", "ffprobe", "npm"):
        if shutil.which(need) is None:
            print(f"Missing {need}. Install it first (on a Mac: brew install ffmpeg node).", file=sys.stderr)
            return 2
    if not (CFG["SOCIAL_STUDIO_URL"] and CFG["SOCIAL_STUDIO_TOKEN"]):
        print("Set SOCIAL_STUDIO_URL and SOCIAL_STUDIO_TOKEN in .env (copy the lines from Social Studio -> Setup -> Connections -> Reel editor).", file=sys.stderr)
        return 2
    log(f"Yap worker started, watching {BASE}")
    stop = threading.Event()
    threading.Thread(target=heartbeat, args=(stop,), daemon=True).start()
    while True:
        try:
            got = call("/jobs", {"action": "claim"}, timeout=60)
            if got.get("job"):
                log(f"Picked up job {got['job']['id'][:8]} ({got['job']['mode']})")
                process(got["job"])
                if once:
                    return 0
                continue
            if once:
                log("No jobs waiting.")
                return 0
        except Exception as e:  # noqa: BLE001
            log(f"Could not reach the dashboard: {e}")
        time.sleep(POLL)


# ---- one-time install (macOS: starts at login and restarts if it stops) -------------------------------------------------
def plist_path() -> Path:
    return Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"


def install() -> int:
    if not (CFG["SOCIAL_STUDIO_URL"] and CFG["SOCIAL_STUDIO_TOKEN"]):
        print("First put the three lines from Social Studio -> Setup -> Connections -> Reel editor into the .env file in this folder, then run this again.")
        return 2
    for need, how in (("ffmpeg", "brew install ffmpeg"), ("node", "brew install node"), ("python3", "brew install python")):
        if shutil.which(need) is None:
            print(f"Missing {need}. Install it with: {how}   then run this again.")
            return 2
    print("Checking the connection to your dashboard…")
    try:
        call("/jobs", {"action": "ping"}, timeout=30)
    except Exception as e:  # noqa: BLE001
        print("Could not sign in to the dashboard:", e)
        return 2
    print("Installing the video renderer (first time only, a few minutes)…")
    ensure_render_deps()
    if platform.system() != "Darwin":
        print("Connected. On this computer start it with:  python3 scripts/worker.py  (or use the Dockerfile for a server).")
        return 0
    log_file = Path.home() / "Library/Logs/yap-worker.log"
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{sys.executable}</string><string>{ROOT / 'scripts/worker.py'}</string></array>
  <key>WorkingDirectory</key><string>{ROOT}</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{log_file}</string><key>StandardErrorPath</key><string>{log_file}</string>
</dict></plist>
"""
    plist_path().parent.mkdir(parents=True, exist_ok=True)
    plist_path().write_text(plist)
    subprocess.run(["launchctl", "unload", str(plist_path())], capture_output=True)
    r = subprocess.run(["launchctl", "load", "-w", str(plist_path())], capture_output=True, text=True)
    if r.returncode != 0:
        print("Could not start it automatically:", r.stderr.strip())
        return 1
    print(f"Done. The editor is running and will start by itself whenever you log in. Look for a green 'online' light in Social Studio (give it a minute).\nLog file: {log_file}\nTo remove it later: python3 scripts/worker.py --uninstall")
    return 0


def install_transcription() -> int:
    """Optional: Whisper on this computer, used when online transcription is unavailable (no OpenAI credits)."""
    venv = ROOT / ".venv"
    if not venv.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = str(venv / "bin/pip")
    pkg = "mlx-whisper" if platform.system() == "Darwin" and platform.machine() == "arm64" else "faster-whisper"
    print(f"Installing {pkg} (a few minutes; the speech model downloads the first time it is used)…")
    r = subprocess.run([pip, "install", pkg])
    print("Done." if r.returncode == 0 else "That did not work; see the messages above.")
    return r.returncode


def uninstall() -> int:
    subprocess.run(["launchctl", "unload", "-w", str(plist_path())], capture_output=True)
    plist_path().unlink(missing_ok=True)
    print("The editor was stopped and will no longer start at login.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="handle one waiting job, then exit (for testing)"); ap.add_argument("--install-transcription", action="store_true", help="install Whisper on this computer as a fallback"); ap.add_argument("--install", action="store_true"); ap.add_argument("--uninstall", action="store_true")
    a = ap.parse_args()
    sys.exit(install_transcription() if a.install_transcription else install() if a.install else uninstall() if a.uninstall else loop(a.once))
