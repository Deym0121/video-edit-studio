#!/usr/bin/env python3
"""health — Edit Health: one report of everything that makes a viewer leave or the creator re-edit.

Every check below is something Lloyd caught by eye on editor_story (2026-10-20/21): words said twice,
clipped joins, dead air between cuts, an HDR file that plays "filtered", graphics over the face,
text under the TikTok/Reels buttons, no hook in the first second, audio too quiet, lip-sync drift.

Usage: health.py VIDEO [--quick]   → work/<name>/health.json (+ a printed list)
       --quick reuses literal.txt / soundcheck.json when they are newer than edl.json (no re-listening).
Each item: check · sev (3 fix before posting, 2 should fix, 1 nice to fix) · at (edited s) · src · en/tl text · fix.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vedit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FACEBOX = vedit.finder("facebox")  # Apple Vision on a Mac, OpenCV elsewhere
PY = sys.executable
PARTIAL = {"tag", "lockup", "thumb", "lower", "panel"}  # graphics that share the frame with the camera
# where the TikTok / Reels / Shorts interface sits on a 1080×1920 frame
UI_ZONES = {"right": (930, 880, 1080, 1660), "bottom": (0, 1580, 1080, 1920), "top": (0, 0, 1080, 150)}


def tc(t):
    return vedit.tc(t)


def item(check, sev, at, en, tl, src=None, fix=None, detail_en="", detail_tl=""):
    return dict(check=check, sev=sev, at=None if at is None else round(at, 2), src=None if src is None else round(src, 2),
                en=en, tl=tl, detail_en=detail_en, detail_tl=detail_tl, fix=fix)


class Edit:
    """The edited timeline as rendered: cold open first, then the body segments (source seconds)."""

    def __init__(self, wd):
        self.edl = vedit.jload(wd / "edl.json")
        self.segs = (self.edl.get("hook_segs") or []) + self.edl["segments"]
        self.offs, o = [], 0.0
        for a, b in self.segs:
            self.offs.append(o)
            o += b - a
        self.dur = o

    def src(self, t):
        for (a, b), of in zip(self.segs, self.offs):
            if of <= t < of + (b - a):
                return a + (t - of)
        return self.segs[-1][1]


def run_tool(tool, src):
    return subprocess.run([PY, str(ROOT / "tools" / tool), str(src)], capture_output=True, text=True, cwd=ROOT)


def fresh(f, edl_path):
    return f.exists() and f.stat().st_mtime >= edl_path.stat().st_mtime


def check_doubles(src, wd, quick):
    lit = wd / "literal.txt"
    if not (quick and fresh(lit, wd / "edl.json")):
        run_tool("literal.py", src)
    out = []
    for line in lit.read_text().splitlines() if lit.exists() else []:
        m = re.match(r"\s*(\d+):(\d+\.\d)\s+\((\d+):(\d+\.\d)\)", line)
        if not m or "·DBL" not in line:
            continue
        at, s = int(m[1]) * 60 + float(m[2]), int(m[3]) * 60 + float(m[4])
        for w in dict.fromkeys(re.findall(r"\[\[([^\]·]+)·DBL\]\]", line)):
            out.append(item("double", 3, at, f"Said twice: “{w}”", f"Nasabi nang dalawang beses: “{w}”", src=s,
                            detail_en="The literal (letter-by-letter) listen hears this word twice in a row.",
                            detail_tl="Narinig ng literal check na dalawang beses sunod-sunod.",
                            fix={"action": "ask", "text": f"May doble sa {tc(at)}: “{w}”. Tanggalin ang isa."}))
    return out


def check_joins(src, wd, quick):
    sc = wd / "soundcheck.json"
    if not (quick and fresh(sc, wd / "edl.json")):
        run_tool("soundcheck.py", src)
    out = []
    for i in vedit.jload(sc, []):
        if i["kind"] == "CUT":
            out.append(item("join", 2, i["out"], "A cut while the voice is loud — a word may be clipped",
                            "Naputol habang malakas ang boses — baka may salitang putol", src=i["src"],
                            fix={"action": "ask", "text": f"Pakinggan ang dugtungan sa {tc(i['out'])} — baka may putol na salita."}))
        elif i["kind"] == "REPEAT":
            out.append(item("double", 2, i["out"], f"Sounds repeated ({i['lag']} s apart)", f"Parang naulit ({i['lag']} s ang pagitan)",
                            src=i["src"], fix={"action": "ask", "text": f"Parang may naulit sa {tc(i['out'])}. Ayusin kung totoo."}))
        elif i["kind"] == "CHOPPY":
            out.append(item("choppy", 1, i["out"], "Choppy audio (noise-gate dropouts)", "Putol-putol ang tunog dito", src=i["src"]))
    return out


def check_dead_air(wd, ed, min_gap=0.9):
    """Quiet stretches longer than min_gap in the EDITED audio — also across joins (the 0:09 'dead air' case)."""
    db = np.load(wd / "energy.npy")
    live = db[db > -90]
    floor = np.percentile(live, 10) if len(live) else -60
    thr = max(floor + 10, np.percentile(db, 90) - 24)
    e, s = [], []
    for a, b in ed.segs:
        f0, f1 = int(round(a * 100)), int(round(b * 100))
        e.append(db[f0:f1])
        s.append(np.arange(f0, f1) / 100)
    e, s = np.concatenate(e), np.concatenate(s)
    quiet = e < thr
    out, k, n = [], 0, len(e)
    while k < n:
        if not quiet[k]:
            k += 1
            continue
        j = k
        while j < n and quiet[j]:
            j += 1
        if (j - k) / 100 >= min_gap and k > 0 and j < n:  # not the very start/end
            keep = slice(k + 12, j - 13)  # leave ≈0.25 s of breath
            fr = s[keep]
            ranges, r0 = [], None
            for q in range(len(fr)):
                if r0 is None:
                    r0 = fr[q]
                if q + 1 == len(fr) or fr[q + 1] - fr[q] > 0.015:
                    if fr[q] + 0.01 - r0 > 0.1:
                        ranges.append([round(float(r0), 2), round(float(fr[q] + 0.01), 2)])
                    r0 = None
            out.append(item("dead_air", 2, k / 100, f"{(j - k) / 100:.1f} s of dead air", f"{(j - k) / 100:.1f} s na walang nagsasalita",
                            src=float(s[k]), fix={"action": "tighten", "ranges": ranges} if ranges else None,
                            detail_en="Viewers swipe on silence. Tighten keeps a short breath.",
                            detail_tl="Nag-i-swipe ang viewers kapag tahimik. Ang Tighten ay nag-iiwan ng maikling hinga."))
        k = j
    return out


def check_colour(src, wd):
    out = []
    trc = vedit.probe(str(src)).get("trc")
    if trc in ("arib-std-b67", "smpte2084"):
        out.append(item("colour", 3, None, "HDR source — the render will look filtered", "HDR ang video — magmumukhang may filter",
                        detail_en="iPhone HDR plays differently once edited. Convert to natural colour (Apple's own conversion) before rendering.",
                        detail_tl="Iba ang pagpapakita ng iPhone HDR pagka-edit. I-convert sa natural na kulay (sariling conversion ng Apple) bago mag-render.",
                        fix={"action": "sdr"}))
    last = Path(vedit.jload(wd / "last_render.json", {}).get("path", ""))
    if last.is_file():
        r = subprocess.run([vedit.binpath("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=color_transfer", "-of", "csv=p=0", str(last)], capture_output=True, text=True)
        if r.stdout.strip() in ("arib-std-b67", "smpte2084"):
            out.append(item("colour", 3, None, "Last render is tagged HDR", "HDR ang huling render",
                            detail_en="Re-render after converting the source.", detail_tl="Mag-render ulit pagka-convert."))
    return out


def check_sync(src):
    d = json.loads(subprocess.run([vedit.binpath("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type,duration",
                                   "-of", "json", str(src)], capture_output=True, text=True).stdout or "{}")
    v = [float(s["duration"]) for s in d.get("streams", []) if s.get("codec_type") == "video" and s.get("duration")]
    a = [float(s["duration"]) for s in d.get("streams", []) if s.get("codec_type") == "audio" and s.get("duration")]
    if v and a and abs(v[0] - a[0]) > 0.1:
        return [item("sync", 2, None, f"Video and audio lengths differ by {abs(v[0] - a[0]):.2f} s — lips may drift",
                     f"Magkaiba ang haba ng video at audio ({abs(v[0] - a[0]):.2f} s) — baka hindi sabay ang bibig",
                     detail_en="Usually from joining clips video-only. Rejoin with a video+audio concat.",
                     detail_tl="Kadalasan dahil sa pagdugtong ng clips na video lang. I-join ulit kasama ang audio.")]
    return []


def frame_rgba(f, t, w=1080, h=1920):
    raw = subprocess.run([vedit.binpath("ffmpeg"), "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", str(f), "-frames:v", "1",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 4) if len(raw) == w * h * 4 else None


def check_graphics(src, wd, ed, dec):
    """Partial graphics (tags, lockups, thumbnail titles, lower cards): do they cover the face, or sit under the app buttons?"""
    out, todo = [], []
    tmp = wd / "health"
    tmp.mkdir(exist_ok=True)
    for o in dec.get("overlays", []):
        if o.get("kind") not in PARTIAL:
            continue
        f = ROOT / o["file"]
        if not f.exists():
            continue
        dt = min(max(0.6, o["dur"] * 0.5), 2.0)
        al = frame_rgba(f, dt)
        if al is None:
            continue
        a = al[..., 3] > 90 if f.suffix in (".mov", ".webm") else np.ones(al.shape[:2], bool)
        png = tmp / f"{o['id']}.png"
        subprocess.run([vedit.binpath("ffmpeg"), "-v", "error", "-y", "-ss", f"{ed.src(o['at'] + dt):.3f}", "-i", str(src),
                        "-frames:v", "1", "-vf", "scale=1080:1920", str(png)], capture_output=True)
        todo.append((o, a, png, o["at"] + dt))
    faces = {}
    if FACEBOX and todo:
        r = subprocess.run([*FACEBOX, *[str(p) for _, _, p, _ in todo]], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            try:
                j = json.loads(line)
                faces[j["file"]] = j["faces"]
            except ValueError:
                pass
    for o, a, png, t in todo:
        for x, y, w, h in faces.get(str(png), []):
            cover = a[max(0, y):y + h, max(0, x):x + w].mean() if w > 0 and h > 0 else 0
            if cover > 0.12:
                out.append(item("face", 3, t, f"“{o['id']}” covers {cover:.0%} of the face", f"Natatakpan ng “{o['id']}” ang {cover:.0%} ng mukha",
                                src=ed.src(t), fix={"action": "scene_off", "id": o["id"]},
                                detail_en="Move it to the top band / side, or switch it off.",
                                detail_tl="Ilipat sa itaas o sa gilid, o patayin."))
                break
        for zone, (x0, y0, x1, y1) in UI_ZONES.items():
            share = a[y0:y1, x0:x1].sum() / max(1, a.sum())
            if share > 0.06:
                out.append(item("safe_zone", 1, t, f"“{o['id']}” runs under the app's {zone} buttons/text",
                                f"Matatakpan ng app ({'kanan' if zone == 'right' else 'ibaba' if zone == 'bottom' else 'itaas'}) ang “{o['id']}”",
                                src=ed.src(t), detail_en="TikTok / Reels / Shorts put their UI there.",
                                detail_tl="Diyan nakalagay ang buttons ng TikTok / Reels / Shorts."))
    cap = dec.get("caption_size", 100)
    ys = [dec.get("caption_y", 1150)] + [z["y"] for z in dec.get("caption_zones", [])]
    if dec.get("captions", True) and max(ys) + cap * 1.3 > UI_ZONES["bottom"][1]:
        out.append(item("safe_zone", 2, None, "Captions sit in the app's bottom text area", "Nasa ibaba ang captions, matatakpan ng app",
                        detail_en="Keep captions above y ≈ 1500.", detail_tl="Ilagay ang captions sa taas ng y ≈ 1500."))
    return out


def check_hook(dec, ed):
    out = []
    firsts = [o["at"] for o in dec.get("overlays", []) if o.get("kind") != "look"]
    if not firsts or min(firsts) > 1.0:
        out.append(item("hook", 2, 0.0, "Nothing on screen in the first second", "Walang text o graphic sa unang segundo",
                        detail_en="Short-form viewers decide in 1–2 s. Add a hook title.",
                        detail_tl="Nagdedesisyon ang viewers sa unang 1–2 s. Lagyan ng hook title.", fix={"action": "hooklab"}))
    if not ed.edl.get("hook_segs") and not ed.edl.get("hook"):
        out.append(item("hook", 1, 0.0, "No cold open — try Hook Lab", "Walang cold open — subukan ang Hook Lab",
                        detail_en="Open with your strongest 2-second line from later in the video.",
                        detail_tl="Simulan sa pinakamalakas mong linya mula sa gitna ng video.", fix={"action": "hooklab"}))
    return out


def check_loudness(wd):
    last = Path(vedit.jload(wd / "last_render.json", {}).get("path", ""))
    if not last.is_file():
        return []
    r = subprocess.run([vedit.binpath("ffmpeg"), "-hide_banner", "-nostats", "-i", str(last), "-vn", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    out = []
    if i:
        lufs = float(i[-1])
        if lufs < -18 or lufs > -10:
            out.append(item("loudness", 2, None, f"Loudness {lufs:.0f} LUFS (social apps aim for −14)",
                            f"{lufs:.0f} LUFS ang lakas (−14 ang target ng social apps)",
                            detail_en="Too quiet loses viewers on phone speakers; too loud distorts.",
                            detail_tl="Kapag mahina, hindi marinig sa phone; kapag sobrang lakas, nagda-distort."))
    if p and float(p[-1]) > -0.5:
        out.append(item("loudness", 2, None, "Audio peaks hit 0 dB (clipping)", "Umaabot sa 0 dB ang tunog (clipping)"))
    return out


def main():
    src, wd, meta = vedit.ctx(sys.argv[1])
    quick = "--quick" in sys.argv
    dec = vedit.jload(wd / "decisions.json", {})
    ed = Edit(wd)
    t0 = time.time()
    items, checks = [], {}
    for name, fn in (("doubles", lambda: check_doubles(src, wd, quick)), ("joins", lambda: check_joins(src, wd, quick)),
                     ("dead_air", lambda: check_dead_air(wd, ed)), ("colour", lambda: check_colour(src, wd)),
                     ("sync", lambda: check_sync(src)), ("graphics", lambda: check_graphics(src, wd, ed, dec)),
                     ("hook", lambda: check_hook(dec, ed)), ("loudness", lambda: check_loudness(wd))):
        print(f"• {name}…", flush=True)
        try:
            got = fn()
        except Exception as e:  # one broken check must not hide the others
            got = [item("error", 1, None, f"{name} check failed: {e}", f"Hindi natapos ang {name} check: {e}")]
        checks[name] = len(got)
        items += got
    pen = sum({3: 8, 2: 4, 1: 1}[i["sev"]] for i in items)
    score = max(0, 100 - pen)
    items.sort(key=lambda i: (-i["sev"], i["at"] if i["at"] is not None else -1))
    rep = dict(score=score, ran_at=time.time(), secs=round(time.time() - t0, 1), duration=round(ed.dur, 1), checks=checks, items=items)
    vedit.jsave(wd / "health.json", rep)
    for i in items:
        print(f"{'!!!' if i['sev'] == 3 else ' ! ' if i['sev'] == 2 else ' · '} {tc(i['at']) if i['at'] is not None else '  —  '}  {i['en']}")
    print(f"✓ Edit Health {score}/100 · {len(items)} items · {rep['secs']} s → work/{wd.name}/health.json")


if __name__ == "__main__":
    main()
