"""Studio v2 features, next to studio_api (look) and server.py (routes):

  Edit Health      tools/health.py as a background job + one-click fixes (tighten dead air, natural colour, graphic off)
  Talk-to-edit     timestamped notes on the edit (work/<name>/comments.json) that Claude applies
  Claude runs      `claude -p` (Claude Code, headless) on this folder: Auto-edit and Apply notes, streamed step by step
  Hook Lab         finds the strongest 2–7 s lines to open with, proposes a thumbnail title, sets a COPIED cold open
  Post Kit         9:16 + 1:1 + 16:9, captions, cover, post text — one folder + zip in output/
  Brand Kits       the look saved as brandkits/<kit>.json, applied to any video (and to every new upload by default)

Everything writes the same files Claude edits by hand (decisions.json, scenes.json), so a Studio action and a
chat request always end up in the same edit.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import zipfile
from pathlib import Path

import numpy as np

import studio_api as sa
from studio_api import PY, ROOT, WORK, brandkit, vedit

OUT = ROOT / "output"
KITS = ROOT / "brandkits"
JOBS: dict[str, dict] = {}  # "health:<n>" · "claude:<n>" · "postkit:<n>" · "sdr:<n>"


def _job(key):
    return JOBS.get(key) or {"state": "idle"}


def _start(key, fn, **meta):
    if JOBS.get(key, {}).get("state") == "running":
        return JOBS[key]
    j = JOBS[key] = {"state": "running", "log": "", "started": time.time(), **meta}

    def run():
        try:
            fn(j)
            if j["state"] == "running":
                j["state"] = "done"
        except Exception as e:  # surfaced in the UI, never a silent hang
            j["state"], j["log"] = "error", j["log"] + f"\n{type(e).__name__}: {e}"
        j["ended"] = time.time()
    threading.Thread(target=run, daemon=True).start()
    return j


def _meta(name):
    return vedit.jload(WORK / name / "meta.json", {})


def _src(name):
    return _meta(name).get("src")


def _tool(args, j=None, step=None):
    """Run a toolkit command; stream its lines into the job log."""
    if j is not None and step:
        j["step"] = step
    p = subprocess.Popen([PY, *map(str, args)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
    tail = []
    for line in p.stdout:
        line = re.sub(r".*\r", "", line.rstrip("\n"))
        if not line or "Warning" in line or line.startswith(("Fetching", "Loading")):
            continue
        tail = (tail + [line])[-200:]
        if j is not None:
            j["log"] = "\n".join(tail)
    return p.wait() == 0


def plan(name, j=None):
    return _tool([ROOT / "tools" / "vedit.py", "plan", _src(name)], j, "plan")


def mograph_html(name, j=None):
    """Re-write the scene pages (no render) — the Studio's live preview plays them straight away."""
    return _tool([ROOT / "tools" / "mograph.py", _src(name), "--no-render"], j, "graphics")


def _edit(name):
    edl = vedit.jload(WORK / name / "edl.json", {})
    segs = (edl.get("hook_segs") or []) + edl.get("segments", [])
    offs, o = [], 0.0
    for a, b in segs:
        offs.append(o)
        o += b - a
    return segs, offs, o


def e2s(name, t):
    segs, offs, _ = _edit(name)
    for (a, b), of in zip(segs, offs):
        if of <= t < of + (b - a):
            return a + (t - of)
    return segs[-1][1] if segs else t


# ================================================================ Edit Health
def health(name):
    wd = WORK / name
    hp, edl = wd / "health.json", wd / "edl.json"
    rep = vedit.jload(hp, None)
    stale = bool(rep) and edl.exists() and hp.stat().st_mtime < edl.stat().st_mtime
    return dict(report=rep, stale=stale, job=_job(f"health:{name}"))


