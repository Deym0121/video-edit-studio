#!/usr/bin/env python3
"""Manual transcript editor for vedit projects.

Open http://localhost:8765 — pick a video, click words to listen, select ranges to
remove/restore, fix caption text, then Save (re-plans instantly) and Render.
Everything is written to work/<name>/decisions.json, the same file Claude edits.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import vedit  # noqa: E402
sys.path.insert(0, str(Path(__file__).parent))
import studio_api  # noqa: E402
import studio_brief  # noqa: E402  (brief + style references)  (Studio wizard: look, frames, cut-outs, uploads)
import studio_pro  # noqa: E402  (v2: Health, notes, Claude, Hook Lab, Post Kit, Brand Kits)
from urllib.parse import parse_qs  # noqa: E402

WORK, OUT, HERE = ROOT / "work", ROOT / "output", Path(__file__).parent
PY = str(ROOT / ".venv" / "bin" / "python")
PORT = 8765
jobs: dict[str, dict] = {}  # name -> {"state", "log"}


def project(name):
    wd = WORK / name
    meta = vedit.jload(wd / "meta.json")
    if not meta or not (wd / "transcript.json").exists():
        raise FileNotFoundError(name)
    return wd, meta


def ensure_proxy(name):
    """Small H.264 copy of the original so any browser can play and seek it."""
    wd, meta = project(name)
    px = wd / "proxy.mp4"
    if px.exists():
        return "ready"
    job = jobs.get(f"proxy:{name}")
    if job and job["state"] == "running":
        return "preparing"
    jobs[f"proxy:{name}"] = {"state": "running", "log": ""}

    def run():
        tmp = wd / "proxy.tmp.mp4"
        r = subprocess.run([vedit.binpath("ffmpeg"), "-y", "-v", "error", "-i", meta["src"],
                            "-vf", "scale=-2:960" if meta["h"] >= meta["w"] else "scale=960:-2",
                            "-c:v", "h264_videotoolbox", "-b:v", "2500k", "-g", "15",
                            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            tmp.rename(px)
            jobs[f"proxy:{name}"] = {"state": "done", "log": ""}
        else:
            jobs[f"proxy:{name}"] = {"state": "error", "log": r.stderr[-2000:]}
    threading.Thread(target=run, daemon=True).start()
    return "preparing"


history: dict[str, list] = {}
future: dict[str, list] = {}
THUMB_EVERY, THUMB_W, THUMB_COLS = 2.0, 72, 25


def peaks(name):
    """Waveform: 25 values/second, 0..1, from the 10 ms energy file."""
    import numpy as np
    wd, _ = project(name)
    db = np.load(wd / "energy.npy")
    n = len(db) // 4
    m = db[: n * 4].reshape(n, 4).max(1)
    return [round(float(v), 2) for v in np.clip((m + 60) / 55, 0, 1)]


def ensure_thumbs(name):
    wd, meta = project(name)
    th, px = wd / "thumbs.jpg", wd / "proxy.mp4"
    th_h = round(THUMB_W * meta["h"] / meta["w"] / 2) * 2
    n = int(meta["dur"] // THUMB_EVERY) + 1
    info = dict(url=f"/media/{name}/thumbs.jpg", every=THUMB_EVERY, w=THUMB_W, h=th_h, cols=THUMB_COLS, n=n)
    if th.exists():
        return dict(info, ready=True)
    if not px.exists() or jobs.get(f"thumbs:{name}", {}).get("state") == "running":
        return dict(info, ready=False)
    jobs[f"thumbs:{name}"] = {"state": "running"}

    def run():
        rows = (n + THUMB_COLS - 1) // THUMB_COLS
        subprocess.run([vedit.binpath("ffmpeg"), "-y", "-v", "error", "-i", str(px), "-vf",
                        f"fps=1/{THUMB_EVERY},scale={THUMB_W}:{th_h},tile={THUMB_COLS}x{rows}",
                        "-frames:v", "1", "-q:v", "4", str(th)])
        jobs[f"thumbs:{name}"] = {"state": "done"}
    threading.Thread(target=run, daemon=True).start()
    return dict(info, ready=False)


def write_removed(dec, ids):
    old = {}
    for r in dec.get("remove", []):
        for i in range(r["from"], r["to"] + 1):
            old[i] = r.get("reason", "")
    out = []
    for a, b in ranges(ids):
        out.append({"from": a, "to": b, "reason": old.get(a) or "manual edit"})
    dec["remove"] = out


def op(name, body):
    """One editor action → decisions.json (with undo history) → re-plan."""
    wd, meta = project(name)
    p = wd / "decisions.json"
    raw = p.read_text() if p.exists() else "{}"
    kind = body.get("type")
    if kind in ("undo", "redo"):
        src, dst = (history, future) if kind == "undo" else (future, history)
        if not src.get(name):
            return load(name)
        dst.setdefault(name, []).append(raw)
        p.write_text(src[name].pop())
    else:
        history.setdefault(name, []).append(raw)
        future[name] = []
        dec = json.loads(raw)
        words = vedit.jload(wd / "transcript.json")["words"]
        rm = {i for r in dec.get("remove", []) for i in range(r["from"], r["to"] + 1)}
        fixes = dec.setdefault("fixes", {})
        if kind == "cut":
            dec.setdefault("cut_ranges", []).append(
                {"start": round(body["start"], 3), "end": round(body["end"], 3), "reason": "manual cut (editor)"})
        elif kind == "remove_words":
            rm |= set(body["ids"])
            write_removed(dec, rm)
        elif kind == "restore":
            a, b, s0, s1 = body.get("after", -1), body.get("before", -1), body["src_start"], body["src_end"]
            if a >= 0:
                rm -= set(range(a + 1, b))
            rm -= {w["i"] for w in words if s0 - 0.05 <= (w["s"] + w["e"]) / 2 <= s1 + 0.05}
            write_removed(dec, rm)
            dec["cut_ranges"] = [c for c in dec.get("cut_ranges", []) if c["end"] <= s0 or c["start"] >= s1]
        elif kind in ("trim_cut", "trim_keep"):
            a, b = sorted((round(body["a"], 3), round(body["b"], 3)))
            sub = lambda lst: [r for x in lst for r in (
                [x] if x["end"] <= a or x["start"] >= b else
                ([dict(x, end=a)] if x["start"] < a else []) + ([dict(x, start=b)] if x["end"] > b else []))]
            if kind == "trim_cut":
                dec["keep_ranges"] = sub(dec.get("keep_ranges", []))
                dec.setdefault("cut_ranges", []).append({"start": a, "end": b, "reason": "trimmed in editor"})
            else:
                dec["cut_ranges"] = sub(dec.get("cut_ranges", []))
                dec.setdefault("keep_ranges", []).append({"start": a, "end": b, "reason": "extended in editor"})
                rm -= {w["i"] for w in words if a <= (w["s"] + w["e"]) / 2 <= b}
                write_removed(dec, rm)
        elif kind == "tuning":
            v = float(body["keep_pause"])
            dec["tuning"] = dict(dec.get("tuning", {}), keep_pause=round(v, 2), max_pause=round(v + 0.25, 2))
        elif kind == "caption":
            ids = body["ids"]
            for k, i in enumerate(ids):
                fixes[str(i)] = body["text"] if k == 0 else ""
        vedit.jsave(p, dec)
    r = subprocess.run([PY, str(ROOT / "tools" / "vedit.py"), "plan", meta["src"]],
                       capture_output=True, text=True, cwd=ROOT)
    msg = (r.stdout + r.stderr).strip()
    if kind == "remove_words":  # the planner never splices inside continuous voice — say so instead of failing silently
        segs = vedit.jload(wd / "edl.json", {}).get("segments", [])
        words_ = vedit.jload(wd / "transcript.json")["words"]
        still = [words_[i]["w"] for i in body["ids"] if i < len(words_)
                 and any(a <= (words_[i]["s"] + words_[i]["e"]) / 2 <= b for a, b in segs)]
        if still:
            msg += ("\n⚠ Not cut: “" + " ".join(still[:6]) + "” — the voice runs straight through it, so a clean cut "
                    "isn't possible there. Select the whole phrase or sentence instead.")
    if (wd / "scenes.json").exists():  # keep every motion graphic glued to its words after the edit
        g = subprocess.run([PY, str(ROOT / "tools" / "mograph.py"), meta["src"], "--no-render"],
                           capture_output=True, text=True, cwd=ROOT)
        msg += "\n" + "\n".join(l for l in (g.stdout + g.stderr).splitlines() if l.startswith("⚠"))
    out = load(name)
    out["msg"] = msg.strip()[-400:]
    return out


def review_state(name):
    wd, _ = project(name)
    return vedit.jload(wd / "review.json", {"part": {}, "scene": {}, "issue": {}})


def set_review(name, body):
    """Approve / reject / reopen one part (content cut), scene (motion graphic) or QC issue."""
    wd, meta = project(name)
    rv = review_state(name)
    kind, key, state = body["kind"], str(body["key"]), body.get("state", "open")
    bucket = rv.setdefault(kind, {})
    if state == "open":
        bucket.pop(key, None)
    else:
        bucket[key] = {"state": state, "note": body.get("note", "")}
    vedit.jsave(wd / "review.json", rv)
    msg = ""
    if kind == "scene":  # a rejected scene is switched off in scenes.json; reopening switches it back on
        sp = wd / "scenes.json"
        if sp.exists():
            scenes = json.loads(sp.read_text())
            for sc in scenes:
                if sc.get("id") == key:
                    if state == "rejected":
                        sc["disabled"] = True
                    else:
                        sc.pop("disabled", None)
            sp.write_text(json.dumps(scenes, ensure_ascii=False, indent=1))
            g = subprocess.run([PY, str(ROOT / "tools" / "mograph.py"), meta["src"], "--no-render"],
                               capture_output=True, text=True, cwd=ROOT)
            msg = "\n".join(l for l in (g.stdout + g.stderr).splitlines() if l.startswith("⚠"))
    out = load(name)
    out["msg"] = msg
    return out


def tsec(s):
    m = re.match(r"(\d+):(\d+(?:\.\d+)?)", s)
    return int(m.group(1)) * 60 + float(m.group(2)) if m else 0.0


def qc_issues(name):
    """Possible problems for the reviewer, read from the QC files the tools write (literal / wordcheck /
    splicecheck / review.md). Each has an edited-timeline time so the editor can jump and listen."""
    wd, _ = project(name)
    out = []
    lit = wd / "literal.txt"
    if lit.exists():
        for line in lit.read_text().splitlines():
            m = re.match(r"\s*(\d+:\d+\.\d)\s", line)
            if m and "·DBL" in line:
                for w in re.findall(r"\[\[([^\]·]+)·DBL\]\]", line):
                    out.append(dict(kind="double", sev=3, at=tsec(m.group(1)), title=f"Posibleng doble: “{w}”",
                                    detail="Narinig nang dalawang beses ng literal check."))
    wc = wd / "wordcheck.txt"
    if wc.exists():
        for line in wc.read_text().splitlines():
            m = re.match(r"(\d+:\d+\.\d)\s+expected “(.+?)”\s+· literal heard: (.*)", line)
            if m and m.group(3).strip() in ("—", "-", ""):
                out.append(dict(kind="missing", sev=2, at=tsec(m.group(1)), title=f"Baka putol/kulang: “{m.group(2)}”",
                                detail="Hindi narinig ng literal check ang salitang ito."))
    sp = wd / "splicecheck.txt"
    if sp.exists():
        lines = sp.read_text().splitlines()
        for k, line in enumerate(lines):
            m = re.match(r"(\d+:\d+\.\d) CUT\s+src ([\d.]+)→([\d.]+)", line)
            if m:
                script = next((l.split(":", 1)[1].strip() for l in lines[k + 1:k + 3] if l.strip().startswith("script")), "")
                heard = next((l.split(":", 1)[1].strip() for l in lines[k + 1:k + 3] if l.strip().startswith("heard")), "")
                out.append(dict(kind="join", sev=1, at=tsec(m.group(1)), title="Dugtungan — pakinggan",
                                detail=f"{script}  ·  narinig: {heard}"))
    rv = wd / "review.md"
    if rv.exists():
        txt = rv.read_text()
        m = re.search(r"\*\*Suspiciously long words.*?\*\*(.*)", txt)
        if m:
            for w, t in re.findall(r"“(.+?)” orig (\d+:\d+\.\d)", m.group(1)):
                out.append(dict(kind="long", sev=1, src=tsec(t), at=None, title=f"Mahabang salita: “{w}”",
                                detail=f"Baka may nakatagong retake sa orig {t}."))
    for x in out:
        x["key"] = f"{x['kind']}:{x.get('at') if x.get('at') is not None else 's' + str(x.get('src'))}:{x['title']}"
    return sorted(out, key=lambda x: (x.get("at") if x.get("at") is not None else 9e9))


def scene_label(sc):
    """Readable card title: lockup tokens ("S:hirap pa rin/sa pag-edit?@nahihirapan") -> plain words."""
    if sc.get("rows"):
        toks = [t for r in sc["rows"] for t in (r if isinstance(r, list) else [r]) if t != "<"]
        label = " ".join(re.sub(r"^[A-Z]\d*:|@.*$", "", t).replace("/", " ") for t in toks)
    elif sc["type"] == "behind":
        label = f'{sc.get("kicker", "")} {sc.get("text", "")}'
    else:
        label = sc.get("title") or sc.get("kicker") or sc.get("big") or ""
    return re.sub(r"\s+", " ", re.sub(r"[*_]", " ", str(label))).strip()[:90] or sc["id"]


def scenes_info(name, dec):
    wd, _ = project(name)
    sp = wd / "scenes.json"
    scenes = json.loads(sp.read_text()) if sp.exists() else []
    ov = {o["id"]: o for o in dec.get("overlays", [])}
    out = []
    for sc in scenes:
        o = ov.get(sc["id"])
        out.append(dict(id=sc["id"], type=sc["type"], label=scene_label(sc),
                        start=sc.get("start", ""), kicker=sc.get("kicker", ""), source=(sc.get("source") or {}).get("name", ""),
                        disabled=bool(sc.get("disabled")), at=o["at"] if o else None, dur=o["dur"] if o else None,
                        url=gfx_preview(o) if o else None, kind=o.get("kind") if o else None,
                        card=o.get("card") if o else None))
    return out


def run_qc(name):
    wd, meta = project(name)
    key = f"qc:{name}"
    if jobs.get(key, {}).get("state") == "running":
        return jobs[key]
    jobs[key] = {"state": "running", "log": ""}

    def run():
        for tool, outf in (("literal.py", None), ("wordcheck.py", "wordcheck.txt"), ("splicecheck.py", "splicecheck.txt")):
            r = subprocess.run([PY, str(ROOT / "tools" / tool), meta["src"]], capture_output=True, text=True, cwd=ROOT)
            if outf:
                (wd / outf).write_text("\n".join(l for l in r.stdout.splitlines() if "Loading" not in l))
        jobs[key] = {"state": "done"}
    threading.Thread(target=run, daemon=True).start()
    return jobs[key]


RENDERS = ROOT / "motion" / "renders"
_live_t: dict[str, threading.Timer] = {}


def live_html(name):
    """Re-write the project's scene pages (mograph --no-render) ~0.8 s after the last look change (debounced)."""
    if _live_t.get(name):
        _live_t[name].cancel()

    def run():
        jobs[f"live:{name}"] = {"state": "running"}
        studio_pro.mograph_html(name)
        subprocess.run([PY, str(ROOT / "tools" / "mograph.py"), "--gallery", str(WORK / name / "decisions.json")],
                       capture_output=True, cwd=ROOT)  # the motion library previews follow the look too
        jobs[f"live:{name}"] = {"state": "done", "t": time.time()}
    _live_t[name] = threading.Timer(0.8, run)
    _live_t[name].start()


