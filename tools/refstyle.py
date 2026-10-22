#!/usr/bin/env python3
"""refstyle — learn a style from a video you like (any creator's): pacing, captions, colours, graphics and hook.

Only the style is kept: a contact sheet of small frames and a few numbers. The reference footage itself is never
used in an edit. The Studio turns one or more references into a look ("Make it my style"), mixing them per part.

  .venv/bin/python tools/refstyle.py analyze <video> [--out refs/<id>]   → style.json + sheet.jpg
  .venv/bin/python tools/refstyle.py look <refs/<id>/style.json> …        → the Studio look it maps to (JSON)
"""
import colorsys
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import brandkit  # noqa: E402
import vedit  # noqa: E402

TEXTBOX = ROOT / "tools" / "bin" / "textbox"
FACEBOX = ROOT / "tools" / "bin" / "facebox"
SPAN = 90.0     # seconds analysed (the opening of a short is where its style lives)
NFRAMES = 16


# ---------------------------------------------------------------- measuring
def cuts(src, span):
    """Cuts in the first `span` seconds, jump cuts included: frames whose change from the one before spikes well above
    the change around them (a plain scene threshold misses jump cuts, where the framing barely moves)."""
    r = subprocess.run([vedit.binpath("ffmpeg"), "-v", "error", "-t", f"{span:.2f}", "-i", str(src), "-an",
                        "-vf", "scale=160:-2,select='gte(scene,0)',metadata=print:file=-", "-f", "null", "-"], capture_output=True, text=True)
    ts = [float(t) for t in re.findall(r"pts_time:([0-9.]+)", r.stdout)]
    sc = [float(v) for v in re.findall(r"lavfi\.scene_score=([0-9.]+)", r.stdout)]
    n = min(len(ts), len(sc))
    if n < 10:
        return []
    ts, sc = np.array(ts[:n]), np.array(sc[:n])
    out, last = [], -1.0
    for i in range(1, n):
        local = np.median(sc[max(0, i - 15):i + 15])
        if sc[i] > max(.06, 5 * local) and ts[i] - last > .35:
            out.append(float(ts[i]))
            last = ts[i]
    return out


def frames(src, span, out):
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for k, t in enumerate(np.linspace(0.6, max(1.0, span - 0.4), NFRAMES)):
        f = out / f"f_{k:02d}.jpg"
        subprocess.run([vedit.binpath("ffmpeg"), "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
                        "-vf", "scale=540:-2", "-q:v", "3", str(f)], check=True)
        files.append((float(t), f))
    return files


def faces(files):
    """Which frames show a face (no face + text = a full-screen graphic page)."""
    if not FACEBOX.exists():
        return {}
    r = subprocess.run([str(FACEBOX)] + [str(f) for _, f in files], capture_output=True, text=True)
    out = {}
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        out[Path(d["file"]).name] = bool(d.get("faces"))
    return out


def text_lines(files):
    if not TEXTBOX.exists():
        return {}
    r = subprocess.run([str(TEXTBOX)] + [str(f) for _, f in files], capture_output=True, text=True)
    out = {}
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        out[Path(d["file"]).name] = d
    return out


def hexc(rgb):
    return "#" + "".join(f"{int(max(0, min(255, round(v)))):02X}" for v in rgb)