def health_run(name, quick=False):
    def fn(j):
        ok = _tool([ROOT / "tools" / "health.py", _src(name), *(["--quick"] if quick else [])], j, "checking")
        j["state"] = "done" if ok else "error"
    return _start(f"health:{name}", fn)


def apply_fix(name, body):
    """One-click fixes from the Health list. Returns what changed; the caller re-loads the project."""
    act = body.get("action")
    if act == "tighten":
        with sa.EDIT:
            dec = sa._dec(name)
            for s, e in body.get("ranges", []):
                dec.setdefault("cut_ranges", []).append({"start": float(s), "end": float(e), "reason": "Edit Health: dead air"})
            sa._save_dec(name, dec)
            plan(name)
        return dict(ok=True, msg="tightened")
    if act == "scene_off":
        with sa.EDIT:
            sc = sa._scenes(name)
            for x in sc:
                if x.get("id") == body.get("id"):
                    x["disabled"] = True
            sa._save_scenes(name, sc)
            mograph_html(name)
        return dict(ok=True, msg="graphic off")
    if act == "sdr":
        return dict(ok=True, job=to_natural(name))
    return dict(ok=False, msg=f"unknown fix {act}")


def to_natural(name):
    """iPhone HDR source → natural SDR colour (Apple's tone mapping), then re-plan. The original is kept."""
    def fn(j):
        j["step"] = "converting colour"
        src = Path(_src(name))
        new = sa.to_sdr(src)
        meta = _meta(name)
        meta["src"], meta["trc"] = str(new), "bt709"
        vedit.jsave(WORK / name / "meta.json", meta)
        for f in ("proxy.mp4", "thumbs.jpg"):  # the Studio rebuilds them from the natural-colour file
            p = WORK / name / f
            if p.exists():
                p.rename(p.with_name(p.stem + "_hdr_old" + p.suffix))
        plan(name, j)
    return _start(f"sdr:{name}", fn)


# ================================================================ Talk-to-edit (timestamped notes)
def comments(name):
    return vedit.jload(WORK / name / "comments.json", [])


def comment_add(name, body):
    cs = comments(name)
    at = float(body["at"])
    cs.append(dict(id=max([c["id"] for c in cs] + [0]) + 1, at=round(at, 2), src=round(e2s(name, at), 2),
                   text=str(body.get("text", "")).strip()[:500], done=False, t=time.time()))
    vedit.jsave(WORK / name / "comments.json", cs)
    return cs


def comment_del(name, body):
    cs = [c for c in comments(name) if c["id"] != body.get("id")]
    vedit.jsave(WORK / name / "comments.json", cs)
    return cs


def _context(name, src_t, span=4.0):
    """The words around a source time (what the creator was hearing when they paused)."""
    words = vedit.jload(WORK / name / "transcript.json", {}).get("words", [])
    fixes = sa._dec(name).get("fixes", {})
    near = [(w["i"], fixes.get(str(w["i"]), w["w"])) for w in words if src_t - span <= w["s"] <= src_t + span]
    return " ".join(f"#{i}:{t}" for i, t in near if t)


# ================================================================ Claude runs (Claude Code, headless)
ALLOWED = ["Read", "Edit", "Write", "Glob", "Grep", "Bash(.venv/bin/python:*)", "Bash(./vedit:*)", "Bash(ls:*)"]


def claude_bin():
    s = sa.settings().get("claude_bin") or os.environ.get("STUDIO_CLAUDE")
    for c in (s, shutil.which("claude"), Path.home() / ".claude/local/claude", Path.home() / ".local/bin/claude",
              "/opt/homebrew/bin/claude", "/usr/local/bin/claude"):
        if c and Path(c).exists():
            return str(c)
    return None


def claude_status():
    b = claude_bin()
    return dict(available=bool(b), bin=b, job_keys=[k for k, v in JOBS.items() if k.startswith("claude:") and v.get("state") == "running"])