def live_url(o):
    f = ROOT / "motion" / "scenes" / f"{o['id']}.html"
    return f"/motion/scenes/{o['id']}.html?v={int(f.stat().st_mtime)}" if f.exists() else None


def gfx_preview(o):
    """Browser-playable copy of a motion-graphic overlay (alpha MOV → VP9 WebM with alpha)."""
    f = ROOT / o["file"]
    if not f.exists():
        return None
    if f.suffix == ".mp4":
        return f"/gfx/{f.name}"
    pv = RENDERS / "preview" / (f.stem + ".webm")
    if pv.exists() and pv.stat().st_mtime >= f.stat().st_mtime:
        return f"/gfx/preview/{pv.name}"
    key = f"gfx:{f.stem}"
    if jobs.get(key, {}).get("state") != "running":
        jobs[key] = {"state": "running"}

        def run():
            pv.parent.mkdir(exist_ok=True)
            tmp = pv.with_suffix(".tmp.webm")
            subprocess.run([vedit.binpath("ffmpeg"), "-y", "-v", "error", "-i", str(f), "-vf", "scale=540:-2",
                            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "1500k", "-deadline", "realtime",
                            "-cpu-used", "8", "-auto-alt-ref", "0", "-an", str(tmp)])
            if tmp.exists():
                tmp.rename(pv)
            jobs[key] = {"state": "done"}
        studio_api.background(run)  # max 2 encodes at a time (was: one thread per graphic, all at once)
    return None


