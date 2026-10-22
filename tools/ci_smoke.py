"""CI smoke test — the path a creator takes, on a 15-second test clip, on whatever OS this runs on (GitHub's Windows
runner, or a Mac): finders → transcribe → plan → render → style reference → the Studio's pages → one motion graphic.

usage:  python tools/ci_smoke.py [--keep] [--no-motion]     (after setup; VEDIT_WHISPER=tiny keeps the download small)
Everything it makes is named ci_smoke and removed at the end (unless --keep). Exit 1 if any step failed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vedit  # noqa: E402

NAME = "ci_smoke"
CLIP = ROOT / "input" / f"{NAME}.mp4"
PORT = 8799  # not the Studio's own 8765, which may be running
TMP = Path(tempfile.mkdtemp(prefix="ci_smoke_"))
FAILS = []


def step(name, fn):
    t = time.time()
    try:
        fn()
        print(f"✓ {name} ({time.time() - t:.0f}s)", flush=True)
    except Exception as e:  # noqa: BLE001 — report every step, then fail at the end
        FAILS.append(name)
        print(f"✗ {name}: {e}", flush=True)


def run(*cmd, inp=None):
    r = subprocess.run([str(c) for c in cmd], input=inp, capture_output=True)
    if r.returncode:
        out = (r.stdout[-1500:] + r.stderr[-2500:]).decode("utf-8", "replace")
        raise RuntimeError(f"exit {r.returncode}: {' '.join(str(c) for c in cmd[:5])}\n{out}")
    return r.stdout


def vedit_cli(*args):
    return run(sys.executable, "-X", "utf8", ROOT / "tools" / "vedit.py", *args).decode("utf-8", "replace")


def card():
    """A 1080×1920 title card (text for the text finder), saved as PNG."""
    im = Image.new("RGB", (1080, 1920), (24, 26, 32))
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(str(ROOT / "assets" / "fonts" / "InterTight-wght-800.ttf"), 120)
    d.text((540, 820), "SMOKE TEST", fill=(255, 255, 255), font=font, anchor="mm")
    d.text((540, 1000), "VIDEO EDIT", fill=(255, 170, 0), font=font, anchor="mm")
    im.save(TMP / "card.png")


def make_clip():
    card()
    vo = [ROOT / "docs" / "tutorial" / "vo" / f"{n:03d}.mp3" for n in (1, 2, 3)]
    ins = [a for f in vo for a in ("-i", f)]
    pads = ";".join(f"[{i + 1}:a]apad=pad_dur=1.2[a{i}]" for i in range(len(vo)))
    CLIP.parent.mkdir(exist_ok=True)
    run(vedit.binpath("ffmpeg"), "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-i", TMP / "card.png", *ins,
        "-filter_complex", pads + ";" + "".join(f"[a{i}]" for i in range(len(vo))) + f"concat=n={len(vo)}:v=0:a=1[a]",
        "-map", "0:v", "-map", "[a]", "-shortest", *vedit.h264("6M", 20), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", CLIP)
    assert CLIP.stat().st_size > 50_000, "test clip too small"


def finders():
    which = {n: vedit.finder(n) for n in ("facebox", "textbox", "personmask")}
    print("  finders: " + ", ".join(f"{n}={'missing' if not c else Path(c[-1]).name}" for n, c in which.items()))
    missing = [n for n, c in which.items() if not c]
    assert not missing, f"not installed: {missing}"
    fb = json.loads(run(*which["facebox"], TMP / "card.png").decode().splitlines()[0])
    assert "faces" in fb, fb
    tb = json.loads(run(*which["textbox"], TMP / "card.png").decode("utf-8").splitlines()[0])
    words = " ".join(x["t"] for x in tb["lines"]).upper()
    assert "SMOKE" in words, f"text finder read: {words!r}"
    w, h = 96, 160
    masks = run(*which["personmask"], w, h, inp=bytes(w * h * 4) * 2)
    assert len(masks) == w * h * 2, f"person cut-out returned {len(masks)} bytes"


def transcribe():
    vedit_cli("transcribe", CLIP, "--language", "en", "--no-fill")
    words = vedit.jload(vedit.WORK / NAME / "transcript.json")["words"]
    text = " ".join(w["w"] for w in words).lower()
    print(f"  {len(words)} words: {text[:90]}…")
    assert len(words) > 12, "too few words"


def plan_render():
    vedit_cli("plan", CLIP)
    out = vedit_cli("render", CLIP)
    made = [p for p in (ROOT / "output").glob(f"{NAME}*") if p.suffix == ".mp4"]
    assert made, f"no render in output/\n{out[-800:]}"
    dur = float(run(vedit.binpath("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", made[0]))
    print(f"  {made[0].name}: {dur:.1f}s")
    assert dur > 5


def style_reference():
    out = TMP / "ref"
    run(sys.executable, "-X", "utf8", ROOT / "tools" / "refstyle.py", "analyze", CLIP, "--out", out)
    st = json.loads((out / "style.json").read_text(encoding="utf-8"))
    assert (out / "sheet.jpg").exists() and st, "no style read"


def studio():
    env = dict(os.environ, VEDIT_PORT=str(PORT), PYTHONUTF8="1")
    log = open(TMP / "studio.log", "wb")
    srv = subprocess.Popen([sys.executable, "-X", "utf8", str(ROOT / "tools" / "vedit.py"), "studio", "--no-open"],
                           env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{PORT}"

    def get(path, kind="json"):
        with urllib.request.urlopen(base + path, timeout=120) as r:
            body = r.read()
            assert r.status == 200, f"{path} → {r.status}"
            return json.loads(body) if kind == "json" else body

    try:
        for _ in range(60):
            try:
                get("/api/settings")
                break
            except OSError:
                time.sleep(1)
        assert b"<html" in get("/", "raw").lower()
        get("/studio_pro.js", "raw")
        assert any(p["name"] == NAME for p in get("/api/projects")), "project not listed"
        get(f"/api/project/{NAME}")
        get(f"/api/project/{NAME}/look")
        get("/api/catalog")
        get("/api/refs")
        assert get(f"/media/{NAME}/frame.jpg?t=2&w=360", "raw")[:2] == b"\xff\xd8", "frame is not a JPEG"
        assert get(f"/media/{NAME}/cutout.png?t=2&w=360", "raw")[:4] == b"\x89PNG", "cut-out is not a PNG"
    except Exception:
        log.flush()
        print((TMP / "studio.log").read_text(encoding="utf-8", errors="replace")[-2500:])
        raise
    finally:
        srv.terminate()
        srv.wait(10)
        log.close()


def motion():
    page = sorted((ROOT / "motion" / "scenes").glob("gal_*.html"))
    assert page, "no gallery pages (run: python tools/mograph.py --gallery)"
    out = TMP / "mg.mp4"
    env = dict(os.environ, PATH=os.pathsep.join([str(vedit.node_dir()), str(Path(vedit.binpath("ffmpeg")).parent), os.environ["PATH"]]),
               HYPERFRAMES_SKIP_SKILLS="1")
    r = subprocess.run([vedit.npx(), "-y", "hyperframes", "render", str(ROOT / "motion"), "-c", f"scenes/{page[0].name}",
                        "-o", str(out), "--fps", "30", "--quiet", "--quality", "looks"],
                       cwd=ROOT / "motion", env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0 and out.exists(), f"exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-2500:]}"
    print(f"  {page[0].name} → {out.stat().st_size // 1024} KB")


def cleanup():
    for p in [CLIP, vedit.WORK / NAME, *(ROOT / "output").glob(f"{NAME}*"), TMP]:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()


def main():
    print(f"• {sys.platform} · Python {sys.version.split()[0]} · Whisper {vedit.FW_MODEL if not vedit.IS_MAC else vedit.MODEL}", flush=True)
    print(vedit_cli("doctor"), flush=True)
    step("test clip", make_clip)
    step("finders (faces · text · person cut-out)", finders)
    step("transcribe", transcribe)
    step("plan + render preview", plan_render)
    step("style reference", style_reference)
    step("Studio pages", studio)
    if "--no-motion" not in sys.argv:
        step("motion graphic (HyperFrames)", motion)
    if "--keep" not in sys.argv:
        cleanup()
    print(f"\n{'✗ failed: ' + ', '.join(FAILS) if FAILS else '✓ all steps passed'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