def _brief(tool, inp):
    if tool == "Bash":
        return (inp.get("description") or inp.get("command", ""))[:90]
    if tool in ("Edit", "Write", "Read"):
        return Path(inp.get("file_path", "")).name
    return json.dumps(inp, ensure_ascii=False)[:80]


def claude_run(name, kind, prompt, after=None):
    """Run Claude Code on this folder with the edit skill; every tool call shows up as a step in the Studio."""
    b = claude_bin()
    if not b:
        return dict(state="error", log="Claude Code is not installed — see README (Install).")

    def fn(j):
        j["events"] = []
        cmd = [b, "-p", prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits",
               "--allowedTools", " ".join(ALLOWED)]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
        for line in p.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                j["log"] = (j["log"] + line)[-4000:]
                continue
            if ev.get("type") == "assistant":
                for c in ev.get("message", {}).get("content", []):
                    if c.get("type") == "tool_use":
                        j["events"] = (j["events"] + [dict(t=time.time(), tool=c["name"], what=_brief(c["name"], c.get("input", {})))])[-60:]
                        j["step"] = j["events"][-1]["what"]
                    elif c.get("type") == "text" and c.get("text", "").strip():
                        j["say"] = c["text"].strip()[-600:]
            elif ev.get("type") == "result":
                j["result"] = (ev.get("result") or "").strip()
                j["cost"] = ev.get("total_cost_usd")
                if ev.get("is_error"):
                    j["state"] = "error"
        if p.wait() and j["state"] == "running":
            j["state"] = "error"
        if j["state"] == "running" and after:
            j["step"] = "rendering preview"
            after()
    return _start(f"claude:{name}", fn, kind=kind)


def auto_edit(name, after=None):
    src = Path(_src(name)).relative_to(ROOT) if _src(name) else f"input/{name}.mov"
    prompt = (f"Edit the video {src} with this toolkit, as the creator's editor. First read CLAUDE.md, DESIGN_SYSTEM.md and "
              f".claude/skills/bbd-video-edit/SKILL.md and follow them, including work/{name}/decisions.json \"look\" (the creator's "
              "Studio choices: palette, fonts, hook, captions, visuals density/types, extras; look.brief is the creator's own words about the "
              "design: follow it first; look.style_refs / look.style_notes are styles learned from videos they like). The transcript and a first plan already "
              f"exist in work/{name}/. Do the full editorial pass: remove retakes, false starts, repeated phrases and dead air "
              "(decisions.json remove / cut_ranges / fixes, cut at energy dips); write the hook and the motion graphics in "
              f"work/{name}/scenes.json (never cover the face; on screen-demo / back-cam parts use only small side callouts); pick "
              "keywords; then run tools/literal.py, tools/soundcheck.py and tools/health.py and fix what they find. Do NOT render "
              "the final and do not touch files outside this folder. Finish with a 3-line summary in the creator's language.")
    return claude_run(name, "auto", prompt, after)


def apply_comments(name, after=None):
    open_ = [c for c in comments(name) if not c.get("done")]
    if not open_:
        return dict(state="error", log="no notes")
    notes = "\n".join(f"- at {vedit.tc(c['at'])} in the edit (source {c['src']:.2f} s): \"{c['text']}\"  · words there: "
                      f"{_context(name, c['src'])}" for c in open_)
    prompt = (f"The creator watched the edit of work/{name} and left these notes (times are in the edited video; source "
              f"seconds and nearby transcript word indices are given):\n{notes}\n\nRead CLAUDE.md and "
              ".claude/skills/bbd-video-edit/SKILL.md first. Apply every note by editing work/{name}/decisions.json (remove by word "
              "index, cut_ranges in source seconds at energy dips, ring_out, hook) and/or scenes.json (graphics), then run "
              f".venv/bin/python tools/vedit.py plan {Path(_src(name)).relative_to(ROOT)} and tools/splicecheck.py on the changed spots. "
              "Do NOT render. Reply with one line per note saying what you changed, in the creator's language.")

    def done():
        cs = comments(name)
        for c in cs:
            if c["id"] in {x["id"] for x in open_}:
                c["done"] = True
        vedit.jsave(WORK / name / "comments.json", cs)
        if after:
            after()
    return claude_run(name, "notes", prompt, done)