def load(name):
    wd, meta = project(name)
    tr = vedit.jload(wd / "transcript.json")
    dec = vedit.jload(wd / "decisions.json", {})
    edl = vedit.jload(wd / "edl.json", {})
    removed = sorted({i for r in dec.get("remove", []) for i in range(r["from"], r["to"] + 1)})
    outs = sorted(p.name for p in OUT.glob(f"{name}*.mp4"))
    words = tr["words"]
    cuts = []
    for c in edl.get("cuts", []):
        if c.get("reason") == "pause":
            continue
        a, b = c.get("after", -1), c.get("before", -1)
        if a >= 0:
            s0, s1 = words[a]["e"], words[b]["s"]
        else:
            s0, s1 = c["t"], c["t"] + c["dur"]
        cuts.append(dict(at=c["at"], dur=c["dur"], after=a, before=b, src_start=round(s0, 3), src_end=round(s1, 3),
                         reason=c.get("reason", ""), text=c.get("removed", ""), key=f"{s0:.1f}-{s1:.1f}"))
    return dict(name=name, src=Path(meta["src"]).name, dur=meta["dur"], w=meta["w"], h=meta["h"],
                words=[dict(i=w["i"], w=w["w"], s=w["s"], e=w["e"], p=w.get("p", 1), fill=bool(w.get("fill")))
                       for w in tr["words"]],
                removed=removed, fixes=dec.get("fixes", {}), cut_ranges=dec.get("cut_ranges", []),
                segments=edl.get("segments", []), new_dur=edl.get("new_dur"),
                words_out=edl.get("words_out", []), cuts=cuts, peaks=peaks(name), thumbs=ensure_thumbs(name),
                can_undo=bool(history.get(name)), can_redo=bool(future.get(name)),
                hook_segs=edl.get("hook_segs") or ([edl["hook"]] if edl.get("hook") else []),
                live=jobs.get(f"live:{name}", {}), comments=studio_pro.comments(name),
                health=(vedit.jload(wd / "health.json", {}) or {}).get("score"),
                overlays=[dict(id=o["id"], at=o["at"], dur=o["dur"], panel=o.get("caption") == "panel", url=gfx_preview(o), live=live_url(o),
                               stale=bool(o.get("stale")), caption=o.get("caption", "low"), kind=o.get("kind", "full"),
                               card=o.get("card"))
                          for o in dec.get("overlays", [])],
                caption_y=dec.get("caption_y", 1150), caption_style=dec.get("caption_style", "pop"),
                captions_on=dec.get("captions", True) is not False, accent=studio_api.brandkit.accent(dec),
                keywords=dec.get("keywords", []), tuning=dec.get("tuning", {}),
                marks=vedit.jload(wd / "marks.json", []),
                outputs=outs, proxy=ensure_proxy(name), job=jobs.get(name),
                review=review_state(name), issues=qc_issues(name), scenes=scenes_info(name, dec),
                qc=jobs.get(f"qc:{name}"), remove_reasons=[dict(f=r["from"], t=r["to"], reason=r.get("reason", ""))
                                                          for r in dec.get("remove", [])],
                previews=sorted((p.name for p in OUT.glob(f"{name}_preview_v*.mp4")),
                                key=lambda n: int(re.search(r"_v(\d+)", n).group(1))))