def colours(img, r):
    """Inside one text line: its text colour, a highlight colour (saturated words) and whether it sits on a box."""
    W, H = img.size
    x, y, w, h = r
    p = max(3, int(h * .25))
    box = np.asarray(img.crop((max(0, x - 1), max(0, y - 1), min(W, x + w + 1), min(H, y + h + 1))).convert("RGB")).reshape(-1, 3).astype(float)
    ring = np.asarray(img.crop((max(0, x - p), max(0, y - p), min(W, x + w + p), min(H, y + h + p))).convert("RGB")).astype(float)
    outer = np.asarray(img.crop((max(0, x - 3 * p), max(0, y - 3 * p), min(W, x + w + 3 * p), min(H, y + h + 3 * p))).convert("RGB")).astype(float)

    def edge(a):
        return np.concatenate([a[:2].reshape(-1, 3), a[-2:].reshape(-1, 3), a[:, :2].reshape(-1, 3), a[:, -2:].reshape(-1, 3)])
    bg, around = np.median(edge(ring), 0), np.median(edge(outer), 0)
    # a box: an even colour right behind the words that differs from the picture just outside it
    boxed = bool(edge(ring).std(0).mean() < 16 and np.abs(bg - around).mean() > 35)
    far = box[np.abs(box - bg).sum(1) > 90]  # the letters: far from the background around them
    if len(far) < 12:
        return None
    hsv = np.array([colorsys.rgb_to_hsv(*(c / 255)) for c in far[:: max(1, len(far) // 400)]])
    sat = (hsv[:, 1] > .45) & (hsv[:, 2] > .45)
    rgb = far[:: max(1, len(far) // 400)]
    base = np.median(rgb[~sat], 0) if (~sat).sum() > 6 else np.median(rgb, 0)
    hi = np.median(rgb[sat], 0) if sat.mean() > .12 else None
    return dict(text=hexc(base), highlight=hexc(hi) if hi is not None else None, boxed=boxed, box=hexc(bg) if boxed else None)


def caption_metrics(files, lines, face):
    caps, titles, pages, first_title, words, uppers, letters, ratios, cols = [], 0, 0, None, [], 0, 0, [], []
    for k, (t, f) in enumerate(files):
        d = lines.get(f.name)
        if not d or not d.get("lines"):
            continue
        W, H = d["w"], d["h"]
        img = Image.open(f)
        best, has_title = None, False
        for ln in d["lines"]:
            x, y, w, h = ln["r"]
            txt = ln["t"].strip()
            al = [c for c in txt if c.isalpha()]
            if ln["c"] < .5 or len(al) < 2 or h / H < .012:
                continue
            hn, cx, cy = h / H, (x + w / 2) / W, (y + h / 2) / H
            if hn >= .055:
                has_title = True
            if .015 <= hn < .09 and abs(cx - .5) < .28 and .1 < cy < .93 and (best is None or hn > best[0]):
                best = (hn, cy, txt, ln["r"])
        titles += has_title
        pages += face.get(f.name) is False and len(d["lines"]) >= 2
        if k == 0:
            first_title = has_title
        if best:
            hn, cy, txt, r = best
            caps.append((hn, cy))
            words.append(len(txt.split()))
            al = [c for c in txt if c.isalpha()]
            uppers += sum(c.isupper() for c in al)
            letters += len(al)
            ratios.append(r[2] / max(1, len(txt)) / max(1, r[3]))  # narrow letters → condensed font
            c = colours(img, r)
            if c:
                cols.append(c)
    n = max(1, len(files))
    if not caps:
        return dict(presence=0.0, titles=round(titles / n, 2), pages=round(pages / n, 2), first_title=bool(first_title))
    y = float(np.median([c[1] for c in caps]))
    hi = [c["highlight"] for c in cols if c["highlight"]]
    return dict(presence=round(len(caps) / n, 2), y=round(y, 3), size=round(float(np.median([c[0] for c in caps])), 4),
                position="top" if y < .36 else "middle" if y < .7 else "low",
                case="upper" if letters and uppers / letters > .75 else "lower" if letters and uppers / letters < .08 else "mixed",
                words=int(np.median(words)), narrow=round(float(np.median(ratios)), 2),
                boxed=round(sum(c["boxed"] for c in cols) / max(1, len(cols)), 2),
                color=max(set(c["text"] for c in cols), key=[c["text"] for c in cols].count) if cols else None,
                highlight=_mode_hue(hi), titles=round(titles / n, 2), pages=round(pages / n, 2), first_title=bool(first_title))


def _mode_hue(hexes):
    """The most common saturated colour among the highlights (grouped by hue)."""
    if not hexes:
        return None
    hs = [colorsys.rgb_to_hsv(*(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))) for h in hexes]
    bins = {}
    for hx, (hh, _, _) in zip(hexes, hs):
        bins.setdefault(round(hh * 12) % 12, []).append(hx)
    return max(bins.values(), key=len)[0]


def analyze(src, out):
    src, out = Path(src), Path(out)
    pr = vedit.probe(str(src))
    span = min(SPAN, pr["dur"])
    cs = cuts(src, span)
    files = frames(src, span, out / "frames")
    cap = caption_metrics(files, text_lines(files), faces(files))
    tiles = [Image.open(f).convert("RGB").resize((180, int(180 * pr["h"] / pr["w"]))) for _, f in files[:12]]
    th = tiles[0].size[1]
    sheet = Image.new("RGB", (180 * 6, th * 2), "black")
    for k, im in enumerate(tiles):
        sheet.paste(im, ((k % 6) * 180, (k // 6) * th))
    sheet.save(out / "sheet.jpg", quality=84)
    files[0][1].replace(out / "thumb.jpg") if files else None
    style = dict(source=src.name, duration=round(pr["dur"], 1), analysed=round(span, 1), vertical=pr["h"] > pr["w"],
                 pace=dict(cuts=len(cs), cuts_per_min=round(len(cs) / (span / 60), 1), avg_shot=round(span / (len(cs) + 1), 2)),
                 captions={k: v for k, v in cap.items() if k not in ("titles", "pages", "first_title")},
                 graphics=dict(titles=cap.get("titles", 0.0), pages=cap.get("pages", 0.0)), hook=dict(title_first=cap.get("first_title", False)),
                 accent=cap.get("highlight"))
    style["look"], style["why"] = to_look(style)
    style["summary"] = summary(style)
    vedit.jsave(out / "style.json", style)
    return style


# ---------------------------------------------------------------- style → Studio look
def _hsv(hx):
    return colorsys.rgb_to_hsv(*(int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)))


def palette_for(hx):
    """The Studio palette closest to a colour, or None (use it as a custom accent)."""
    h, s, v = _hsv(hx)
    if s < .25:
        return "mono"
    best, d = None, 1.0
    for p in brandkit.PALETTES:
        ph, ps, _ = _hsv(p["accent"])
        if ps < .25:
            continue
        dd = min(abs(h - ph), 1 - abs(h - ph))
        if dd < d:
            best, d = p["id"], dd
    return best if d < 18 / 360 else None


def to_look(st):
    """Studio choices for one reference + the reason for each, in plain words."""
    c, pace, g = st.get("captions", {}), st.get("pace", {}), st.get("graphics", {})
    look, why = {}, {}
    acc = st.get("accent") or c.get("highlight")
    if acc:
        pal = palette_for(acc)
        look["palette"], look["accent"] = (pal, None) if pal else (None, acc)
        why["palette"] = f"its highlight colour is {acc}"
    if c.get("presence", 0) < .2:
        look["caption"] = dict(style="none")
        why["caption"] = "it has almost no captions"
    else:
        if c.get("boxed", 0) >= .5:
            style = "box"
        elif c.get("case") == "lower":
            style = "lower"
        elif c.get("highlight") and c.get("words", 3) <= 3:
            style = "pop"
        elif c.get("highlight"):
            style = "highlight"
        elif c.get("case") == "upper" and c.get("words", 3) <= 3:
            style = "punch"
        elif c.get("case") == "upper":
            style = "outline"
        else:
            style = "classic"
        size = int(max(60, min(130, round(c.get("size", .04) * 1920 / .75 / 2) * 2)))
        look["caption"] = dict(style=style, pos=c.get("position", "middle"), size=size)
        why["caption"] = (f"{'boxed ' if style == 'box' else ''}{c.get('case', 'mixed')}-case captions, about {c.get('words', 3)} words at a time, "
                          f"{dict(top='above the head', middle='under the chin', low='in the lower third')[c.get('position', 'middle')]}")
    if c.get("case") == "upper":
        look["fonts"] = "punchy" if c.get("narrow", .6) < .5 else "classic"
    else:
        look["fonts"] = "signature"
    why["fonts"] = "condensed capitals" if look["fonts"] == "punchy" else "wide bold capitals" if look["fonts"] == "classic" else "clean sans-serif text"
    cpm = pace.get("cuts_per_min", 0)
    gr = max(g.get("titles", 0), g.get("pages", 0))
    dens = "heavy" if gr >= .4 or cpm >= 30 else "medium" if gr >= .18 or cpm >= 14 else "light"
    look["visuals"] = dict(density=dens)
    why["visuals"] = f"graphics on {round(gr * 100)}% of its frames, a cut every {pace.get('avg_shot', 0)} s"
    if st.get("hook", {}).get("title_first"):
        look["hook"] = "thumb"
        why["hook"] = "it opens on a big title"
    look["pace"] = "fast" if cpm >= 24 else "medium" if cpm >= 10 else "calm"
    why["pace"] = f"{pace.get('cuts_per_min', 0)} cuts a minute"
    return look, why


def summary(st):
    c, lk = st.get("captions", {}), st["look"]
    bits = []
    if lk.get("caption", {}).get("style") == "none":
        bits.append("no captions")
    else:
        bits.append(f"{c.get('case', 'mixed')}-case captions {dict(top='up top', middle='mid-frame', low='in the lower third')[c.get('position', 'middle')]}")
        if c.get("boxed", 0) >= .5:
            bits.append("on a box")
    if st.get("accent"):
        bits.append(f"{st['accent']} highlights")
    bits.append(f"a cut every {st['pace']['avg_shot']} s")
    bits.append({"heavy": "lots of on-screen text", "medium": "some on-screen text", "light": "little on-screen text"}[lk["visuals"]["density"]])
    if lk.get("hook"):
        bits.append("opens on a big title")
    s = ", ".join(bits)
    return s[0].upper() + s[1:] + "."


PARTS = ("colours", "captions", "fonts", "graphics", "hook", "pace")


def mix(styles, picks):
    """One look from several references: `picks` says which reference each part comes from ({part: ref id})."""
    by = {s["id"]: s for s in styles}
    first = styles[0]["id"] if styles else None
    body, notes = {}, []
    for part in PARTS:
        st = by.get(picks.get(part) or first)
        if not st:
            continue
        lk, why = st["look"], st.get("why", {})
        if part == "colours" and (lk.get("palette") or lk.get("accent")):
            body.update({"palette": lk["palette"]} if lk.get("palette") else {"accent": lk["accent"]})
            notes.append(("colours", st["name"], why.get("palette", "")))
        elif part == "captions" and lk.get("caption"):
            body["caption"] = lk["caption"]
            notes.append(("captions", st["name"], why.get("caption", "")))
        elif part == "fonts" and lk.get("fonts"):
            body["fonts"] = lk["fonts"]
            notes.append(("fonts", st["name"], why.get("fonts", "")))
        elif part == "graphics" and lk.get("visuals"):
            body["visuals"] = lk["visuals"]
            notes.append(("graphics", st["name"], why.get("visuals", "")))
        elif part == "hook" and lk.get("hook"):
            body["hook"] = lk["hook"]
            notes.append(("hook", st["name"], why.get("hook", "")))
        elif part == "pace":
            body["pace"] = lk.get("pace")
            notes.append(("pace", st["name"], why.get("pace", "")))
    return body, notes


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "analyze":
        out = Path(a[a.index("--out") + 1]) if "--out" in a else ROOT / "refs" / re.sub(r"[^a-z0-9]+", "-", Path(a[1]).stem.lower()).strip("-")
        st = analyze(a[1], out)
        print(json.dumps(st, indent=1))
    elif len(a) >= 2 and a[0] == "look":
        for f in a[1:]:
            st = vedit.jload(Path(f), {})
            print(json.dumps(to_look(st), indent=1))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