# ================================================================ Hook Lab
HOOKY = {"grabe": 2, "hindi": 1, "wala": 1, "walang": 1, "secret": 3, "sikreto": 3, "paano": 2, "bakit": 1, "never": 2,
         "stop": 2, "mali": 2, "pinaka": 2, "sarili": 2, "libre": 2, "free": 2, "first": 1, "dapat": 1, "huwag": 2, "wag": 2,
         "kailangan": 1, "lahat": 1, "mas": 1, "ai": 1, "claude": 1, "capcut": 2, "nobody": 3, "walang-wala": 3, "best": 2,
         "worst": 2, "mistake": 3, "pera": 2, "money": 2, "kumita": 3, "x": 1, "times": 1, "instead": 1, "imagine": 2, "now": 1}
STOP = sa.HOOK_STOP


def _phrases(name):
    """Kept words in source order, split into phrases at sentence ends and pauses (source seconds)."""
    words = vedit.jload(WORK / name / "transcript.json", {}).get("words", [])
    fixes = sa._dec(name).get("fixes", {})
    edl = vedit.jload(WORK / name / "edl.json", {})
    body = edl.get("segments", [])
    kept = sorted({i for i, *_ in edl.get("words_out", [])})
    inbody = lambda w: any(a - 0.05 <= (w["s"] + w["e"]) / 2 <= b + 0.05 for a, b in body)
    out, cur = [], []
    for i in kept:
        w = words[i]
        t = fixes.get(str(i), w["w"])
        if not t or not inbody(w):
            continue
        if cur and (w["s"] - cur[-1][2] > 0.6 or re.search(r"[.?!]$", cur[-1][3])):
            out.append(cur)
            cur = []
        cur.append((i, w["s"], w["e"], t))
    if cur:
        out.append(cur)
    return out


FILL = {"so", "yun", "ayun", "guys", "and", "then", "pero", "kasi", "ito", "yung", "ang", "um", "uh", "ah", "eh", "okay", "ok",
        "na", "nga", "lang", "naman", "diba", "parang", "basically", "like", "now", "ngayon",
        "siya", "siyang", "sya", "syang", "din", "rin", "pa", "mo", "ko", "yan", "dito", "nya", "niya", "ka"}
TURN = ("hindi na", "hindi ko na", "wala nang", "wala ng", "no more", "instead of", "stop", "huwag na", "wag na", "never again")


def _content(words):
    """Drop leading fillers ("so yun guys …") so the line — and its title — starts on the point."""
    k = 0
    while k < len(words) - 3 and re.sub(r"[^\w]", "", words[k].lower()) in FILL:
        k += 1
    return k


def _title(words, kws):
    """Thumbnail rows for a line: a short lead-in, the key phrase in the colour box, the rest underneath."""
    toks = [re.sub(r"[^\w'’-]", "", t) for t in words]
    toks = [t for t in toks if t]
    if not toks:
        return ["WATCH THIS"]
    low = [t.lower() for t in toks]
    kwn = {re.sub(r"[^\w]", "", k.lower()) for k in kws}
    hits = [n for n, t in enumerate(low) if t in kwn] or [n for n, t in enumerate(low) if HOOKY.get(t, 0) >= 2]  # the video's keywords first
    k = hits[0] if hits else max(range(len(toks)), key=lambda n: 0 if low[n] in STOP or low[n] in FILL else len(toks[n]))
    j = k  # grow the box over a neighbouring content word ("VIDEO EDITOR")
    if k > 0 and low[k - 1] not in STOP | FILL and len(low[k - 1]) > 2:
        k -= 1
    elif j + 1 < len(toks) and low[j + 1] not in STOP | FILL and len(low[j + 1]) > 2:
        j += 1
    lead = [t for t in toks[max(0, k - 3):k] if t.lower() not in FILL][-2:]
    rest, n2 = [], j + 1
    while n2 < len(toks) and len(rest) < 6:
        if low[n2] not in FILL or rest:
            rest.append(toks[n2])
        n2 += 1
    while rest and rest[-1].lower() in FILL | STOP:
        rest.pop()
    later = next((n for n in range(j + 1, len(toks)) if low[n] in kwn or HOOKY.get(low[n], 0) >= 2), None)
    rest_s = " ".join(("O:" + t.upper()) if later is not None and toks.index(t, j + 1) == later else t.upper() for t in rest)
    return ([" ".join(lead).upper()] if lead else []) + ["H:" + "_".join(t.upper() for t in toks[k:j + 1])] + ([rest_s] if len(rest) >= 2 else [])