def ranges(ids):
    out, start, prev = [], None, None
    for i in sorted(ids):
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            out.append((start, prev))
            start = prev = i
    if start is not None:
        out.append((start, prev))
    return out


def save(name, body):
    wd, meta = project(name)
    p = wd / "decisions.json"
    dec = vedit.jload(p, {})
    old = {(r["from"], r["to"]): r.get("reason", "") for r in dec.get("remove", [])}
    dec["remove"] = [{"from": a, "to": b, "reason": old.get((a, b), "manual edit")}
                     for a, b in ranges(body.get("removed", []))]
    dec["fixes"] = {str(k): v for k, v in body.get("fixes", {}).items()}
    if not (wd / "decisions.manual-backup.json").exists() and p.exists():
        (wd / "decisions.manual-backup.json").write_text(p.read_text())
    vedit.jsave(p, dec)
    r = subprocess.run([PY, str(ROOT / "tools" / "vedit.py"), "plan", meta["src"]],
                       capture_output=True, text=True, cwd=ROOT)
    edl = vedit.jload(wd / "edl.json", {})
    return dict(ok=r.returncode == 0, msg=(r.stdout + r.stderr).strip()[-600:],
                segments=edl.get("segments", []), new_dur=edl.get("new_dur"))


def render(name, final):
    wd, meta = project(name)
    if jobs.get(name, {}).get("state") == "running":
        return jobs[name]
    jobs[name] = {"state": "running", "log": "", "final": final}

    def step(args, label):
        jobs[name]["log"] += f"• {label}…\n"
        r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
        tail = re.sub(r"frame=.*?\r", "", r.stdout + r.stderr).strip().splitlines()[-3:]
        jobs[name]["log"] += "\n".join(tail) + "\n"
        return r.returncode == 0

    def run():
        ok = step([PY, "tools/vedit.py", "plan", meta["src"]], "planning cuts")
        if ok and (wd / "scenes.json").exists():
            ok = step([PY, "tools/mograph.py", meta["src"]], "updating motion graphics (only changed scenes)")
        fl = studio_api.render_flags(name)
        if ok and (wd / "scenes.json").exists() and fl["sfx"]:
            ok = step([PY, "tools/sfx.py", meta["src"]] + ([] if fl["riser"] else ["--no-riser"]), "sound design (sfx)")
        if ok and not fl["hookzoom"]:
            with studio_api.EDIT:
                d_ = vedit.jload(wd / "decisions.json", {})
                if studio_api.stash_hook_zoom(d_):
                    vedit.jsave(wd / "decisions.json", d_)
        if ok:
            ok = step([PY, "tools/vedit.py", "render", meta["src"]] + (["--final"] if final else []),
                      "rendering " + ("FINAL 1080p" if final else "720p preview"))
        last = vedit.jload(wd / "last_render.json", {})
        jobs[name].update(state="done" if ok else "error", output=Path(last.get("path", "")).name if ok else None)
    threading.Thread(target=run, daemon=True).start()
    return jobs[name]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def send_file(self, path, ctype):
        size = path.stat().st_size
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else size - 1
                else:
                    start = size - int(m.group(2))
        end = min(end, size - 1)
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            try:
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        try:
            q = parse_qs(urlparse(self.path).query)
            if path == "/" or path == "/studio":
                return self.send_file(HERE / "studio.html", "text/html; charset=utf-8")
            if path == "/studio_pro.js":
                return self.send_file(HERE / "studio_pro.js", "text/javascript; charset=utf-8")
            if path == "/editor":
                return self.send_file(HERE / "index.html", "text/html; charset=utf-8")
            if path == "/api/catalog":
                return self.send_json(studio_api.catalog_with_samples())
            if path == "/api/imports":
                return self.send_json(studio_api.imports)
            if path == "/api/settings":
                return self.send_json(studio_api.settings())
            # ---- Studio v2 (studio_pro): Health · notes · Claude · Hook Lab · Post Kit · Brand Kits · live graphics
            if path == "/api/claude":
                return self.send_json(studio_pro.claude_status())
            if path == "/api/kits":
                return self.send_json(studio_pro.kits())
            if path == "/api/refs":
                return self.send_json(studio_brief.refs())
            m = re.fullmatch(r"/refs/([a-z0-9-]+)/(thumb\.jpg|sheet\.jpg)", path)
            if m:
                f = studio_brief.ref_file(*m.groups())
                return self.send_file(f, "image/jpeg") if f else self.send_json({"error": "no such file"}, 404)
            m = re.fullmatch(r"/api/project/([^/]+)/brief", path)
            if m:
                return self.send_json(studio_brief.brief_get(m.group(1)))
            m = re.fullmatch(r"/api/kits/([a-z0-9-]+)\.json", path)
            if m:
                f = studio_pro.kit_file(m.group(1))
                return self.send_file(f, "application/json") if f else self.send_json({"error": "no such kit"}, 404)
            m = re.fullmatch(r"/api/project/([^/]+)/(health|comments|hooklab|postkit|claude)", path)
            if m:
                n, what = m.groups()
                return self.send_json({"health": studio_pro.health, "comments": studio_pro.comments, "hooklab": studio_pro.hook_candidates,
                                       "postkit": studio_pro.post_kit_state, "claude": lambda x: studio_pro._job(f"claude:{x}")}[what](n))
            m = re.fullmatch(r"/api/project/([^/]+)/hookpage", path)
            if m:
                return self.send_json(studio_pro.hook_page(m.group(1), q.get("v", [""])[0], q.get("text", [""])[0], q.get("kicker", [""])[0]))
            m = re.fullmatch(r"/api/project/([^/]+)/srcclip", path)
            if m:
                return self.send_json(dict(url=studio_pro.src_clip(m.group(1), float(q["s"][0]), float(q["e"][0]))))
            m = re.fullmatch(r"/motion/((?:scenes|fonts|clips)/[A-Za-z0-9_./ -]+)", path)
            if m and ".." not in m.group(1):  # scene pages for the live preview (+ the fonts / images they load)
                f = ROOT / "motion" / m.group(1)
                ct = {".html": "text/html; charset=utf-8", ".ttf": "font/ttf", ".png": "image/png", ".jpg": "image/jpeg",
                      ".svg": "image/svg+xml", ".mp4": "video/mp4", ".webm": "video/webm", ".otf": "font/otf"}.get(f.suffix, "application/octet-stream")
                return self.send_file(f, ct) if f.is_file() else self.send_json({"error": "not found"}, 404)
            m = re.fullmatch(r"/out/([^/]+_postkit)/([^/]+\.(mp4|srt|jpg|txt))", path)
            if m and (OUT / m.group(1) / m.group(2)).exists():
                return self.send_file(OUT / m.group(1) / m.group(2), {"mp4": "video/mp4", "srt": "application/x-subrip", "jpg": "image/jpeg",
                                                                     "txt": "text/plain; charset=utf-8"}[m.group(3)])
            m = re.fullmatch(r"/out/([^/]+\.zip)", path)
            if m and (OUT / m.group(1)).exists():
                return self.send_file(OUT / m.group(1), "application/zip")
            m = re.fullmatch(r"/sfx/([a-z_]+)\.wav", path)
            if m:  # the render's own sounds (tools/sfx.py), for previews you can hear
                f = studio_api.sfx_wav(m.group(1))
                return self.send_file(f, "audio/wav") if f else self.send_json({"error": "no such sound"}, 404)
            m = re.fullmatch(r"/media/([^/]+)/hookclip", path)
            if m:
                return self.send_json(studio_api.hook_clip(m.group(1)))
            m = re.fullmatch(r"/media/([^/]+)/s/([A-Za-z0-9_.-]+\.(mp4|webm))", path)
            if m:  # Studio preview files (hook clip, cut-out, render clips)
                return self.send_file(WORK / m.group(1) / "studio" / m.group(2), "video/webm" if m.group(3) == "webm" else "video/mp4")
            m = re.fullmatch(r"/api/project/([^/]+)/clip", path)
            if m:
                return self.send_json(dict(url=studio_api.render_clip(m.group(1), float(q.get("at", ["0"])[0]), float(q.get("dur", ["3"])[0]))))
            m = re.fullmatch(r"/gfx/sampleclip/([A-Za-z0-9_-]+)", path)
            if m:
                return self.send_json(dict(url=studio_api.sample_clip(m.group(1))))
            m = re.fullmatch(r"/api/project/([^/]+)/look", path)
            if m:
                return self.send_json(studio_api.get_look(m.group(1)))
            m = re.fullmatch(r"/media/([^/]+)/(frame\.jpg|cutout\.png)", path)
            if m:
                t, w = float(q.get("t", ["1"])[0]), int(q.get("w", ["360"])[0])
                f = (studio_api.frame if m.group(2) == "frame.jpg" else studio_api.cutout)(m.group(1), t, min(720, max(120, w)))
                if not f:
                    return self.send_json({"error": "not ready"}, 404)
                return self.send_file(f, "image/jpeg" if f.suffix == ".jpg" else "image/png")
            m = re.fullmatch(r"/gfx/sample/([A-Za-z0-9_-]+)", path)
            if m:  # catalog sample: a real past render, as a browser-playable preview
                src = next((p for ext in ("mp4", "mov") for p in [RENDERS / f"{m.group(1)}.{ext}"] if p.exists()), None)
                url = gfx_preview(dict(file=str(src.relative_to(ROOT)))) if src else None
                return self.send_json(dict(url=url, ready=bool(url)))
            if path == "/api/projects":
                items = []
                for d in sorted(WORK.iterdir()):
                    meta = vedit.jload(d / "meta.json")
                    if meta and (d / "transcript.json").exists():
                        edl = vedit.jload(d / "edl.json", {})
                        rv = vedit.jload(d / "review.json", {})
                        items.append(dict(name=d.name, src=Path(meta["src"]).name, dur=meta["dur"],
                                          new_dur=edl.get("new_dur"), mtime=(d / "transcript.json").stat().st_mtime,
                                          approved=sum(1 for b in ("part", "scene") for v in rv.get(b, {}).values()
                                                       if v.get("state") == "approved")))
                return self.send_json(items)
            m = re.fullmatch(r"/api/project/([^/]+)", path)
            if m:
                return self.send_json(load(m.group(1)))
            m = re.fullmatch(r"/media/([^/]+)/proxy\.mp4", path)
            if m:
                return self.send_file(WORK / m.group(1) / "proxy.mp4", "video/mp4")
            m = re.fullmatch(r"/gfx/(preview/)?([^/]+\.(mp4|webm))", path)
            if m:
                f = RENDERS / (m.group(1) or "") / m.group(2)
                return self.send_file(f, "video/webm" if m.group(3) == "webm" else "video/mp4")
            m = re.fullmatch(r"/fonts/([^/]+\.ttf)", path)
            if m:
                return self.send_file(ROOT / "assets" / "fonts" / m.group(1), "font/ttf")
            m = re.fullmatch(r"/media/([^/]+)/thumbs\.jpg", path)
            if m:
                return self.send_file(WORK / m.group(1) / "thumbs.jpg", "image/jpeg")
            m = re.fullmatch(r"/out/([^/]+\.(mp4|srt))", path)
            if m and (OUT / m.group(1)).exists():
                return self.send_file(OUT / m.group(1), "video/mp4" if m.group(2) == "mp4" else "application/x-subrip")
            self.send_json({"error": "not found"}, 404)
        except FileNotFoundError as e:
            self.send_json({"error": f"not found: {e}"}, 404)

    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        if path == "/api/upload":  # raw video bytes → input/ → transcribe + plan in the background
            fn = parse_qs(urlparse(self.path).query).get("name", ["video.mov"])[0]
            return self.send_json(studio_api.upload(fn, self.rfile, int(self.headers.get("Content-Length", 0))))
        if path == "/api/refs/upload":  # a video the creator likes → studied for its style, then deleted
            fn = parse_qs(urlparse(self.path).query).get("name", ["reference.mp4"])[0]
            return self.send_json(studio_brief.ref_upload(fn, self.rfile, int(self.headers.get("Content-Length", 0))))
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
        with studio_api.EDIT:  # one edit at a time, so quick clicks can't overwrite each other
            return self.post(path, body)

    def post(self, path, body):
        if path == "/api/settings":
            return self.send_json(studio_api.set_settings(body))
        if path == "/api/kits/import":
            return self.send_json(studio_pro.kit_import(body))
        if path == "/api/refs":
            return self.send_json(studio_brief.ref_delete(body.get("delete", "")))
        m = re.fullmatch(r"/api/project/([^/]+)/(brief|style)", path)
        if m:
            n, what = m.groups()
            if what == "brief":  # Claude fits the edit (if installed), then the Studio renders a preview
                return self.send_json(studio_brief.brief_apply(n, body, render=lambda: render(n, False)))
            return self.send_json(studio_brief.style_apply(n, body))
        m = re.fullmatch(r"/api/project/([^/]+)/(health|fix|comments|claude|hooklab|postkit|kit)", path)
        if m:
            n, what = m.groups()
            if what == "health":
                return self.send_json(studio_pro.health_run(n, bool(body.get("quick"))))
            if what == "fix":
                r = studio_pro.apply_fix(n, body)
                return self.send_json(dict(r, project=load(n)))
            if what == "comments":
                return self.send_json(studio_pro.comment_del(n, body) if body.get("delete") else studio_pro.comment_add(n, body))
            if what == "claude":
                after = lambda: render(n, False)  # noqa: E731 — Claude edits, then the Studio renders a preview
                return self.send_json(studio_pro.apply_comments(n, after) if body.get("kind") == "notes" else studio_pro.auto_edit(n, after))
            if what == "hooklab":
                return self.send_json(studio_pro.set_cold_open(n, body))
            if what == "postkit":
                return self.send_json(studio_pro.post_kit(n))
            if what == "kit":
                if body.get("apply"):
                    r = studio_pro.kit_apply(n, body["apply"])
                    live_html(n)
                    return self.send_json(r)
                return self.send_json(studio_pro.kit_save(n, body))
        m = re.fullmatch(r"/api/project/([^/]+)/look", path)
        if m:
            r = studio_api.set_look(m.group(1), body)
            if any(k in body for k in ("palette", "accent", "fonts", "hook", "extras")):
                live_html(m.group(1))  # live preview: scene pages follow the new look without a render
            return self.send_json(r)
        m = re.fullmatch(r"/api/project/([^/]+)/(mark|unmark)", path)
        if m:  # Lloyd's "something is wrong here" flags — Claude reads work/<name>/marks.json
            name, action = m.groups()
            wd, _ = project(name)
            marks = vedit.jload(wd / "marks.json", [])
            if action == "mark":
                marks.append(dict(id=max([x["id"] for x in marks] + [0]) + 1, out=round(body["out"], 2),
                                  src=round(body["src"], 2), note=body.get("note", "")))
            else:
                marks = [x for x in marks if x["id"] != body.get("id")]
            vedit.jsave(wd / "marks.json", marks)
            return self.send_json(dict(marks=marks))
        m = re.fullmatch(r"/api/project/([^/]+)/(review|qc)", path)
        if m:
            name, action = m.groups()
            return self.send_json(set_review(name, body) if action == "review" else run_qc(name))
        m = re.fullmatch(r"/api/project/([^/]+)/(save|render|op)", path)
        if not m:
            return self.send_json({"error": "not found"}, 404)
        name, action = m.groups()
        if action == "save":
            return self.send_json(save(name, body))
        if action == "op":
            return self.send_json(op(name, body))
        return self.send_json(render(name, bool(body.get("final"))))


def _after_import(name):
    studio_pro.on_imported(name)  # default brand kit
    if studio_api.settings().get("auto_edit") and studio_pro.claude_bin():
        studio_pro.auto_edit(name, after=lambda: render(name, False))


studio_api.ON_IMPORTED.append(_after_import)

if __name__ == "__main__":
    print(f"vedit editor → http://localhost:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
