"""Studio (step-by-step wizard) API: the project's look, preview frames, person cut-outs, uploads.

Used by server.py. Writes the same files Claude edits: work/<name>/decisions.json ("look" + caption keys)
and scenes.json (the hook graphic). See tools/brandkit.py for what each choice means at render time.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import brandkit  # noqa: E402
import vedit  # noqa: E402

WORK, INPUT = ROOT / "work", ROOT / "input"
PY = str(ROOT / ".venv" / "bin" / "python")
HOOK_TYPES = ("behind", "lockup", "thumb", "pov", "redact", "island", "search", "glitch", "flap", "price", "flip")
TONEMAP = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")

# ---------------------------------------------------------------- bounded background work (bug fix:
# opening a project used to start one ffmpeg per graphic at once — 20+ VP9 encodes in parallel)
_sem = threading.BoundedSemaphore(2)
# one edit at a time (bug fix: two quick clicks ran in parallel threads and the slower one wrote back a stale
# decisions.json, silently undoing the other click). server.py holds this around every mutating POST.
EDIT = threading.RLock()


def background(fn):
    def run():
        with _sem:
            fn()
    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------- helpers
def _dec(name):
    return vedit.jload(WORK / name / "decisions.json", {})


def _save_dec(name, dec):
    vedit.jsave(WORK / name / "decisions.json", dec)


def _scenes(name):
    p = WORK / name / "scenes.json"
    return json.loads(p.read_text()) if p.exists() else []


def _save_scenes(name, sc):
    (WORK / name / "scenes.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1))


def _words_out(name):
    wd = WORK / name
    edl = vedit.jload(wd / "edl.json", {})
    words = vedit.jload(wd / "transcript.json", {}).get("words", [])
    fixes = _dec(name).get("fixes", {})
    out = []
    for i, s, e in edl.get("words_out", []):
        t = fixes.get(str(i), words[i]["w"] if i < len(words) else "")
        if t:
            out.append((i, s, e, t))
    return out


def _clean(t):
    return re.sub(r"[^\w'’ -]", "", t, flags=re.UNICODE).strip()


def hook_scene(name):
    """The hook graphic: the scene the Studio marked with "hook", else (older edits) the first enabled
    behind/lockup/thumb scene that starts in the first ~6 s."""
    sc = _scenes(name)
    marked = next((s for s in sc if s.get("hook")), None)
    if marked:
        return marked
    ov = {o["id"]: o for o in _dec(name).get("overlays", [])}
    for s in sc:
        if s.get("type") in HOOK_TYPES and (ov.get(s["id"], {}).get("at", 0) < 6.0):
            return s
    return None


def hook_variant(h):
    """Hook scene → brandkit.HOOKS id (older scenes have no "hook" key: read it from the scene's fields)."""
    if h.get("hook"):
        return h["hook"]
    if h["type"] == "behind":
        return "behind_big" if h.get("kicker_big") else "behind_outline" if h.get("style") == "o" else "behind"
    toks = [t for r in h.get("rows", []) for t in (r if isinstance(r, list) else r.split())]
    if h["type"] == "lockup":
        return "lockup_tag" if any(t.startswith("G:") for t in toks) else "lockup"
    if h["type"] == "thumb":
        return "thumb_tone" if any(t.startswith("O:") for t in toks) and not any(t.startswith("H:") for t in toks) else "thumb"
    if h["type"] == "tag":
        return {"comment": "comment", "counter": "counter", "typing": "typing"}.get(h.get("style"), "typing")
    return h["type"]  # v7 hooks: the scene type is the variant id (pov, redact, island, …)


HOOK_STOP = set("""ang ng sa na ay mga kung yung so ako ka mo ko ni si siya sila kayo tayo kami natin namin ninyo nyo inyo
ito iyan yan yun iyon dito diyan doon lang naman pala talaga kasi pero tapos para kaya din rin pa ba po opo hindi wala
meron mayroon may nang dahil ganun ganito parang sobrang okay guys and the a an to of is it you i we they this that with
for are was have just like really yeah what about your from will there their then when also very anong ano bakit paano
gusto alam sabi ngayon lahat something actual actually thing things know want going make sure mong kong nating yang
tong yong nung kayong niyo thats its dont cant youre theres""".split())


def suggest_hook(name):
    """Hook word: one of Claude's caption keywords said early, else the video's most-repeated topic word
    (the old "longest word in the first 5 s" picked Tagalog verb forms like NAGKAKAROON)."""
    words = [(re.sub(r"[^\w-]", "", _clean(t)).lower(), s) for _, s, _, t in _words_out(name)]
    freq = {}
    for w, _ in words:
        freq[w] = freq.get(w, 0) + 1
    early = {w for w, s in words if s < 12}
    keys = [k for k in _dec(name).get("keywords", []) if k.lower() in early and not any(ch.isdigit() for ch in k)]
    if keys:  # Claude's keywords said early; the most repeated one is the topic
        return max(keys, key=lambda k: freq.get(k.lower(), 0)).upper()
    count = {w: n for w, n in freq.items() if len(w) >= 4 and w.isalpha() and w not in HOOK_STOP
             and not w.startswith(("nag", "mag", "naka", "maka", "pina", "pag"))}
    return max(count, key=lambda k: (count[k], -list(count).index(k))).upper() if count else "WATCH THIS"


# ---------------------------------------------------------------- look: read
def get_look(name):
    dec = _dec(name)
    lk = dec.get("look") or {}
    pos_y = dec.get("caption_y", 1150)
    pos = min(brandkit.CAPTION_POSITIONS, key=lambda p: abs(p["y"] - pos_y))["id"]
    style = "none" if dec.get("captions") is False else dec.get("caption_style", "pop")
    h = hook_scene(name)
    hook = (dict(type="none", text=suggest_hook(name), kicker="") if not h or h.get("disabled") else
            dict(type=hook_variant(h), id=h["id"], **_hook_words(h)))
    ex = brandkit.extras(dec)
    motion = set(ex["motion"])
    # mirror the real settings so the wizard always shows what will render
    motion = {m for m in motion if m not in ("punch", "glass", "sfx")}
    if dec.get("punch_in"):
        motion.add("punch")
    if dec.get("mograph_theme") == "glass":
        motion.add("glass")
    if dec.get("sfx", True) and dec.get("sfx_track", True):
        motion.add("sfx")
    elements = set(ex["elements"]) - {"progress", "keywords"}
    if dec.get("progress_bar"):
        elements.add("progress")
    if dec.get("keywords"):
        elements.add("keywords")
    ov = dec.get("overlays", [])
    edl = vedit.jload(WORK / name / "edl.json", {})
    cover = sum(o["dur"] for o in ov if o.get("kind") in ("full", "glass", "news", "panel", "shrink")) / max(1.0, edl.get("new_dur") or 1.0)
    return dict(
        palette=lk.get("palette", "bbd-orange"), accent=brandkit.accent(dec), fonts=lk.get("fonts", "signature"),
        caption=dict(style=style, size=dec.get("caption_size", 104 if style == "pop" else 80), pos=pos, y=pos_y),
        hook=hook,
        visuals=dict(lk.get("visuals") or {"density": "medium", "types": [v["id"] for v in brandkit.VISUALS[:6]]},
                     coverage=round(cover, 2), scenes=len([s for s in _scenes(name) if s.get("type") not in HOOK_TYPES + ("lockup",) and not s.get("hook")])),
        extras=dict(elements=sorted(elements), motion=sorted(motion)),
        keywords=dec.get("keywords", []), done=lk.get("done", []),
    )


def _hook_words(h):
    """Hook scene -> {text, kicker} for the wizard (inverse of set_hook)."""
    v7 = {"pov": ("text", None), "island": ("title", "body"), "search": ("query", None), "glitch": ("text", "kicker"),
          "flap": ("text", None), "price": ("new", "old"), "flip": ("fact", "myth")}
    if h["type"] in v7:
        a, b = v7[h["type"]]
        return dict(text=str(h.get(a, "")), kicker=str(h.get(b, "")) if b else "")
    if h["type"] == "redact":
        hid = re.findall(r"\[\[(.+?)\]\]", " ".join(h.get("lines", [])))
        return dict(text=hid[0] if hid else "", kicker=next((ln for ln in h.get("lines", []) if "[[" not in ln), ""))
    if h["type"] == "tag":
        return dict(text=re.sub(r"[*]", "", str(h.get("name", ""))), kicker=h.get("k", ""))
    if h.get("text"):
        return dict(text=h["text"], kicker=h.get("kicker", ""))
    if h["type"] == "thumb":
        rows = [re.sub(r"(^|\s)[A-Z]\d*:", r"\1", r if isinstance(r, str) else " ".join(r)).replace("_", " ") for r in h.get("rows", [])]
        tag = h.get("tag", "")
        return dict(text=" ".join(rows).strip(), kicker="" if tag == "New" else tag)
    text, kick = [], []
    for row in h.get("rows", []):
        for tok in (row if isinstance(row, list) else row.split()):
            if tok == "<":
                continue
            word = re.sub(r"^[A-Z]\d*:|@.*$", "", tok).replace("/", " ").replace("_", " ").strip()
            (kick if tok.startswith(("C:", "G:")) else text).append(word)
    return dict(text=" ".join(text).strip(), kicker=" ".join(kick).strip())


# ---------------------------------------------------------------- look: write
def _hook_phrases(name):
    wo = _words_out(name)
    if not wo:
        return None, None
    start = " ".join(_clean(t) for _, _, _, t in wo[:2]).strip()
    end_i = next((k for k, (_, s, _, _) in enumerate(wo) if s >= 4.8), min(len(wo) - 1, 10))
    end = " ".join(_clean(t) for _, _, _, t in wo[end_i:end_i + 2]).strip()
    return start, end


def hook_id(name):
    """Scene ids name files in the shared motion/renders/, so they must be unique across projects
    (bug fix: name[:6] gave IMG_7779 and IMG_7780 the same "img_77_hook" and they overwrote each other)."""
    slug = re.sub(r"[^a-z0-9]+", "", name.lower())[:10] or "video"
    return f"{slug}_{hashlib.md5(name.encode()).hexdigest()[:4]}_hook"


V7_HOOKS = ("pov", "redact", "island", "search", "glitch", "flap", "price", "flip")


def v7_hook_fields(typ, text, kicker):
    """Scene fields for a 2026 trend hook (mograph_more types), timed in seconds from the scene start."""
    t = text.strip() or "WATCH THIS"
    if typ == "pov":
        return dict(type="pov", text=t, at=0.0, y=236)
    if typ == "redact":
        return dict(type="redact", kicker=(kicker or "CLASSIFIED").upper(), lines=[kicker or "Ang sikreto ko:", f"[[{t}]]"] if kicker else [f"[[{t}]]"],
                    reveal_at=1.3, at=0.05, y=236, sfx=[[1.3, "swish"]])
    if typ == "island":
        return dict(type="island", icon="bell", title=t, body=kicker or "", time="now", at=0.05, sfx=[[0.05, "sw_air"]])
    if typ == "search":
        q = t.lower()
        return dict(type="search", query=q, suggestions=[q + " 2026", "paano " + q if not q.startswith("paano") else q + " libre", q + " tutorial"],
                    pick=0, at=0.05, y=236, sfx=[[0.5, "typing"]])
    if typ == "glitch":
        return dict(type="glitch", text=t.upper(), kicker=(kicker or "BREAKING").upper(), at=0.05, y=236, sfx=[[0.05, "sw_whip"]])
    if typ == "flap":
        return dict(type="flap", text=t.upper()[:12], at=0.05, y=236, sfx=[[0.05, "typing"]])
    if typ == "price":
        return dict(type="price", old=kicker or "₱1,100", new=t.upper(), badge="SAVE", at=0.05, new_at=0.7, y=236, sfx=[[0.7, "hit"]])
    if typ == "flip":
        return dict(type="flip", myth=kicker or "Akala mo…", fact=t, flip_at=1.4, at=0.05, y=236, sfx=[[1.4, "sw_whip"]])
    return None


def set_hook(name, hook):
    """Write the hook variant the Studio picked as a real scene (brandkit.HOOKS) — mograph renders it."""
    sc = _scenes(name)
    h = hook_scene(name)
    typ, text, kicker = hook.get("type", "behind"), (hook.get("text") or suggest_hook(name)).strip(), (hook.get("kicker") or "").strip()
    if typ == "none":
        if h:
            h["disabled"] = True
            _save_scenes(name, sc)
        return
    start, end = (h.get("start"), h.get("end") or h.get("until")) if h else _hook_phrases(name)
    if not start:
        return
    words = text.split()
    new = {"id": h["id"] if h else hook_id(name), "hook": typ, "start": start, "lead": 0.05}
    was_behind = bool(h) and h.get("type") == "behind" and not h.get("kicker_big")
    if typ in ("behind", "behind_outline"):
        new.update(type="behind", end=end, at=start, text=text.upper(), y=h.get("y", 205) if was_behind else 205,
                   size=h.get("size", 250) if was_behind else 250, caption="hide")
        if typ == "behind_outline":
            new["style"] = "o"
        if kicker:
            new.update(kicker=kicker, kicker_script=True, kicker_size=120)
    elif typ == "behind_big":  # newsroom thumbnail hook: big white line above the head, the word behind it
        new.update(type="behind", end=end, at=start, text=text.upper(), y=360, size=250, caption="hide")
        if kicker:
            new.update(kicker=kicker, kicker_big=True, kicker_size=96)
    elif typ in ("lockup", "lockup_tag"):
        big, rest = (words[-1], " ".join(words[:-1])) if len(words) > 1 else (text, "")
        rows = []
        if typ == "lockup_tag":
            rows.append([f"G:{kicker or 'NEW'}@0.05"])
        elif kicker:
            rows.append([f"C:{kicker}@0.05"])
        if rest:
            rows.append([f"S:{rest}@0.05"])
        rows.append([f"X:{big.upper()}@0.2"])
        new.update(type="lockup", until=end, y=230, rows=rows)
    elif typ in ("thumb", "thumb_tone"):
        mid = max(1, len(words) // 2)
        if typ == "thumb":  # last words in one colour box ("_" keeps them in the same box)
            rows = [" ".join(words[:mid]), "H:" + "_".join(words[mid:])] if len(words) > 1 else ["H:" + text.replace(" ", "_")]
        else:  # two-tone: white line, then the colour line
            rows = [" ".join(words[:mid]), " ".join("O:" + w for w in words[mid:])] if len(words) > 1 else ["O:" + text.replace(" ", "_")]
        new.update(type="thumb", until=end, tag=kicker or "New", rows=rows, sizes=[160, 190][: len(rows)], caption="hide")
    elif typ == "comment":  # a viewer's comment as the reason for the video
        new.update(type="tag", style="comment", until=end, icon="user", k=kicker or "@viewer", name=text,
                   y=250, caption="hide", sfx=[[0.0, "pop"]])
    elif typ == "counter":  # proof number counts up: ticks … ding
        ticks = [[round(0.3 + k * 0.075, 3), "tick"] for k in range(16)]
        new.update(type="tag", style="counter", until=end, icon="eye", k=kicker or "views in a week", name=text,
                   y=250, caption="hide", sfx=ticks + [[1.55, "ding"]])
    elif typ in V7_HOOKS:  # 2026 trend hooks (mograph_more) — seconds-timed, top band, captions hidden while up
        new.update(until=end, caption="hide", **v7_hook_fields(typ, text, kicker))
    elif typ == "typing":  # headline types out
        new.update(type="tag", style="typing", until=end, k=kicker, name=text, y=250, caption="hide", sfx=[[0.3, "type"]])
        if not kicker:
            new.pop("k")
    else:
        return
    if h:
        sc[sc.index(h)] = new
    else:
        sc.insert(0, new)
    _save_scenes(name, sc)


def set_look(name, body):
    dec = _dec(name)
    lk = dec.setdefault("look", {})
    if "palette" in body:
        lk["palette"] = body["palette"]
        pal = next((p for p in brandkit.PALETTES if p["id"] == body["palette"]), None)
        lk["accent"] = body.get("accent") or (pal["accent"] if pal else brandkit.DEFAULT_ACCENT)
    elif body.get("accent"):
        lk["accent"] = body["accent"]
    if "fonts" in body:
        lk["fonts"] = body["fonts"]
    if "caption" in body:
        c = body["caption"]
        if c.get("style") == "none":
            dec["captions"] = False
        elif c.get("style"):
            dec["captions"] = True
            dec["caption_style"] = c["style"]
        if c.get("size"):
            dec["caption_size"] = int(c["size"])
        if c.get("pos"):
            p = next((p for p in brandkit.CAPTION_POSITIONS if p["id"] == c["pos"]), None)
            if p:
                dec["caption_y"] = p["y"]
                dec.pop("caption_zones", None)  # one clear position for the whole video
    if "visuals" in body:
        lk["visuals"] = {k: v for k, v in body["visuals"].items() if k in ("density", "types")}
    if "extras" in body:
        ex = body["extras"]
        el, mo = set(ex.get("elements", [])), set(ex.get("motion", []))
        lk["extras"] = dict(elements=sorted(el), motion=sorted(mo))
        dec["progress_bar"] = "progress" in el
        if "keywords" in el and not dec.get("keywords") and lk.get("keywords_backup"):
            dec["keywords"] = lk.pop("keywords_backup")
        if "keywords" not in el and dec.get("keywords"):
            lk["keywords_backup"] = dec.pop("keywords")
        if "punch" in mo:
            dec["punch_in"] = dec.get("punch_in") or 1.07
        else:
            dec.pop("punch_in", None)
        if "glass" in mo:
            if dec.get("mograph_theme") != "news":
                dec["mograph_theme"] = "glass"
        elif dec.get("mograph_theme") == "glass":
            dec.pop("mograph_theme")
        dec["sfx"] = "sfx" in mo
        if "hookzoom" not in mo:
            stash_hook_zoom(dec)
        elif not dec.get("hook_zoom") and lk.get("hook_zoom_backup"):
            dec["hook_zoom"] = lk.pop("hook_zoom_backup")
    if "keywords" in body:
        dec["keywords"] = [k for k in body["keywords"] if k]
    if body.get("done"):
        lk["done"] = sorted(set(lk.get("done", [])) | {body["done"]})
    _save_dec(name, dec)
    if "hook" in body:
        set_hook(name, body["hook"])
    return get_look(name)


def stash_hook_zoom(dec):
    """Hook zoom switched off: park its timings in look so ticking it again brings them back."""
    if dec.get("hook_zoom"):
        dec.setdefault("look", {})["hook_zoom_backup"] = dec.pop("hook_zoom")
        return True
    return False


def render_flags(name):
    """Extra args / follow-ups for the render pipeline that come from the look (sfx.py riser, hook zoom)."""
    ex = brandkit.extras(_dec(name))
    return dict(riser="riser" in ex["motion"], hookzoom="hookzoom" in ex["motion"], sfx="sfx" in ex["motion"])


# ---------------------------------------------------------------- preview frames + person cut-out
def frame(name, t, w=360):
    wd = WORK / name
    meta = vedit.jload(wd / "meta.json")
    out = wd / "studio" / f"f_{t:.1f}_{w}.jpg"
    if out.exists():
        return out
    out.parent.mkdir(exist_ok=True)
    tm = TONEMAP if meta.get("trc") == "arib-std-b67" else ""
    subprocess.run([vedit.binpath("ffmpeg"), "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", meta["src"], "-frames:v", "1",
                    "-vf", f"{tm}scale={w}:-2", "-q:v", "3", str(out)], capture_output=True)
    return out if out.exists() else None


def cutout(name, t, w=360):
    """PNG of just the person (transparent background) — Apple Vision person segmentation (tools/bin/personmask)."""
    wd = WORK / name
    meta = vedit.jload(wd / "meta.json")
    out = wd / "studio" / f"cut_{t:.1f}_{w}.png"
    if out.exists():
        return out
    pm = ROOT / "tools" / "bin" / "personmask"
    src = frame(name, t, w)
    if not src or not pm.exists():
        return None
    h = round(w * meta["h"] / meta["w"] / 2) * 2
    ff = vedit.binpath("ffmpeg")
    raw = subprocess.run([ff, "-v", "error", "-i", str(src), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgra", "-"],
                         capture_output=True).stdout
    mask = subprocess.run([str(pm), str(w), str(h)], input=raw, capture_output=True).stdout
    if len(mask) < w * h:
        return None
    mp = out.with_suffix(".gray")
    mp.write_bytes(mask[: w * h])
    subprocess.run([ff, "-y", "-v", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-i", str(mp),
                    "-filter_complex", f"[0:v]scale={w}:{h},format=rgba[c];[1:v]format=gray[m];[c][m]alphamerge", str(out)],
                   capture_output=True)
    mp.unlink(missing_ok=True)
    return out if out.exists() else None


# ---------------------------------------------------------------- uploads → transcribe
imports: dict[str, dict] = {}
ON_IMPORTED: list = []  # callbacks(name) after a new upload is transcribed + planned
TOSDR = ROOT / "tools" / "bin" / "tosdr"


def to_sdr(src):
    """iPhone HDR (HLG + Dolby Vision) → SDR with Apple's own tone mapping, audio untouched. An HLG render plays as
    "HDR" and looks filtered next to the camera (DESIGN_SYSTEM.md); the original is kept in work/<name>/source_hdr.*"""
    v, out = src.with_name(src.stem + ".sdrv.mov"), src.with_name(src.stem + ".sdr.mov")
    subprocess.run([str(TOSDR), str(src), str(v)], check=True, capture_output=True)
    subprocess.run([vedit.binpath("ffmpeg"), "-y", "-v", "error", "-i", str(v), "-i", str(src), "-map", "0:v", "-map", "1:a:0?",
                    "-c", "copy", str(out)], check=True, capture_output=True)
    keep = WORK / src.stem
    keep.mkdir(parents=True, exist_ok=True)
    src.rename(keep / f"source_hdr{src.suffix}")
    v.unlink()
    return out.rename(src.with_suffix(".mov"))


def upload(filename, stream, length):
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(filename).stem).strip("_").lower() or "video"
    ext = Path(filename).suffix.lower() if Path(filename).suffix.lower() in (".mov", ".mp4", ".m4v") else ".mov"
    dest, n = INPUT / f"{stem}{ext}", 2
    while dest.exists() or (WORK / dest.stem).exists():
        dest, n = INPUT / f"{stem}_{n}{ext}", n + 1
    INPUT.mkdir(exist_ok=True)
    left = length
    with open(dest, "wb") as f:
        while left > 0:
            chunk = stream.read(min(1 << 20, left))
            if not chunk:
                break
            f.write(chunk)
            left -= len(chunk)
    name = dest.stem
    imports[name] = {"state": "running", "log": "transcribing…"}

    def run():
        nonlocal dest
        if vedit.probe(str(dest)).get("trc") in ("arib-std-b67", "smpte2084") and TOSDR.exists():
            imports[name] = {"state": "running", "log": "iPhone HDR → natural colour…"}
            try:
                dest = to_sdr(dest)
            except subprocess.CalledProcessError as e:
                imports[name] = {"state": "error", "log": (e.stderr or b"")[-600:].decode(errors="replace")}
                return
            imports[name] = {"state": "running", "log": "transcribing…"}
        r = subprocess.run([PY, str(ROOT / "tools" / "vedit.py"), "transcribe", str(dest)], capture_output=True, text=True, cwd=ROOT)
        if r.returncode == 0:
            p = subprocess.run([PY, str(ROOT / "tools" / "vedit.py"), "plan", str(dest)], capture_output=True, text=True, cwd=ROOT)
            if p.returncode == 0:
                for fn in ON_IMPORTED:  # default brand kit, auto-edit (studio_pro)
                    try:
                        fn(name)
                    except Exception as e:  # noqa: BLE001 — a kit problem must not fail the import
                        print(f"⚠ after import: {e}", flush=True)
            imports[name] = {"state": "done" if p.returncode == 0 else "error", "log": (p.stdout + p.stderr)[-400:]}
        else:
            imports[name] = {"state": "error", "log": (r.stdout + r.stderr)[-600:]}
    threading.Thread(target=run, daemon=True).start()
    return dict(name=name, file=dest.name)


def catalog_with_samples():
    """Catalog + a real past render for every visual type that has one (scans work/*/scenes.json)."""
    cat = brandkit.catalog()
    renders = ROOT / "motion" / "renders"
    found = {}
    for sp in sorted(WORK.glob("*/scenes.json"), key=lambda p: -p.stat().st_mtime):
        try:
            for s in json.loads(sp.read_text()):
                t = s.get("type")
                if t and t not in found and not s.get("disabled") and any((renders / f"{s['id']}.{x}").exists() for x in ("mp4", "mov")):
                    found[t] = s["id"]
        except Exception:
            continue
    for v in cat["visuals"]:
        v["sample"] = v.get("sample") if v.get("sample") and any((renders / f"{v['sample']}.{x}").exists() for x in ("mp4", "mov")) else found.get(v["id"])
    for h in cat["hooks"]:
        h["sample"] = found.get(h["id"])
    return cat


# ---------------------------------------------------------------- studio settings (product name is editable)
SETTINGS = ROOT / "studio.json"
DEFAULT_SETTINGS = {"name": "Joshua Ladero Studio"}


def settings():
    try:
        return {**DEFAULT_SETTINGS, **json.loads(SETTINGS.read_text())}
    except (FileNotFoundError, ValueError):
        return dict(DEFAULT_SETTINGS)


def set_settings(body):
    st = settings()
    name = re.sub(r"\s+", " ", str(body.get("name") or "")).strip()[:40]
    if name:
        st["name"] = name
    for k in ("default_kit", "claude_bin", "auto_edit"):  # brand kit for new uploads · Claude Code path · auto-edit uploads
        if k in body:
            if body[k] in (None, ""):
                st.pop(k, None)
            else:
                st[k] = body[k]
    SETTINGS.write_text(json.dumps(st, ensure_ascii=False, indent=1))
    return st


# ---------------------------------------------------------------- previews you can hear: real sfx.py sounds
SFX_DIR = ROOT / "motion" / "sfx_preview"


def sfx_wav(name):
    """One sound from tools/sfx.py as a WAV, at the level it gets in the render (so the preview mix is honest)."""
    import numpy as np
    import wave
    import sfx
    out = SFX_DIR / f"{name}.wav"
    if out.exists():
        return out
    if name == "riser":
        snd, gain = sfx.s_riser_suspense(3.0), sfx.GAIN["riser"]
    elif name in sfx.SOUNDS:
        snd, gain = sfx.SOUNDS[name](), sfx.GAIN[name]
    else:
        return None
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    x = np.clip(snd * gain, -0.98, 0.98)
    tmp = out.with_suffix(".tmp")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sfx.SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    tmp.rename(out)
    return out


def _tm(path):
    """Tonemap prefix for browser previews of iPhone HLG files (renders stay HLG; only previews are SDR)."""
    return TONEMAP if vedit.probe(str(path)).get("trc") == "arib-std-b67" else ""


def hook_clip(name, secs=6.0):
    """First seconds of the EDITED video (with sound) + a moving cut-out of the person (VP9 alpha), so the Studio
    can play every hook with text truly behind the speaker. Built once per edit, in the background."""
    wd = WORK / name
    edl = vedit.jload(wd / "edl.json", {})
    if not edl.get("segments"):
        return dict(ready=False)
    key = f"{int((wd / 'edl.json').stat().st_mtime)}"
    st = wd / "studio"
    bg, cut = st / f"hookbg_{key}.mp4", st / f"hookcut_{key}.webm"
    if bg.exists() and cut.exists():
        return dict(ready=True, bg=f"/media/{name}/s/{bg.name}", cut=f"/media/{name}/s/{cut.name}", dur=secs)
    job = f"hookclip:{name}"
    if _jobs.get(job) != "running":
        _jobs[job] = "running"

        def run():
            try:
                _make_hook_clip(wd, edl, bg, cut, secs)
            finally:
                _jobs[job] = "done"
        background(run)
    return dict(ready=False, bg=f"/media/{name}/s/{bg.name}" if bg.exists() else None)


_jobs: dict[str, str] = {}


def _make_hook_clip(wd, edl, bg, cut, secs):
    import subprocess as sp
    meta = vedit.jload(wd / "meta.json")
    ff, pm = vedit.binpath("ffmpeg"), ROOT / "tools" / "bin" / "personmask"
    bg.parent.mkdir(exist_ok=True)
    segs, left = [], secs
    for a, b in edl["segments"]:
        if left <= 0:
            break
        segs.append((a, min(b, a + left)))
        left -= min(b, a + left) - a
    fc = "".join(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}];[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}];"
                 for i, (a, b) in enumerate(segs))
    fc += "".join(f"[v{i}][a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=1[cv][ca];[cv]{_tm(meta['src'])}scale=540:960,fps=30[v]"
    tmp = bg.with_suffix(".tmp.mp4")
    sp.run([ff, "-y", "-v", "error", "-i", meta["src"], "-filter_complex", fc, "-map", "[v]", "-map", "[ca]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", str(tmp)], capture_output=True)
    if not tmp.exists():
        return
    tmp.rename(bg)
    if not pm.exists():
        return
    mk = bg.with_suffix(".mask.gray")
    with open(mk, "wb") as mf:
        p1 = sp.Popen([ff, "-v", "error", "-i", str(bg), "-vf", "scale=360:640", "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=sp.PIPE)
        p2 = sp.Popen([str(pm), "360", "640"], stdin=p1.stdout, stdout=mf)
        p1.stdout.close()
        p2.wait()
        p1.wait()
    tmpc = cut.with_suffix(".tmp.webm")
    sp.run([ff, "-y", "-v", "error", "-i", str(bg), "-f", "rawvideo", "-pix_fmt", "gray", "-s", "360x640", "-r", "30", "-i", str(mk),
            "-filter_complex", "[0:v]format=rgba[c];[1:v]scale=540:960,format=gray,gblur=sigma=1[m];[c][m]alphamerge",
            "-an", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "1800k", "-deadline", "realtime", "-cpu-used", "8",
            "-auto-alt-ref", "0", str(tmpc)], capture_output=True)
    mk.unlink(missing_ok=True)
    if tmpc.exists():
        tmpc.rename(cut)


def render_clip(name, at, dur):
    """A moment of the project's LAST RENDER (graphics + voice + sound effects) as a small browser clip."""
    wd = WORK / name
    src = Path(vedit.jload(wd / "last_render.json", {}).get("path", ""))
    if not src.name or not src.exists():
        return None
    st = wd / "studio"
    st.mkdir(exist_ok=True)
    a0 = max(0.0, at - 0.3)
    out = st / f"clip_{src.stem}_{a0:.2f}_{dur + 0.6:.2f}.mp4"
    if not out.exists():
        tmp = out.with_suffix(".tmp.mp4")
        subprocess.run([vedit.binpath("ffmpeg"), "-y", "-v", "error", "-ss", f"{a0:.3f}", "-t", f"{dur + 0.6:.3f}", "-i", str(src),
                        "-vf", f"{_tm(src)}scale=540:-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp)], capture_output=True)
        if not tmp.exists():
            return None
        tmp.rename(out)
    return f"/media/{name}/s/{out.name}"


def sample_clip(scene_id):
    """Library sample with sound: the scene as it played in the past video it came from."""
    for sp_ in WORK.glob("*/scenes.json"):
        try:
            if not any(s.get("id") == scene_id for s in json.loads(sp_.read_text())):
                continue
        except ValueError:
            continue
        o = next((o for o in _dec(sp_.parent.name).get("overlays", []) if o["id"] == scene_id), None)
        if o:
            return render_clip(sp_.parent.name, o["at"], o["dur"])
    return None