def hook_candidates(name, n=3):
    wd = WORK / name
    db = np.load(wd / "energy.npy")
    med = float(np.median(db[db > -90])) if (db > -90).any() else -30.0
    dur = _meta(name).get("dur", 1)
    kws = sa._dec(name).get("keywords", [])
    kwn = {re.sub(r"[^\w]", "", k.lower()) for k in kws}
    words = vedit.jload(wd / "transcript.json", {}).get("words", [])
    ph = _phrases(name)
    cands = []
    for a in range(len(ph)):
        for b in range(a, min(a + 3, len(ph))):
            ws = [w for p in ph[a:b + 1] for w in p]
            ws = ws[_content([w[3] for w in ws]):]
            s, e = ws[0][1], ws[-1][2]
            if not 2.0 <= e - s <= 7.5 or s < max(8.0, 0.05 * dur):  # the intro already plays at the start
                continue
            toks = [re.sub(r"[^\w-]", "", w[3].lower()) for w in ws]
            text = " ".join(toks)
            score = sum(HOOKY.get(t, 0) for t in toks) + 2 * sum(t in kwn for t in toks) + 1.5 * sum(bool(re.match(r"\d", t)) for t in toks)
            score += 2 * sum(text.count(x) for x in TURN)  # "hindi ko na kailangan ng …" — a before/after in one line
            loud = float(np.mean(db[int(s * 100):int(e * 100)])) - med
            score += max(-1, min(1.5, loud / 4))  # camera distance changes loudness: keep it a small nudge
            nxt = words[ws[-1][0] + 1]["s"] if ws[-1][0] + 1 < len(words) else e + 1
            score += 1.0 if re.search(r"[.?!]$", ws[-1][3]) or nxt - e > 0.3 else -0.5  # ends on a finished thought
            score -= 0.15 * abs(len(ws) - 12) / 3   # 8–16 words read best in 2–5 s
            cands.append(dict(score=round(score, 2), start=round(s, 2), end=round(e, 2), **{"from": ws[0][0], "to": ws[-1][0]},
                              text=" ".join(w[3] for w in ws), rows=_title([w[3] for w in ws], kws)))
    cands.sort(key=lambda c: -c["score"])
    picked = []
    for c in cands:
        if all(c["end"] <= p["start"] or c["start"] >= p["end"] for p in picked):
            picked.append(c)
        if len(picked) == n:
            break
    for k, c in enumerate(picked):
        c["id"] = f"h{k + 1}"
    return dict(candidates=picked, current=sa._dec(name).get("hook"))


def _face_top(name, src_t):
    """Top of the face (px, 1920-high frame) at a source time, or None when no face (screen / back-cam shot)."""
    fb = ROOT / "tools" / "bin" / "facebox"
    if not fb.exists():
        return None
    png = WORK / name / "studio" / "hookface.png"
    png.parent.mkdir(exist_ok=True)
    subprocess.run([vedit.binpath("ffmpeg"), "-v", "error", "-y", "-ss", f"{src_t:.2f}", "-i", _src(name), "-frames:v", "1",
                    "-vf", "scale=1080:1920", str(png)], capture_output=True)
    r = subprocess.run([str(fb), str(png)], capture_output=True, text=True)
    try:
        faces = json.loads(r.stdout.splitlines()[0])["faces"]
    except (ValueError, IndexError, KeyError):
        return None
    return min((f[1] for f in faces), default=None)


def set_cold_open(name, body):
    """Copy a line to the top (never moved: the body still runs through it) + a thumbnail title on its first seconds."""
    with sa.EDIT:
        dec = sa._dec(name)
        if body.get("off"):
            dec.pop("hook", None)
            sc = [x for x in sa._scenes(name) if x.get("id") != "cold_open"]
        else:
            dec["hook"] = {"from": int(body["from"]), "to": int(body["to"])}
            for k in ("start", "end"):
                if body.get(k) is not None:
                    dec["hook"][k] = float(body[k])
            words = vedit.jload(WORK / name / "transcript.json", {}).get("words", [])
            probe = float(body.get("probe") or body.get("start") or words[int(body["from"])]["s"])
            ft = _face_top(name, probe + 0.8)
            y = 190 if ft is None or ft > 620 else None  # title in the top band unless the face is already up there
            first = " ".join(w["w"] for w in words[int(body["from"]):int(body["from"]) + 3])
            last = " ".join(w["w"] for w in words[max(int(body["from"]), int(body["to"]) - 1):int(body["to"]) + 1])
            scene = dict(id="cold_open", type="thumb", start=re.sub(r"[^\w' -]", "", first).strip(),
                         until=re.sub(r"[^\w' -]", "", last).strip(), tag=body.get("tag") or "Panoorin mo 'to",
                         rows=body.get("rows") or ["WATCH THIS"], caption="hide")
            if y:
                scene["y"] = y
            sc = [x for x in sa._scenes(name) if x.get("id") != "cold_open"]
            sc.insert(0, scene)
        sa._save_dec(name, dec)
        sa._save_scenes(name, sc)
        plan(name)
        mograph_html(name)
    return hook_candidates(name)


def src_clip(name, s, e):
    """A source-time moment as a small browser clip (Hook Lab plays the candidate lines with sound)."""
    st = WORK / name / "studio"
    st.mkdir(exist_ok=True)
    out = st / f"src_{s:.2f}_{e:.2f}.mp4"
    if not out.exists():
        tmp = out.with_suffix(".tmp.mp4")
        subprocess.run([vedit.binpath("ffmpeg"), "-y", "-v", "error", "-ss", f"{s:.3f}", "-t", f"{e - s + 0.2:.3f}", "-i", _src(name),
                        "-vf", f"{sa._tm(Path(_src(name)))}scale=540:-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp)], capture_output=True)
        if not tmp.exists():
            return None
        tmp.rename(out)
    return f"/media/{name}/s/{out.name}"


# ================================================================ Post Kit
def _latest(name):
    fin = OUT / f"{name}_FINAL.mp4"
    if fin.exists():
        return fin
    last = Path(vedit.jload(WORK / name / "last_render.json", {}).get("path", ""))
    return last if last.is_file() else None


def post_text(name):
    p = OUT / f"{name}_POST.txt"
    if p.exists():
        return p.read_text()
    dec = sa._dec(name)
    hook = sa.get_look(name).get("hook", {})
    title = re.sub(r"\s+", " ", " ".join(re.sub(r"@.*$", "", r).replace("H:", "").replace("O:", "").replace("_", " ") for r in
                                          next((s.get("rows", []) for s in sa._scenes(name) if s.get("id") in ("cold_open", "es_cold")), []))).strip()
    kws = [k.strip(".,!?").lower() for k in dec.get("keywords", [])][:5]
    cta = next((s.get("text") for s in sa._scenes(name) if s.get("type") == "behind" and "comment" in str(s.get("kicker", "")).lower()), "")
    lines = [title.capitalize() or (hook.get("text") or name).capitalize(), ""]
    if cta:
        lines += [f'👉 Comment "{cta}" para makuha mo.', ""]
    lines += [" ".join("#" + re.sub(r"[^\w]", "", k) for k in dict.fromkeys(kws) if k)]
    return "\n".join(lines)


def post_kit(name):
    def fn(j):
        src = _latest(name)
        if not src:
            j["state"], j["log"] = "error", "Render the video first."
            return
        kit = OUT / f"{name}_postkit"
        kit.mkdir(exist_ok=True)
        ff = vedit.binpath("ffmpeg")
        j["step"] = "9:16"
        shutil.copyfile(src, kit / "video_9x16.mp4")
        srt = OUT / f"{name}.srt"
        if not srt.exists():  # the final's .srt went missing: rebuild it from the edit (same timing as the render)
            j["step"] = "captions"
            code = ("import sys; sys.path.insert(0, 'tools'); import vedit; src, wd, meta = vedit.ctx(sys.argv[1]); "
                    "vedit.write_captions(wd / 'captions_postkit.ass', sys.argv[2], vedit.jload(wd / 'edl.json'), "
                    "vedit.jload(wd / 'transcript.json')['words'], vedit.jload(wd / 'decisions.json', {}), meta['w'], meta['h'])")
            subprocess.run([PY, "-c", code, _src(name), str(srt)], cwd=ROOT, capture_output=True)
        if srt.exists():
            shutil.copyfile(srt, kit / "captions.srt")
        j["step"] = "cover"
        subprocess.run([ff, "-y", "-v", "error", "-ss", "0.6", "-i", str(src), "-frames:v", "1", "-q:v", "2", str(kit / "cover.jpg")])
        tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
        venc = ["-c:v", "h264_videotoolbox", "-b:v", "8M"] if "h264_videotoolbox" in subprocess.run(
            [ff, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout else ["-c:v", "libx264", "-crf", "20", "-preset", "fast"]
        for label, w, h in (("1x1", 1080, 1080), ("16x9", 1920, 1080)):
            j["step"] = label  # letterbox on the brand dark — never crop the face out
            subprocess.run([ff, "-y", "-v", "error", "-i", str(src), "-vf", f"scale=-2:{h},pad={w}:{h}:(ow-iw)/2:0:color=0x0F0D0C",
                            *venc, "-pix_fmt", "yuv420p", *tags, "-c:a", "copy", "-movflags", "+faststart", str(kit / f"video_{label}.mp4")])
        (kit / "post.txt").write_text(post_text(name))
        j["step"] = "zip"
        zp = OUT / f"{name}_postkit.zip"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
            for f in sorted(kit.iterdir()):
                z.write(f, f"{name}_postkit/{f.name}")
        j["files"] = sorted(f.name for f in kit.iterdir())
        j["zip"] = zp.name
    return _start(f"postkit:{name}", fn)


def post_kit_state(name):
    kit = OUT / f"{name}_postkit"
    files = sorted(f.name for f in kit.iterdir()) if kit.exists() else []
    zp = OUT / f"{name}_postkit.zip"
    return dict(job=_job(f"postkit:{name}"), files=files, zip=zp.name if zp.exists() else None,
                text=(kit / "post.txt").read_text() if (kit / "post.txt").exists() else post_text(name))


# ================================================================ Brand Kits
KIT_KEYS_DEC = ("caption_style", "caption_size", "caption_y", "captions", "progress_bar", "mograph_theme", "sfx", "punch_in")


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:40] or "kit"


def kits():
    KITS.mkdir(exist_ok=True)
    out = []
    for f in sorted(KITS.glob("*.json")):
        k = vedit.jload(f, {})
        out.append(dict(id=f.stem, name=k.get("name", f.stem), accent=k.get("look", {}).get("accent"),
                        fonts=k.get("look", {}).get("fonts"), hook=k.get("hook", {}).get("type"), caption=k.get("dec", {}).get("caption_style")))
    return dict(kits=out, default=sa.settings().get("default_kit"))


def kit_save(name, body):
    dec = sa._dec(name)
    lk = {k: v for k, v in dec.get("look", {}).items() if k in ("palette", "accent", "fonts", "visuals", "extras")}
    hk = sa.get_look(name).get("hook", {})
    kit = dict(name=body.get("kit") or "My brand", look=lk, dec={k: dec[k] for k in KIT_KEYS_DEC if k in dec},
               hook=dict(type=hk.get("type"), kicker=hk.get("kicker", "")), saved=time.time(), version=1)
    KITS.mkdir(exist_ok=True)
    vedit.jsave(KITS / f"{_slug(kit['name'])}.json", kit)
    if body.get("default"):
        sa.set_settings({"default_kit": _slug(kit["name"])})
    return kits()


def kit_apply(name, kit_id):
    k = vedit.jload(KITS / f"{_slug(kit_id)}.json", None)
    if not k:
        return dict(ok=False, msg="kit not found")
    with sa.EDIT:
        dec = sa._dec(name)
        dec.setdefault("look", {}).update(k.get("look", {}))
        dec.update(k.get("dec", {}))
        sa._save_dec(name, dec)
        if k.get("hook", {}).get("type"):
            cur = sa.get_look(name).get("hook", {})
            sa.set_hook(name, dict(type=k["hook"]["type"], text=cur.get("text", ""), kicker=k["hook"].get("kicker") or cur.get("kicker", "")))
    return dict(ok=True, look=sa.get_look(name))


def kit_import(body):
    k = body.get("kit") if isinstance(body.get("kit"), dict) else body
    if not isinstance(k, dict) or "look" not in k:
        return dict(ok=False, msg="not a brand kit file")
    KITS.mkdir(exist_ok=True)
    vedit.jsave(KITS / f"{_slug(k.get('name', 'imported'))}.json", k)
    return kits()


def kit_file(kit_id):
    p = KITS / f"{_slug(kit_id)}.json"
    return p if p.exists() else None


def on_imported(name):
    """New upload finished transcribing: apply the default brand kit, if there is one."""
    d = sa.settings().get("default_kit")
    if d:
        kit_apply(name, d)


# ================================================================ live hook previews (2026 trend hooks)
_MG = None


def _mograph():
    global _MG
    if _MG is None:
        import mograph  # the real template code, so the preview is exactly what renders
        _MG = mograph
    return _MG


def hook_page(name, variant, text, kicker):
    """A 2026 trend hook as a live page in the project's look (motion/scenes/hkp_<variant>.html), timed in seconds."""
    if variant not in sa.V7_HOOKS:
        return dict(url=None)
    M = _mograph()
    dec = sa._dec(name)
    M.LOOK_DEC.clear(); M.LOOK_DEC.update(dec)
    sc = sa.v7_hook_fields(variant, text or sa.suggest_hook(name), kicker or "")
    dur = 4.6 if variant not in ("flip", "redact", "search") else 5.4
    inner = M.TEMPLATES[sc["type"]](dict(sc, _dur=dur), lambda v: float(v) if isinstance(v, (int, float)) else 0.12)
    sid = f"hkp_{variant}"
    (M.MOTION / "scenes").mkdir(parents=True, exist_ok=True)
    f = M.MOTION / "scenes" / f"{sid}.html"
    f.write_text(brandkit.brandize_page(M.page(sid, dur, inner, M.mograph_more.panel_of(sc)), dec))
    return dict(url=f"/motion/scenes/{sid}.html?v={int(f.stat().st_mtime * 1000)}", id=sid, dur=dur, sfx=sc.get("sfx", []))
