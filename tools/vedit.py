#!/usr/bin/env python3
"""vedit — BBD transcript-driven video editor.

Why it never chops words:
  * Cuts are decided on WORD INDICES from a word-level transcript, never on raw
    times, so a cut can only ever land in the gap between two words.
  * Every cut point is then refined against the real audio energy, so trailing
    consonants / breaths that Whisper's timestamps miss are kept.
  * Cut points are snapped to the video frame grid (no A/V drift over hundreds
    of cuts) and every splice gets a 12 ms audio fade (no clicks/pops).
  * `verify` re-transcribes the render and flags any word that went missing
    near a cut, then widens the padding at exactly that cut.

Subcommands: doctor, transcribe, plan, render, verify, locate
"""
from __future__ import annotations

import argparse
import bisect
import difflib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK, OUT = ROOT / "work", ROOT / "output"
STYLE = json.loads((ROOT / "tools" / "style.json").read_text())
MODEL = "mlx-community/whisper-large-v3-turbo"
FW_MODEL = os.environ.get("VEDIT_WHISPER", "large-v3-turbo")  # faster-whisper model (Windows / Intel Mac)

# ----------------------------------------------------------------- Mac + Windows
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
if IS_WIN:
    # Windows reads/writes text in the local code page by default; every file here is UTF-8 (emoji, “quotes”, Taglish).
    # Re-run the tool in Python's UTF-8 mode, and let every process it starts inherit it.
    os.environ["PYTHONUTF8"] = "1"
    if not sys.flags.utf8_mode and sys.argv and sys.argv[0].endswith(".py"):
        sys.exit(subprocess.call([sys.executable, "-X", "utf8", *sys.argv]))


def venv_py(env=".venv"):
    """The Python inside one of this folder's venvs (Windows keeps it in Scripts\\python.exe)."""
    return ROOT / env / ("Scripts/python.exe" if IS_WIN else "bin/python")


def node_dir():
    """The private Node that tools/setup installs (node + npx sit in tools/node on Windows, tools/node/bin elsewhere)."""
    return ROOT / "tools" / "node" if IS_WIN else ROOT / "tools" / "node" / "bin"


def npx():
    return shutil.which("npx", path=str(node_dir())) or shutil.which("npx") or "npx"


FINDERS = {"facebox": "cv2", "textbox": "rapidocr_onnxruntime", "personmask": "torchvision"}  # Python twin → module it needs


def finder(name):
    """A finder as a command: the Apple Vision build (tools/bin/<name>, Mac) or its cross-platform Python twin
    (tools/<name>.py: OpenCV faces, RapidOCR text, torchvision person cut-out). None when neither is installed."""
    b = ROOT / "tools" / "bin" / name
    if b.exists():
        return [str(b)]
    twin = ROOT / "tools" / f"{name}.py"
    import importlib.util
    if twin.exists() and name in FINDERS and importlib.util.find_spec(FINDERS[name]):
        return [sys.executable, str(twin)]
    return None


_vt = None


def has_vt():
    """ffmpeg has Apple's hardware H.264 encoder (Mac)."""
    global _vt
    if _vt is None:
        _vt = "h264_videotoolbox" in subprocess.run([binpath("ffmpeg"), "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    return _vt


def h264(bitrate="8M", crf=20):
    """Encoder arguments: Apple's hardware H.264 on a Mac, libx264 everywhere else."""
    return ["-c:v", "h264_videotoolbox", "-b:v", bitrate] if has_vt() else ["-c:v", "libx264", "-crf", str(crf), "-preset", "fast"]
# Seeding the prompt with fillers makes Whisper transcribe them instead of
# silently skipping them (otherwise "um"/"ano" hide inside word timings).
PROMPT = "Umm, uh, ah, so, ano, kasi, like... Taglish na usapan, okay? Beyond Breakeven Digital."

# Pause handling per format. Long-form keeps natural breathing room.
PRESETS = {
    "long":  dict(max_pause=0.55, keep_pause=0.30, pad_before=0.10, pad_after=0.18, min_cut=0.15, lead=0.20, tail=0.60),
    "mid":   dict(max_pause=0.40, keep_pause=0.22, pad_before=0.08, pad_after=0.15, min_cut=0.12, lead=0.12, tail=0.50),
    "short": dict(max_pause=0.30, keep_pause=0.16, pad_before=0.07, pad_after=0.13, min_cut=0.10, lead=0.08, tail=0.40),
}
FADE = 0.012


# ----------------------------------------------------------------- helpers
def die(msg):
    sys.exit(f"✗ {msg}")


_bins: dict[str, str] = {}


def binpath(name):
    if name in _bins:
        return _bins[name]
    own = ROOT / "tools" / "ffmpeg" / "bin" / (name + ".exe" if IS_WIN else name)  # Windows: setup.ps1's build, with libass
    if own.exists():
        os.environ["PATH"] = str(own.parent) + os.pathsep + os.environ["PATH"]
    p = str(own) if own.exists() else shutil.which(name)
    if not p:
        try:
            import static_ffmpeg
            static_ffmpeg.add_paths()
            p = shutil.which(name)
        except ImportError:
            pass
    if not p:
        die(f"{name} not found — run {'tools/setup.ps1' if IS_WIN else './tools/setup.sh'}")
    _bins[name] = p
    return p


def fpath(p):
    """A file path inside an ffmpeg filter graph, for use in '…': "/" separators and the Windows drive colon escaped (D\\:/…)."""
    return Path(p).as_posix().replace(":", "\\:")


def sh(args, capture=False):
    args = [str(x) for x in args]
    r = subprocess.run(args, capture_output=capture, text=True)
    if r.returncode:
        if capture:
            sys.stderr.write(r.stderr[-4000:])
        die(f"command failed: {Path(args[0]).name} (exit {r.returncode})")
    return r.stdout if capture else ""


def jload(p, default=None):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def jsave(p, obj):
    Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")


def tc(t):
    t = max(t, 0)
    m, s = divmod(t, 60)
    h, m = divmod(int(m), 60)
    return f"{h}:{m:02d}:{s:04.1f}" if h else f"{m:02d}:{s:04.1f}"


def parse_tc(s):
    t = 0.0
    for x in s.split(":"):
        t = t * 60 + float(x)
    return t


def norm(w):
    return re.sub(r"[^\w']+", "", w.lower())


def probe(src):
    d = json.loads(sh([binpath("ffprobe"), "-v", "error", "-print_format", "json",
                       "-show_streams", "-show_format", src], capture=True))
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    if not v:
        die("no video stream")
    fps_r = v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1"
    num, den = (float(x) for x in fps_r.split("/"))
    fps = num / den if den else 0
    if not 1 < fps < 121:
        fps_r, fps = "30/1", 30.0
    w, h = int(v["width"]), int(v["height"])
    rot = int(v.get("tags", {}).get("rotate", 0) or 0)
    for sd in v.get("side_data_list", []):
        rot = int(sd.get("rotation", rot) or rot)
    if abs(rot) % 180 == 90:
        w, h = h, w
    if v.get("color_transfer") in ("arib-std-b67", "smpte2084"):  # iPhone HDR: brand orange plays back RED (BT.2020 tags)
        pass  # HLG sources are kept as shot; vedit converts the graphics into HLG instead (tools/hdr.py)
    return dict(w=w, h=h, fps=fps, fps_r=fps_r, dur=float(d["format"]["duration"]), trc=v.get("color_transfer", ""),
                audio=any(s["codec_type"] == "audio" for s in d["streams"]))


def ctx(video):
    src = Path(video).expanduser().resolve()
    if not src.exists():
        die(f"file not found: {src}")
    wd = WORK / src.stem
    wd.mkdir(parents=True, exist_ok=True)
    meta = jload(wd / "meta.json")
    if not meta or meta.get("src") != str(src):
        meta = probe(src)
        meta["src"] = str(src)
        jsave(wd / "meta.json", meta)
    return src, wd, meta


def extract_wav(src, wav):
    sh([binpath("ffmpeg"), "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", wav])


_FW = None  # the faster-whisper model, loaded once


def whisper_words(wav, language=None, prompt=PROMPT):
    """Returns [(word, start, end, prob)] and detected language."""
    binpath("ffmpeg")  # Whisper shells out to ffmpeg; make sure the bundled one is on PATH
    try:
        import mlx_whisper
        r = mlx_whisper.transcribe(str(wav), path_or_hf_repo=MODEL, word_timestamps=True,
                                   language=language, initial_prompt=prompt,
                                   condition_on_previous_text=False)
        ws = [(w["word"], w["start"], w["end"], w.get("probability", 1.0))
              for s in r["segments"] for w in s.get("words", [])]
        return ws, r.get("language")
    except ImportError:
        global _FW
        if _FW is None:
            from faster_whisper import WhisperModel
            _FW = WhisperModel(FW_MODEL, device="cpu", compute_type="int8")
        import numpy as np  # decode with our ffmpeg: faster-whisper's own decoder breaks on new PyAV releases
        pcm = subprocess.run([binpath("ffmpeg"), "-v", "error", "-i", str(wav), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        segs, info = _FW.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True, language=language,
                                  initial_prompt=prompt, condition_on_previous_text=False)
        ws = [(w.word, w.start, w.end, w.probability) for s in segs for w in (s.words or [])]
        return ws, info.language


def fixed_text(words, fixes, i):
    return fixes.get(str(i), words[i]["w"]).strip()


# ----------------------------------------------------------------- doctor
def cmd_doctor(a):
    ok = True
    for name in ("ffmpeg", "ffprobe"):
        try:
            print(f"✓ {name}: {binpath(name)}")
        except SystemExit:
            print(f"✗ {name} missing")
            ok = False
    if ok:
        ver = sh([binpath("ffmpeg"), "-version"], capture=True).splitlines()[0]
        enc = sh([binpath("ffmpeg"), "-hide_banner", "-encoders"], capture=True)
        flt = sh([binpath("ffmpeg"), "-hide_banner", "-filters"], capture=True)
        print(f"  {ver}")
        print(f"  {'✓' if 'h264_videotoolbox' in enc else '✓' if 'libx264' in enc else '✗'} H.264 encoder ({'videotoolbox' if 'h264_videotoolbox' in enc else 'libx264'})")
        print(f"  {'✓' if re.search(r'^\s*\S+\s+ass\s', flt, re.M) else '✗'} captions (libass)")
    for mod in ("mlx_whisper", "faster_whisper"):
        try:
            __import__(mod)
            print(f"✓ transcription: {mod}")
            break
        except ImportError:
            continue
    else:
        print("✗ no whisper backend")
        ok = False
    import shutil  # the Studio's extras — each one is optional, the edit still runs without it
    for b, what in (("personmask", "text behind you (person cut-out)"), ("facebox", "Edit Health: graphics over the face"),
                    ("textbox", "Style references: caption finder")):
        f = finder(b)
        how = "Apple Vision" if f and len(f) == 1 else "Python" if f else "not installed"
        print(f"{'✓' if f else '–'} {what} ({how})")
    tm = (ROOT / "tools" / "bin" / "tosdr").exists()
    print(f"{'✓' if tm else '✓' if 'zscale' in sh([binpath('ffmpeg'), '-hide_banner', '-filters'], capture=True) else '–'} natural colour from iPhone HDR "
          f"({'Apple tone mapping' if tm else 'ffmpeg tone mapping'})")
    print(f"{'✓' if (node_dir() / ('node.exe' if IS_WIN else 'node')).exists() or shutil.which('node') else '✗'} node (motion-graphics renderer)")
    print(f"{'✓' if venv_py('.venv-df').exists() else '–'} voice cleanup (DeepFilterNet, .venv-df)")
    try:
        __import__("transformers")
        print("✓ literal listening (MMS) for repeats / clipped words")
    except ImportError:
        print("– literal listening (MMS) not installed")
    print(f"{'✓' if shutil.which('claude') else '–'} Claude Code CLI (Studio: Auto-edit, Apply notes)")
    print("ready" if ok else "run tools\\setup.ps1" if IS_WIN else "run ./tools/setup.sh")


# ----------------------------------------------------------------- transcribe
LATIN = re.compile(r"^[A-Za-z0-9Ññ'’\-.,?!%…]{1,20}$")
# classic Whisper hallucinations on silence
GHOSTS = {"you", "thank", "thanks", "bye", "goodnight", "good", "night", "huh", "ah", "uh", "um", "oh", "hmm", "stop"}


def write_transcript_files(wd, words, meta, lang):
    jsave(wd / "transcript.json", dict(language=lang, words=words))
    (wd / "words.tsv").write_text("i\tstart\tend\tword\n" + "".join(
        f"{w['i']}\t{w['s']:.2f}\t{w['e']:.2f}\t{w['w']}\n" for w in words))
    lines = [f"# Transcript — {Path(meta['src']).name} ({tc(meta['dur'])}, {len(words)} words, lang={lang})",
             "# #<index of first word on the line>  <time>  text · ⏸ = pause ≥0.7s · (?word) = low confidence"
             " · [+word] = recovered by gap re-listen",
             ""]
    cur: list = []

    def fmt(w):
        t = w["w"] if w["p"] >= 0.5 else f"(?{w['w']})"
        return f"[+{t}]" if w.get("fill") else t

    def flush():
        if cur:
            lines.append(f"#{cur[0]['i']:<5} {tc(cur[0]['s']):>9}  " + " ".join(fmt(w) for w in cur))
            cur.clear()

    for w in words:
        if cur:
            gap = w["s"] - cur[-1]["e"]
            if gap >= 0.7:
                flush()
                lines.append(f"{'':16}⏸ {gap:.1f}s")
            elif len(cur) >= 16 or re.search(r"[.?!]$", cur[-1]["w"]):
                flush()
        cur.append(w)
    flush()
    (wd / "transcript.txt").write_text("\n".join(lines) + "\n")


def fill_gaps(wd, words, meta, lang, min_gap=1.2):
    """Re-listen to every long silence on its own: Whisper drops quiet or mumbled words
    inside long files, and a dropped word looks like a pause that would get cut."""
    import numpy as np
    wav, clip = wd / "audio.wav", wd / "gap.wav"
    db = np.load(wd / "energy.npy")
    thr = max(np.percentile(db, 10) + 6, np.percentile(db, 90) - 30)

    def voiced(s, e):  # at least 40% of the word's frames carry voice energy
        seg = db[int(s * 100): max(int(e * 100), int(s * 100) + 1)]
        return len(seg) and (seg > thr).mean() >= 0.4

    gaps = []
    for k in range(len(words) + 1):
        prev_e = words[k - 1]["e"] if k else 0.0
        next_s = words[k]["s"] if k < len(words) else meta["dur"]
        if next_s - prev_e >= min_gap:
            gaps.append((k, prev_e, next_s))
    found: dict[int, list] = {}
    for n, (k, a0, a1) in enumerate(gaps, 1):
        print(f"\r• re-listening to gaps {n}/{len(gaps)}", end="", flush=True)
        c0 = max(0.0, a0 - 0.15)
        sh([binpath("ffmpeg"), "-y", "-v", "error", "-ss", f"{c0:.3f}", "-to", f"{a1 + 0.15:.3f}",
            "-i", wav, clip])
        ws, _ = whisper_words(clip, lang, prompt=None)
        got = []
        for t, s, e, p in ws:
            t, s, e = t.strip(), s + c0, e + c0
            if (t and LATIN.match(t) and len(re.sub(r"[^A-Za-zÑñ]", "", t)) >= 2
                    and norm(t) not in GHOSTS and p >= 0.3
                    and a0 + 0.05 < s < a1 - 0.05 and voiced(s, e)):
                got.append(dict(w=t, s=round(s, 3), e=round(min(e, a1 - 0.02), 3), p=round(p, 2), fill=True))
        toks = [norm(g["w"]) for g in got]
        if got and max(toks.count(t) for t in toks) < 3:  # repetition loop = hallucination
            found[k] = got
    print()
    remap, new = {}, []
    for k in range(len(words) + 1):
        for g in found.get(k, []):
            g["i"] = len(new)
            new.append(g)
        if k < len(words):
            w = dict(words[k])
            remap[k] = w["i"] = len(new)
            new.append(w)
    return new, remap, sum(len(v) for v in found.values())


def remap_decisions(wd, remap):
    """Keep an existing decisions.json valid after words were inserted."""
    p = wd / "decisions.json"
    dec = jload(p)
    if not dec:
        return
    p.with_suffix(".json.bak").write_text(p.read_text())
    for r in dec.get("remove", []):
        r["from"], r["to"] = remap[r["from"]], remap[r["to"]]
    if dec.get("hook"):
        dec["hook"] = {"from": remap[dec["hook"]["from"]], "to": remap[dec["hook"]["to"]]}
    dec["fixes"] = {str(remap[int(k)]): v for k, v in dec.get("fixes", {}).items()}
    jsave(p, dec)
    print("• decisions.json word indices updated (backup: decisions.json.bak)")


def cmd_transcribe(a):
    import numpy as np
    src, wd, meta = ctx(a.video)
    wav = wd / "audio.wav"
    tr = jload(wd / "transcript.json")
    if a.fill_only:
        tr or die("no transcript yet — run transcribe first")
        words, lang = tr["words"], tr["language"]
    else:
        print(f"• {src.name}: {tc(meta['dur'])}, {meta['w']}x{meta['h']} @ {meta['fps']:.2f}fps")
        extract_wav(src, wav)
        print("• transcribing (word-level)…", flush=True)
        raw, lang = whisper_words(wav, a.language)
        words, last = [], 0.0
        for t, s, e, p in raw:
            if not t.strip():
                continue
            s = max(s, last)
            e = max(e, s + 0.02)
            words.append(dict(i=len(words), w=t.strip(), s=round(s, 3), e=round(e, 3), p=round(p, 2)))
            last = s
        with wave.open(str(wav)) as f:
            x = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        hop = 160  # 10 ms at 16 kHz
        n = len(x) // hop
        rms = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1) + 1e-10)
        np.save(wd / "energy.npy", (20 * np.log10(rms)).astype(np.float32))
    if not a.no_fill:
        words, remap, n_added = fill_gaps(wd, words, meta, lang)
        print(f"• recovered {n_added} words Whisper missed")
        if a.fill_only and n_added:
            remap_decisions(wd, remap)
    write_transcript_files(wd, words, meta, lang)
    print(f"✓ {len(words)} words → {wd.relative_to(ROOT)}/transcript.txt")


# ----------------------------------------------------------------- plan
def auto_mode(dur):
    return "short" if dur <= 30 else "mid" if dur <= 60 else "long"


def cmd_plan(a):
    import numpy as np
    src, wd, meta = ctx(a.video)
    tr = jload(wd / "transcript.json") or die("run transcribe first")
    words = tr["words"]
    if not words:
        die("no speech in transcript")
    db = np.load(wd / "energy.npy")
    dec = jload(wd / "decisions.json", {})
    fixes = dec.get("fixes", {})
    mode = a.mode or dec.get("mode") or auto_mode(meta["dur"])
    P = dict(PRESETS[mode], **dec.get("tuning", {}))
    ov = jload(wd / "pad_overrides.json", {})
    fps, dur = meta["fps"], meta["dur"]

    removed: dict[int, str] = {}
    for r in dec.get("remove", []):
        for i in range(r["from"], r["to"] + 1):
            removed[i] = r.get("reason", "removed")
    protect = [(p["start"], p["end"]) for p in dec.get("protect", [])]

    # voice threshold: above room tone (ignore digital-silence frames from noise gates)
    live = db[db > -90]
    floor = np.percentile(live, 10) if len(live) else np.percentile(db, 10)
    thr = max(floor + 10, np.percentile(db, 90) - 24)
    nf = len(db)

    def loud(f):
        return 0 <= f < nf and db[f] > thr

    def true_end(t, limit):
        """Extend past Whisper's end while speech energy continues (max +350 ms)."""
        f = int(t * 100)
        lim = max(f, int(min(limit, t + 0.35) * 100))
        quiet = 0
        while f < lim:
            quiet = 0 if loud(f) else quiet + 1
            if quiet >= 3:
                return max(t, (f - 2) / 100)
            f += 1
        return max(t, lim / 100)

    def true_start(t, limit):
        """Pull earlier while speech energy precedes Whisper's start (max −250 ms)."""
        f = int(t * 100)
        lim = min(f, int(max(limit, t - 0.25) * 100))
        quiet = 0
        while f > lim:
            quiet = 0 if loud(f - 1) else quiet + 1
            if quiet >= 3:
                return min(t, (f + 2) / 100)
            f -= 1
        return min(t, lim / 100)

    # Whisper often stretches a word across the silence after (or before) it; shrink
    # over-long words back to their voiced part so those pauses can be tightened too.
    for w in words:
        if w["e"] - w["s"] > 0.7:
            f_s, f = int(w["s"] * 100), int(w["e"] * 100)
            while f > f_s + 20 and not loud(f):
                f -= 1
            if (f + 1) / 100 + 0.04 < w["e"] - 0.25:
                w["e"] = round((f + 1) / 100 + 0.04, 3)
            f, f_e = f_s, int(w["e"] * 100)
            while f < f_e - 20 and not loud(f):
                f += 1
            if f / 100 - 0.03 > w["s"] + 0.25:
                w["s"] = round(f / 100 - 0.03, 3)

    def snap_up(t):
        return min(dur, math.ceil(t * fps - 1e-6) / fps)

    def snap_dn(t):
        return max(0.0, math.floor(t * fps + 1e-6) / fps)

    def protected(t0, t1):
        return any(t0 < pe and t1 > ps for ps, pe in protect)

    kept = [w for w in words if w["i"] not in removed]
    if not kept:
        die("every word is removed")
    first = kept[0]
    prev_e = words[first["i"] - 1]["e"] + 0.02 if first["i"] else 0.0
    seg_start = snap_dn(max(prev_e, true_start(first["s"], prev_e) - P["lead"]))

    segs, cuts, out_len, kept_voice = [], [], 0.0, []
    for A, B in zip(kept, kept[1:]):
        ia, ib = A["i"], B["i"]
        adjacent = ib == ia + 1
        gap = B["s"] - A["e"]
        if adjacent and (gap <= P["max_pause"] or a.no_pause_cuts or protected(A["e"], B["s"])):
            continue
        nxt_s, prv_e = words[ia + 1]["s"], words[ib - 1]["e"]
        ea, sb = true_end(A["e"], nxt_s), true_start(B["s"], prv_e)
        half = P["keep_pause"] / 2
        out_t = ea + max(P["pad_after"], half) + ov.get(f"after:{ia}", 0)
        in_t = sb - max(P["pad_before"], half) - ov.get(f"before:{ib}", 0)
        if not adjacent:  # never leak into the words being removed
            out_t = min(out_t, max(ea, nxt_s - 0.02))
            in_t = max(in_t, min(sb, prv_e + 0.02))
        out_t, in_t = snap_up(out_t), snap_dn(in_t)
        if in_t - out_t < (P["min_cut"] if adjacent else 1e-3) or out_t <= seg_start:
            continue
        if adjacent:  # Whisper sometimes misses speech — never trim a "pause" that has voice in it
            run = best = 0
            for f in range(int(out_t * 100), int(in_t * 100)):
                run = run + 1 if loud(f) else 0
                best = max(best, run)
            if best >= 35:
                kept_voice.append((A["e"], B["s"]))
                continue
        segs.append([seg_start, out_t])
        out_len += out_t - seg_start
        seg_start = in_t
        cuts.append(dict(t=out_t, at=round(out_len, 3), after=ia, before=ib,
                         reason="pause" if adjacent else " + ".join(
                             dict.fromkeys(removed.get(k, "removed") for k in range(ia + 1, ib))),
                         removed=" ".join(words[k]["w"] for k in range(ia + 1, ib)),
                         dur=round(in_t - out_t, 2)))
    last = kept[-1]
    nxt = words[last["i"] + 1]["s"] - 0.02 if last["i"] + 1 < len(words) else dur
    end = min(nxt, true_end(last["e"], nxt) + P["tail"]) if last["i"] + 1 < len(words) \
        else min(dur, true_end(last["e"], dur) + P["tail"])
    segs.append([seg_start, snap_up(max(end, seg_start + 1 / fps))])

    # cut_ranges: non-word noise (laughs, bumps, off-mic sounds) removed by original time
    for c in dec.get("cut_ranges", []):
        c0, c1 = snap_up(c["start"]), snap_dn(c["end"])
        new_segs = []
        for S, E in segs:
            if c1 <= S or c0 >= E:
                new_segs.append([S, E])
                continue
            if c0 > S:
                new_segs.append([S, c0])
            if c1 < E:
                new_segs.append([c1, E])
        segs = [s_ for s_ in new_segs if s_[1] - s_[0] >= 1 / fps]
        cuts.append(dict(t=c0, after=-1, before=-1, reason=c.get("reason", "noise"),
                         removed=f"(sound {tc(c['start'])}–{tc(c['end'])})", dur=round(c1 - c0, 2)))
    keeps = sorted((max(0.0, snap_dn(k["start"])), min(dur, snap_up(k["end"]))) for k in dec.get("keep_ranges", []))
    if keeps:  # keep_ranges: time the editor explicitly dragged back in (dead air, breaths, removed words)
        merged = []
        for a_, b_ in sorted([tuple(x) for x in segs] + keeps):
            if merged and a_ <= merged[-1][1] + 1.5 / fps:
                merged[-1][1] = max(merged[-1][1], b_)
            else:
                merged.append([a_, b_])
        segs = merged
        cuts = [c for c in cuts if not any(a_ + 0.01 < c["t"] < b_ - 0.01 for a_, b_ in segs)]
    # Dead-air pass on the real audio: Whisper's word times are often early/late, so trim every
    # flat stretch the waveform shows — clip heads/tails and long silences inside clips.
    if not dec.get("no_silence_pass"):
        keep_iv = [(k["start"], k["end"]) for k in dec.get("keep_ranges", [])]
        in_keep = lambda t: any(a_ - 0.05 <= t <= b_ + 0.05 for a_, b_ in keep_iv)
        # soft syllables and gated word edges sit around −40 dB, far above room tone (≈ floor), so only
        # frames near the room floor count as dead air here — never trim a quiet word ending as "silence"
        thr_sil = min(thr, max(floor + 14, np.percentile(db, 90) - 40))
        # speech = loud frames + SHORT soft runs touching them (soft syllables, gated word edges). A long flat
        # soft stretch is the room heard through an open noise gate (≈ −45 dB) — that is dead air.
        loud_ = db > -40
        loud_ &= np.r_[False, loud_[:-1]] | np.r_[loud_[1:], False]  # a lone 10 ms spike is not speech
        # flat room noise heard through an open gate: steady level (rolling std < 2.5 dB over 150 ms), never speech
        k_ = 15
        pad_ = np.pad(db, (k_ // 2, k_ - 1 - k_ // 2), mode="edge")
        win_ = np.lib.stride_tricks.sliding_window_view(pad_, k_)
        plateau = (db < -38) & (db > -60) & (win_.std(axis=1) < 2.5)
        soft_ = (db > thr_sil) & ~loud_ & ~plateau
        voiced = loud_.copy()
        f = 0
        while f < nf:
            if soft_[f]:
                g = f
                while g < nf and soft_[g]:
                    g += 1
                touch = loud_[max(0, f - 5):f].any() or loud_[g:g + 5].any()
                if g - f <= 25 and touch:
                    voiced[f:g] = True
                f = g
            else:
                f += 1
        lead_keep = min(0.10, P["keep_pause"] / 2)
        tail_keep = min(0.16, P["keep_pause"] / 2 + 0.04)
        max_sil = P["max_pause"]

        def first_voice(a_, b_):  # first frame starting a run of ≥3 voiced frames
            f, run = int(a_ * 100), 0
            while f < int(b_ * 100):
                run = run + 1 if (f < nf and voiced[f]) else 0
                if run >= 3:  # include any short voiced bursts just before (gated / soft onsets)
                    f0 = f - 2
                    for g in range(f0 - 1, max(int(a_ * 100), f0 - 18) - 1, -1):
                        if g < nf and voiced[g]:
                            f0 = g
                    return f0 / 100
                f += 1
            return None

        def last_voice(a_, b_):
            f, run = int(b_ * 100) - 1, 0
            while f >= int(a_ * 100):
                run = run + 1 if (0 <= f < nf and voiced[f]) else 0
                if run >= 3:  # include trailing soft bursts (word endings, gated tails)
                    f1 = f + 2
                    for g in range(f1 + 1, min(int(b_ * 100), f1 + 18) + 1):
                        if g < nf and voiced[g]:
                            f1 = g
                    return (f1 + 1) / 100
                f -= 1
            return None

        tightened, sil_cuts = [], 0
        for S, E in segs:
            vs, ve = first_voice(S, E), last_voice(S, E)
            if vs is None:
                if any(a_ < E and b_ > S for a_, b_ in keep_iv):
                    tightened.append([S, E])
                continue  # nothing but silence
            if not in_keep(S):
                S = max(S, snap_dn(vs - lead_keep))
            if not in_keep(E):
                E = min(E, snap_up(ve + tail_keep))
            # long silences inside the clip
            f, start_sil, cur = int(S * 100), None, S
            while f <= int(E * 100):
                v = f < nf and voiced[f]
                if not v and start_sil is None:
                    start_sil = f
                if v and start_sil is not None:
                    a_, b_ = start_sil / 100, f / 100
                    if b_ - a_ > max_sil and not in_keep((a_ + b_) / 2):
                        out_t, in_t = snap_up(a_ + tail_keep), snap_dn(b_ - lead_keep)
                        if in_t - out_t > 0.08:
                            tightened.append([cur, out_t])
                            cur = in_t
                            sil_cuts += 1
                    start_sil = None
                f += 1
            if E - cur > 1 / fps:
                tightened.append([cur, E])
        segs = [x for x in tightened if x[1] - x[0] >= 2 / fps]
        cuts = [c for c in cuts if not any(a_ + 0.01 < c["t"] < b_ - 0.01 for a_, b_ in segs)]
        if sil_cuts:
            cuts += [dict(t=0, after=-1, before=-1, reason="pause", removed="", dur=0)] * 0
    # Splice smoothing: never leave a splice in the middle of sound. If a clip starts or
    # ends while the voice is still loud, slide that edge to the nearest quiet moment.
    def quiet_at(f):
        return all(not (0 <= g < nf) or db[g] < thr for g in range(f, f + 3))

    def loud_edge(a_, b_):
        seg = db[max(0, int(a_ * 100)):max(int(a_ * 100) + 1, int(b_ * 100))]
        return len(seg) and seg.max() > thr + 12

    smoothed = []
    for n_, (S, E) in enumerate(segs):
        prev_e = smoothed[-1][1] if smoothed else 0.0
        next_s = segs[n_ + 1][0] if n_ + 1 < len(segs) else dur
        if loud_edge(S, S + 0.04):
            f0 = int(S * 100)
            back = next((f for f in range(f0, max(int(prev_e * 100) + 1, f0 - 30), -1) if quiet_at(f - 3)), None)
            fwd = next((f for f in range(f0, min(int(E * 100) - 10, f0 + 20)) if quiet_at(f)), None)
            if back is not None:
                S = snap_dn(back / 100 - 0.01)
            else:  # no silence before (speech runs into the cut): deepest dip at or before the edge
                lo_, hi_ = max(int(prev_e * 100) + 1, f0 - 15), f0 + 1
                if hi_ > lo_:
                    S = snap_dn((lo_ + int(np.argmin(db[lo_:hi_]))) / 100)
        if loud_edge(E - 0.04, E):
            f0 = int(E * 100)
            fwd = next((f for f in range(f0, min(int(next_s * 100) - 1, f0 + 30)) if quiet_at(f)), None)
            back = next((f for f in range(f0, max(int(S * 100) + 10, f0 - 20), -1) if quiet_at(f - 3)), None)
            if fwd is not None:
                E = snap_up(fwd / 100 + 0.02)
            else:  # deepest dip at or after the edge — never pull an end back into the word
                lo_, hi_ = f0, min(int(next_s * 100) - 1, f0 + 15)
                if hi_ > lo_:
                    E = snap_up((lo_ + int(np.argmin(db[lo_:hi_]))) / 100)
        if E - S >= 2 / fps:
            smoothed.append([S, E])
    segs = smoothed
    # The phone's noise gate splits words ("Da·pat", "Pa·ngatlo"): a soft onset or ending sits 0.1–0.3 s away
    # from the rest of the word with −100 dB in between. Pull clip edges out to include those pieces.
    burst = db > -40
    crs = [(c["start"], c["end"]) for c in dec.get("cut_ranges", [])]
    crs += [(words[k]["s"], words[k]["e"]) for k in removed if k < len(words)]  # never pull removed takes back in
    in_cut = lambda t: any(a_ - 0.005 <= t <= b_ + 0.005 for a_, b_ in crs)
    bridged = []

    def blip(f_from, step, stop):
        """Isolated speech blip reached from f_from across gate silence: (start, end) frames, or None.
        Only the gate-split pattern counts — a short piece (≤0.18 s) with gate (<−70 dB) between it and the
        clip edge, and quiet (non-speech) on its far side — never a whole word of a neighbouring take."""
        f, gap = f_from, 0
        while (f > stop if step < 0 else f < stop) and not in_cut(f / 100) and gap <= 30:
            if burst[f]:
                break
            if db[f] > -70:  # soft/room frames instead of gate → not a gate split
                return None
            gap += 1
            f += step
        else:
            return None
        if not burst[f] or gap < 3:
            return None
        g = f
        while 0 <= g + step < nf and burst[g + step] and abs(g - f) < 19:
            g += step
        if abs(g - f) >= 18:
            return None
        far = range(g + step, g + step * 13, step)
        if any(0 <= h < nf and (burst[h] or in_cut(h / 100)) for h in far):
            return None
        return (min(f, g), max(f, g))

    for n_, (S, E) in enumerate(segs):
        prev_e = bridged[-1][1] if bridged else 0.0
        next_s = segs[n_ + 1][0] if n_ + 1 < len(segs) else dur
        bh = blip(int(S * 100) - 1, -1, max(int(prev_e * 100) + 2, int(S * 100) - 50))
        if bh:
            S = snap_dn(max(prev_e, bh[0] / 100 - 0.02))
        bt = blip(int(E * 100), 1, min(int(next_s * 100) - 2, int(E * 100) + 50, nf - 14))
        if bt:
            E = snap_up(min(next_s, (bt[1] + 1) / 100 + 0.03))
        if bridged and S <= bridged[-1][1] + 1 / fps:
            bridged[-1][1] = max(bridged[-1][1], E)
        else:
            bridged.append([S, E])
    segs = bridged
    # Close gate holes around isolated blips on the EDITED timeline: a short burst (≤0.2 s, e.g. "Da", "sa",
    # "Then", "kasi") with up to 0.45 s of gate silence between it and its neighbouring speech sounds chopped
    # ("Da … pat"). Shrink those holes to a few frames — wherever they are, inside a clip or across a cut.
    gate = db < -70
    seq = [(f, n) for n, (S, E) in enumerate(segs) for f in range(int(round(S * 100)), min(int(round(E * 100)), nf))]
    loud_o = [db[f] > -40 for f, _ in seq]
    runs_o, i_ = [], 0
    while i_ < len(seq):
        if loud_o[i_]:
            j_ = i_
            while j_ + 1 < len(seq) and (loud_o[j_ + 1] or (j_ + 3 < len(seq) and any(loud_o[j_ + 2:j_ + 4]))):
                j_ += 1
            runs_o.append([i_, j_ + 1])
            i_ = j_ + 1
        else:
            i_ += 1
    drop = []
    for r0, r1 in zip(runs_o, runs_o[1:]):
        h0, h1 = r0[1], r1[0]
        if not 8 <= h1 - h0 <= 45 or sum(gate[seq[k][0]] for k in range(h0, h1)) < 0.6 * (h1 - h0):
            continue
        if r0[1] - r0[0] <= 20 or r1[1] - r1[0] <= 20:
            drop.append((h0 + 2, h1 - 2))
    holes = 0
    if drop:
        dropset = set(k for d0, d1 in drop for k in range(d0, d1))
        kept_f = [seq[k][0] for k in range(len(seq)) if k not in dropset]
        new_segs, st_ = [], None
        for k, f in enumerate(kept_f):
            if st_ is None:
                st_ = f
            if k + 1 == len(kept_f) or kept_f[k + 1] != f + 1:
                new_segs.append([st_, f + 1])
                st_ = None
        # back to seconds on the video frame grid (only shrink holes, never cut into speech)
        segs2 = []
        for f0, f1 in new_segs:
            S, E = snap_dn(f0 / 100), snap_up(f1 / 100)
            if segs2 and S <= segs2[-1][1]:
                segs2[-1][1] = max(segs2[-1][1], E)
            else:
                segs2.append([S, E])
        holes = len(drop)
        segs = segs2
    for c in dec.get("cut_ranges", []):
        c0, c1 = snap_up(c["start"]), snap_dn(c["end"])
        segs = [x for S, E in segs for x in ([[S, E]] if c1 <= S or c0 >= E else
                                             ([[S, c0]] if c0 > S else []) + ([[c1, E]] if c1 < E else []))]
    segs = [x for x in segs if x[1] - x[0] >= 1 / fps]
    if segs and not dec.get("no_silence_pass"):  # let the last word ring out instead of ending abruptly
        segs[-1][1] = max(segs[-1][1], min(dur, snap_up(segs[-1][1] + dec.get("ring_out", 0.45))))  # 0 = end hard (e.g. hand over the lens)
    hook, hook_segs = None, []
    if dec.get("hook"):
        h = dec["hook"]
        i0, i1 = h["from"], h["to"]
        lo = words[i0 - 1]["e"] + 0.02 if i0 else 0.0
        hi = words[i1 + 1]["s"] - 0.02 if i1 + 1 < len(words) else dur
        hs = h.get("start", max(lo, true_start(words[i0]["s"], lo) - 0.06))  # "start"/"end" (seconds) pin the edges to a dip
        he = h.get("end", min(hi, true_end(words[i1]["e"], hi) + P["pad_after"] + 0.10))
        hook = [snap_dn(hs), snap_up(he)]
        # the cold open keeps the body's own cuts inside the line (self-corrections, stutters)
        hook_segs = [x for S, E in segs if E > hook[0] and S < hook[1]
                     for x in [[max(S, hook[0]), min(E, hook[1])]] if x[1] - x[0] >= 1 / fps] or [hook]
        if h.get("move"):  # moved instead of copied: the line plays only at the top
            segs = [x for S, E in segs for x in ([[S, E]] if E <= hook[0] or S >= hook[1] else
                                                 ([[S, hook[0]]] if S < hook[0] else []) + ([[hook[1], E]] if E > hook[1] else []))]
            segs = [x for x in segs if x[1] - x[0] >= 1 / fps]
    hook_dur = sum(E - S for S, E in hook_segs)
    for c in cuts:  # edited-timeline position of every cut
        c["at"] = round(hook_dur + sum(E - S for S, E in segs if E <= c["t"] + 1e-6), 3)
    cuts.sort(key=lambda c: c["at"])

    # map every kept word to its time in the edited video
    starts = [w["s"] for w in words]
    keep_set = {w["i"] for w in kept}
    nh = len(hook_segs)
    if hook:
        keep_set |= {k for k in range(dec["hook"]["from"], dec["hook"]["to"] + 1) if k not in removed}
    words_out, off, all_segs = [], 0.0, hook_segs + segs
    offs = []
    for S, E in all_segs:
        offs.append(off)
        off += E - S
    # a word belongs to the segment holding most of it (Whisper starts/ends are often early/late)
    best: dict[int, tuple] = {}
    for n, (S, E) in enumerate(all_segs):
        for k in range(bisect.bisect_left(starts, S - 3), bisect.bisect_left(starts, E)):
            if k not in keep_set:
                continue
            ov = min(words[k]["e"], E) - max(words[k]["s"], S)
            if ov > 0.05 and (n < nh and not dec["hook"].get("move")) or ov > 0.05 and (k not in best or ov > best[k][0]):
                if n < nh and not dec["hook"].get("move"):  # copied cold open: the word also stays in the body
                    words_out.append([k, round(offs[n] + max(0.0, words[k]["s"] - S), 3), round(offs[n] + min(words[k]["e"], E) - S, 3)])
                else:
                    best[k] = (ov, n)
    # every kept word must reach the captions: words whose (often imprecise) timing fell into a removed gap
    # or a closed gate hole go to the nearest clip
    for k in keep_set:
        if k in best or (hook and not dec["hook"].get("move") and dec["hook"]["from"] <= k <= dec["hook"]["to"]):
            continue
        mid = (words[k]["s"] + words[k]["e"]) / 2
        n = min(range(len(all_segs)), key=lambda q: 0 if all_segs[q][0] <= mid <= all_segs[q][1]
                else min(abs(mid - all_segs[q][0]), abs(mid - all_segs[q][1])))
        S, E = all_segs[n]
        if min(abs(mid - S), abs(mid - E)) < 1.5 or S <= mid <= E:
            best[k] = (0.0, n)
            words[k]["s"], words[k]["e"] = min(max(words[k]["s"], S), E - 0.05), min(max(words[k]["e"], S + 0.05), E)
    for k, (ov, n) in sorted(best.items()):
        S, E = all_segs[n]
        words_out.append([k, round(offs[n] + max(words[k]["s"], S) - S, 3), round(offs[n] + min(words[k]["e"], E) - S, 3)])
    words_out.sort(key=lambda x: x[1])
    new_dur = off

    jsave(wd / "edl.json", dict(mode=mode, fps=fps, fps_r=meta["fps_r"], hook=hook, hook_segs=hook_segs, segments=segs,
                                cuts=cuts, words_out=words_out, orig_dur=dur, new_dur=new_dur))

    # ---- review sheet
    content = [c for c in cuts if c["reason"] != "pause"]
    pauses = [c for c in cuts if c["reason"] == "pause"]
    L = [f"# Edit review — {src.name}", "",
         f"**{tc(dur)} → {tc(new_dur)}** (−{tc(dur - new_dur)}) · mode **{mode}** · "
         f"{len(pauses)} pause trims ({sum(c['dur'] for c in pauses):.0f}s) · {len(content)} content cuts", ""]
    if hook:
        ht = " ".join(fixed_text(words, fixes, k) for k in range(dec["hook"]["from"], dec["hook"]["to"] + 1))
        L += [f"**Cold-open hook ({hook_dur:.1f}s{', moved' if dec['hook'].get('move') else ''}):** “{ht}”", ""]
    long_words = [w for w in words if w["i"] in keep_set and w["e"] - w["s"] > 1.2 and not w.get("patched")]
    if long_words:
        L += ["**Suspiciously long words (may hide a retake — re-listen):** "
              + ", ".join(f"#{w['i']} “{w['w']}” orig {tc(w['s'])} ({w['e'] - w['s']:.1f}s)" for w in long_words), ""]
    if kept_voice:
        L += ["**Pauses kept because they contain voice Whisper didn't transcribe** (check these spots): "
              + ", ".join(f"orig {tc(s)}–{tc(e)}" for s, e in kept_voice), ""]
    L += ["## Content cuts — check these", ""]
    if content:
        L += ["| # | at (edited) | removed | reason |", "|---|---|---|---|"]
        L += [f"| {n} | {tc(c['at'])} | {c['removed'][:160].replace('|', '/')} | {c['reason']} |"
              for n, c in enumerate(content, 1)]
    else:
        L.append("_None — only pauses were tightened._")
    L += ["", "## Final script (what the viewer hears)", ""]
    para, p_start = [], 0.0
    for k, s, e in words_out:
        if not para:
            p_start = s
        para.append(fixed_text(words, fixes, k))
        if len(para) >= 55 and re.search(r"[.?!]$", para[-1]):
            L += [f"`{tc(p_start)}` " + " ".join(para), ""]
            para = []
    if para:
        L += [f"`{tc(p_start)}` " + " ".join(para), ""]
    (wd / "review.md").write_text("\n".join(L))
    print(f"✓ {tc(dur)} → {tc(new_dur)} · {len(pauses)} pause trims · {len(content)} content cuts"
          f"{' · hook' if hook else ''} → {wd.relative_to(ROOT)}/review.md")


# ----------------------------------------------------------------- captions
def caption_chunks(words_out, words, fixes, vertical, punch=False, pop=False, limits=None):
    max_words, max_chars = limits or ((2, 14) if pop else (3, 18) if punch else (4, 24) if vertical else (7, 42))
    max_gap = 0.25 if pop else 0.45
    items = []  # Whisper splits Tagalog hyphenation ("Pag -open") — glue it back
    for k, s, e in words_out:
        t = fixed_text(words, fixes, k)
        if not t:
            continue
        if t.startswith("-") and items:
            items[-1] = (items[-1][0] + t, items[-1][1], e)
        else:
            items.append((t, s, e))
    chunks, cur = [], []
    for t, s, e in items:
        if cur and (len(cur) >= max_words or s - cur[-1][2] > max_gap
                    or len(" ".join(x[0] for x in cur) + " " + t) > max_chars
                    or re.search(r"[.?!,]$", cur[-1][0])):
            chunks.append(cur)
            cur = []
        cur.append((t, s, e))
    if cur:
        chunks.append(cur)
    timed = []
    for n, c in enumerate(chunks):
        start = c[0][1]
        end = c[-1][2] + 0.35
        if n + 1 < len(chunks):
            end = min(end, chunks[n + 1][0][1])
        end = max(end, start + 0.3)
        if pop and n + 1 < len(chunks):  # pops hard-cut when the next group starts
            end = min(end, chunks[n + 1][0][1])
        timed.append((start, end, c))
    return timed


def font_available(name):
    pat = name.lower().replace(" ", "")
    for d in ("~/Library/Fonts", "/Library/Fonts", "/System/Library/Fonts", "/System/Library/Fonts/Supplemental"):
        p = Path(d).expanduser()
        if p.exists() and any(pat in f.name.lower().replace(" ", "") for f in p.iterdir()):
            return True
    return False


def ass_color(hexrgb):
    h = hexrgb.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ass_time(t):
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def brandkit_ink(hex_):
    """Text colour that reads on a box of this colour (dark ink on light accents, white on dark ones)."""
    import brandkit
    return brandkit.ink_for(hex_)


def write_captions(path_ass, path_srt, edl, words, dec, W, H):
    vertical = H > W
    fixes = dec.get("fixes", {})
    kw = {norm(k) for k in dec.get("keywords", [])}
    style = dec.get("caption_style", STYLE.get("captions", {}).get("style", "classic"))
    # Studio styles built on pop's placement + size: highlight (karaoke line), box (colour box), outline (caps + stroke)
    hi, boxed, outl = style == "highlight", style == "box", style == "outline"
    lower, scr = style == "lower", style == "script"  # 2026: quiet lowercase · keyword in the script font
    pop = style in ("pop", "highlight", "box", "outline", "lower", "script")  # design system: 1–2 word pops, shadow only, no box (default)
    punch = pop or style == "punch"  # 1–3 words, centred, pop-in (inspiration-reel look)
    font = "Inter Tight ExtraBold" if punch else STYLE["fonts"]["captions"]
    look = dec.get("look")  # Studio look (tools/brandkit.py): caption font + accent colour
    if look:
        import brandkit
        font = brandkit.font_pair(dec)["caption"]
    black = brandkit.font_pair(dec)["caption_black"] if look else "Inter Tight Black"
    script_font = brandkit.font_pair(dec)["script"] if look else "Great Vibes"
    accent_hex = brandkit.accent(dec) if look else STYLE["colors"]["accent"]
    if not punch and not font_available(font):
        font = STYLE["fonts"]["captions_fallback"]
    fs = round(H * (dec.get("caption_size", STYLE.get("captions", {}).get("size_px_1920", 72)) / 1920 if pop else 0.042 if punch else 0.040 if vertical else 0.058))
    mv = round(H * (0.22 if vertical else 0.08))
    ml = round(W * 0.06)
    outline = max(2, round(fs * (0.05 if punch else 0.08)))
    if dec.get("_hlg"):
        import hdr
        accent, white = ass_color(hdr.hex_to_hlg(accent_hex)), ass_color(hdr.hex_to_hlg(STYLE["colors"]["text"]))
    else:
        accent, white = ass_color(accent_hex), ass_color(STYLE["colors"]["text"])
    timed = caption_chunks(edl["words_out"], words, fixes, vertical, punch, pop,
                           limits=(4, 24) if hi else (3, 18) if outl else (3, 20) if lower else None)
    ink_hex = "#1A0B04" if boxed and brandkit_ink(accent_hex) == "#1A0B04" else STYLE["colors"]["text"]
    if dec.get("_hlg"):
        import hdr
        ink = ass_color(hdr.hex_to_hlg(ink_hex))
    else:
        ink = ass_color(ink_hex)
    # while a graphic covers the frame, captions drop below it (or hide)
    windows = [(o["at"], o["at"] + o["dur"], o.get("caption", "low")) for o in dec.get("overlays", [])]

    zones = dec.get("caption_zones", [])  # [{"src_start", "src_end", "y"}] original seconds → caption top y (1920 px), e.g. a closer camera

    def src_of(t):  # edited time → original seconds (through the EDL segments)
        acc = 0.0
        for a0, b0 in (edl.get("hook_segs") or []) + edl["segments"]:  # cold open first, as rendered
            if t < acc + (b0 - a0):
                return a0 + (t - acc)
            acc += b0 - a0
        return edl["segments"][-1][1] if edl["segments"] else t

    def cap_y(t):
        st = src_of(t)
        z = next((z for z in zones if z["src_start"] <= st < z["src_end"]), None)
        return z["y"] if z else dec.get("caption_y", STYLE.get("captions", {}).get("top_y_1920", 1150))

    def placement(s):
        modes = [mode for a0, a1, mode in windows if a0 - 0.2 <= s < a1]  # a caption starting just before the graphic hides too
        return "hide" if "hide" in modes else next((m for m in modes if m != "normal"), "normal")
    L = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2",
         "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
         "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
         "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
         "MarginL, MarginR, MarginV, Encoding",
         f"Style: Cap,{font},{fs},{white},{white},&H00000000,&HA6000000,{0 if punch else -1},0,0,0,100,100,"
         f"{-1 if punch else 0},0,1,{outline},{3 if punch else 2},2,"
         f"{ml},{ml},{mv},1",
         f"Style: Box,{font},{fs},{ink},{ink},{accent},&H66000000,0,0,0,0,100,100,-1,0,3,{max(6, round(fs * .22))},0,2,"
         f"{ml},{ml},{mv},1", "", "[Events]",
         "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    srt = []
    for n, (s, e, c) in enumerate(timed, 1):
        parts = []
        for t, _, _ in c:
            t2 = t.replace("{", "(").replace("}", ")").replace("\\", "/")
            if outl:
                t2 = t2.upper()
            if boxed or hi:  # box: one colour block; highlight: colour moves word by word (below)
                parts.append(t2)
            elif lower:  # quiet lowercase: no keyword colour, no shouting
                parts.append(t2.lower())
            elif scr and norm(t) in kw:  # the keyword in the creator's handwritten font, bigger, in colour
                parts.append(f"{{\\fn{script_font}\\fs{round(fs * 1.7)}\\c{accent}&\\b0}}{t2}{{\\fn{font}\\fs{fs}\\c{white}&\\b1}}")
            elif norm(t) in kw and pop:  # design system: keyword turns orange (.pop .k), same size
                parts.append(f"{{\\c{accent}&}}{t2}{{\\c{white}&}}")
            elif norm(t) in kw and punch:  # inspiration look: keyword bigger, Black weight, orange
                parts.append(f"{{\\fn{black}\\fs{round(fs * 1.38)}\\c{accent}&}}{t2}"
                             f"{{\\fn{font}\\fs{fs}\\c{white}&}}")
            else:
                parts.append(f"{{\\c{accent}&}}{t2}{{\\c{white}&}}" if norm(t) in kw else t2)
        f = lambda t: ass_time(t).replace(".", ",") + "0"
        srt += [str(n), f"0{f(s)} --> 0{f(e)}", " ".join(x[0] for x in c), ""]
        pre = ""
        if punch:
            mode = placement(s)
            if mode == "hide":
                continue
            y = round(H * (0.74 if mode in ("low", "panel") else 0.18 if mode == "top" else 0.62))  # 0.74 = y 1420: inside the Reels/TikTok/Shorts safe zone
            pre = f"{{\\an5\\pos({W // 2},{y})\\fscx82\\fscy82\\t(0,90,\\fscx100\\fscy100)}}"
            if pop:  # talking head: top of the caption at y 1150 (≈60%), scale 0.84→1 + fade in 0.16 s
                an, y = (8, round(H * cap_y(s) / 1920)) if mode == "normal" else (5, y)
            if boxed:  # words on a solid accent box (BorderStyle 3), pops in
                L.append(f"Dialogue: 1,{ass_time(s)},{ass_time(e)},Box,,0,0,0,,"
                         f"{{\\an{an}\\pos({W // 2},{y})\\fad(120,0)\\fscx86\\fscy86\\t(0,140,\\fscx100\\fscy100)}}{' '.join(parts)}")
                continue
            if outl:  # all caps, thick black stroke, keyword in colour
                L.append(f"Dialogue: 1,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,"
                         f"{{\\an{an}\\pos({W // 2},{y})\\fad(120,0)\\fscx84\\fscy84\\t(0,140,\\fscx100\\fscy100)"
                         f"\\bord{max(4, round(fs * .11))}\\shad{max(2, round(fs * .05))}\\3c&H000000&\\4c&H000000&\\4a&H60&\\blur0.8}}{' '.join(parts)}")
                continue
            if hi:  # karaoke line: the whole line stays, the word being said lights up in the accent
                for j, (_, ws, _) in enumerate(c):
                    s1 = s if j == 0 else ws
                    e1 = c[j + 1][1] if j + 1 < len(c) else e
                    if e1 - s1 < 0.02:
                        continue
                    lit = " ".join(f"{{\\c{accent}&}}{p}{{\\c{white}&}}" if k == j else p for k, p in enumerate(parts))
                    fade = "\\fad(120,0)" if j == 0 else ""
                    L.append(f"Dialogue: 0,{ass_time(s1)},{ass_time(e1)},Cap,,0,0,0,,"
                             f"{{\\an{an}\\pos({W // 2},{y + round(fs * .08)}){fade}\\1a&HFF&\\bord{round(fs * .16)}\\shad0"
                             f"\\3c&H000000&\\3a&H90&\\blur{round(fs * .2)}}}{' '.join(parts)}")
                    L.append(f"Dialogue: 1,{ass_time(s1)},{ass_time(e1)},Cap,,0,0,0,,"
                             f"{{\\an{an}\\pos({W // 2},{y}){fade}\\bord{max(2, round(fs * .03))}\\shad0\\3c&H000000&\\3a&H30&\\blur2}}{lit}")
                continue
            if pop:
                pre = (f"{{\\an{an}\\pos({W // 2},{y})\\fad(160,0)\\fscx84\\fscy84\\t(0,160,\\fscx100\\fscy100)"
                       f"\\bord{max(2, round(fs * .03))}\\shad0\\3c&H000000&\\3a&H30&\\blur2}}")
                # soft drop shadow underneath (design system --shadow: no boxes or strokes behind captions)
                L.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,"
                         f"{{\\an{an}\\pos({W // 2},{y + round(fs * .08)})\\fad(160,0)\\fscx84\\fscy84"
                         f"\\t(0,160,\\fscx100\\fscy100)\\1a&HFF&\\bord{round(fs * .16)}\\shad0"
                         f"\\3c&H000000&\\3a&H90&\\blur{round(fs * .2)}}}{' '.join(parts)}")
        L.append(f"Dialogue: 1,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{pre}{' '.join(parts)}")
    Path(path_ass).write_text("\n".join(L) + "\n")
    if path_srt:
        Path(path_srt).write_text("\n".join(srt))


# ----------------------------------------------------------------- render
def room_tone(wd):
    import numpy as np
    """(start, end) of the longest clean room-tone stretch (no voice, no gate silence), 0.6–3 s, or None."""
    db = np.load(wd / "energy.npy")
    live = db[db > -90]
    if not len(live):
        return None
    floor = np.percentile(live, 10)
    ok = (db > floor - 5) & (db < floor + 5)
    best, run, start = (0, 0), 0, 0
    for f, v in enumerate(ok):
        if v:
            if not run:
                start = f
            run += 1
            if run > best[1] - best[0]:
                best = (start, f + 1)
        else:
            run = 0
    a, b = best
    if b - a < 60:
        return None
    a, b = a + 5, min(b - 5, a + 5 + 300)  # stay off the edges
    return a / 100, b / 100


def shrink_p(t, a0, a1, ti, to):
    """Shrink card progress: 0 = full frame, 1 = in the card. Cubic ease-out in, cubic ease-in-out back (= shrink_expr)."""
    u, v = min(1.0, max(0.0, (t - a0) / ti)), min(1.0, max(0.0, (a1 - t) / to))
    return min(1 - (1 - u) ** 3, 4 * v ** 3 if v < 0.5 else 1 - (2 - 2 * v) ** 3 / 2)


def shrink_expr(t, a0, a1, ti, to):
    u, v = f"clip(({t}-{a0:.4f})/{ti},0,1)", f"clip(({a1:.4f}-{t})/{to},0,1)"
    return f"min(1-pow(1-{u},3),if(lt({v},0.5),4*pow({v},3),1-pow(2-2*{v},3)/2))"


def shrink_mask(path, o, ow, oh, fps, fps_r):
    """Rounded window of the footage for a shrink card (footage coordinates, one gray frame per output frame):
    the whole frame at the start/end, the card's window in between. numpy → FFV1 (an ffmpeg geq mask ran at 13 fps)."""
    import numpy as np
    c, a0 = o["card"], o["at"]
    a1 = a0 + o["dur"]
    fx, fy, s1 = ow / 1080, oh / 1920, c["s"]
    src_x = (1080 - c["w"] / s1) / 2
    wl, wr = src_x * fx, (src_x + c["w"] / s1) * fx
    wt, wb = c["src_y"] * fy, (c["src_y"] + c["h"] / s1) * fy
    xs = np.arange(ow, dtype=np.float32)[None, :] + .5
    ys = np.arange(oh, dtype=np.float32)[:, None] + .5
    p3 = subprocess.Popen([binpath("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{ow}x{oh}",
                           "-r", fps_r, "-i", "-", "-c:v", "ffv1", str(path)], stdin=subprocess.PIPE)
    done = {}  # the hold (p = 1) is one frame, written again and again
    for i in range(int(math.ceil(o["dur"] * fps)) + 2):
        p = round(shrink_p(a0 + i / fps, a0, a1, c["tin"], c["tout"]), 4)
        if p not in done:
            q = 1 - p  # start/end: edges 2 px outside the frame, so the full frame is fully opaque
            L, R, T, B = -2 * q + p * wl, (ow + 2) * q + p * wr, -2 * q + p * wt, (oh + 2) * q + p * wb
            rad = max(1.0, p * c["r"] / s1 * fx)
            dx = np.maximum(np.maximum(L + rad - xs, xs - (R - rad)), 0)
            dy = np.maximum(np.maximum(T + rad - ys, ys - (B - rad)), 0)
            frame = (np.clip(rad - np.sqrt(dx * dx + dy * dy) + .5, 0, 1) * 255 + .5).astype(np.uint8).tobytes()
            if p == 1.0:
                done[p] = frame
        p3.stdin.write(done.get(p, frame))
    p3.stdin.close()
    if p3.wait():
        die(f"shrink mask failed for {o['id']}")


def behind_pass(out, items, ow, oh, fps_r, venc, wd, cube=None):
    """Text BEHIND the speaker: Apple Vision cuts the person out of the rendered frames (tools/bin/personmask),
    the text layer goes over the frame and the person goes back on top of it."""
    import subprocess as sp
    ffmpeg, pm = binpath("ffmpeg"), finder("personmask")
    if pm:
        print(f"• text-behind: cutting the speaker out for {len(items)} moment(s)…", flush=True)
    else:
        print("– text-behind: no person cut-out installed (tools/setup) — the text goes over the speaker instead", flush=True)
    hlg = cube is not None  # HLG source: composite in RGB on the untouched signal, text layer through the SDR→HLG LUT
    # Each moment reads its own seeked slice of the render (bug fix: one split of the whole video made ffmpeg queue every
    # frame before a late moment — a CTA at 3:17 in a 1080p final = ~37 GB of raw frames → killed by the OS).
    rgb = 'scale=in_color_matrix=bt2020:in_range=tv,format=gbrp,' if hlg else ''
    inputs, fl, n_in = ["-i", out], [f"[0:v]{rgb}null[base]"], 1
    cur = "[base]"
    for k, o in enumerate(items):
        a0, a1 = o["at"], o["at"] + o["dur"]
        mk = wd / f"mask_{o['id']}.mkv"
        if not pm:  # an empty mask: nobody is put back on top of the text
            sp.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={ow}x{oh}:r={fps_r}", "-t", f"{a1 - a0:.4f}",
                    "-pix_fmt", "gray", "-c:v", "ffv1", str(mk)], check=True)
        else:
            p1 = sp.Popen([ffmpeg, "-v", "error", "-ss", f"{a0:.4f}", "-t", f"{a1 - a0:.4f}", "-i", str(out),
                           "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=sp.PIPE)
            p2 = sp.Popen([*pm, str(ow), str(oh)], stdin=p1.stdout, stdout=sp.PIPE)
            p3 = sp.Popen([ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{ow}x{oh}", "-r", fps_r,
                           "-i", "-", "-c:v", "ffv1", str(mk)], stdin=p2.stdout)
            p1.stdout.close(), p2.stdout.close()
            if p3.wait() or p2.wait() or p1.wait():
                die(f"person mask failed for {o['id']}")
        op = Path(o["file"]) if Path(o["file"]).is_absolute() else ROOT / o["file"]
        inputs += ["-ss", f"{a0:.4f}", "-t", f"{a1 - a0:.4f}", "-i", out, "-i", op, "-i", mk]
        fi, ti, mi = n_in, n_in + 1, n_in + 2
        n_in += 3
        fl.append(f"[{fi}:v]{rgb}setpts=PTS-STARTPTS,format={'gbrp' if hlg else 'yuv420p'}[f{k}]")
        fl.append(f"[{mi}:v]format=gray,tmix=frames=3:weights='1 2 1',gblur=sigma={max(1, round(oh / 1100))}[m{k}]")
        fl.append(f"[f{k}][m{k}]alphamerge,setpts=PTS+{a0:.4f}/TB[p{k}]")
        fl.append(f"[{ti}:v]scale={ow}:{oh},{"lut3d=file='" + fpath(cube) + "':interp=tetrahedral,format=gbrap" if hlg else 'format=yuva420p'},setpts=PTS-STARTPTS+{a0:.4f}/TB[t{k}]")
        fl.append(f"{cur}[t{k}]overlay=eof_action=pass:format=auto[x{k}]")
        fl.append(f"[x{k}][p{k}]overlay=eof_action=pass:format=auto[y{k}]")
        cur = f"[y{k}]"
    fl.append(f"{cur}{'scale=out_color_matrix=bt2020:out_range=tv,' if hlg else ''}format=yuv420p[vout]")
    script = wd / "filter_behind.txt"
    script.write_text(";\n".join(fl))
    tmp = out.with_name(out.stem + ".bt.mp4")
    ver = re.search(r"version (\d+)", sh([ffmpeg, "-version"], capture=True))
    fc = ["-/filter_complex", script] if (not ver or int(ver.group(1)) >= 7) else ["-filter_complex_script", script]
    sh([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *inputs, *fc, "-map", "[vout]",
        "-map", "0:a", *venc, "-r", fps_r, "-pix_fmt", "yuv420p",
        *(["-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc", "-color_range", "tv"] if hlg
          else ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]),  # SDR: tag it, players must not guess
        "-c:a", "copy", "-movflags", "+faststart", tmp])
    tmp.replace(out)


def cmd_render(a):
    src, wd, meta = ctx(a.video)
    edl = jload(wd / "edl.json") or die("run plan first")
    words = jload(wd / "transcript.json")["words"]
    dec = jload(wd / "decisions.json", {})
    ffmpeg = binpath("ffmpeg")
    W, H, fps = meta["w"], meta["h"], meta["fps"]
    final = a.final
    if final:
        ow, oh = W, H
        fh = dec.get("final_height")  # e.g. 1920: deliver 1080×1920 from a 4K phone source
        if fh and max(W, H) > fh:
            ow, oh = (round(W * fh / H / 2) * 2, fh) if H >= W else (fh, round(H * fh / W / 2) * 2)
    elif W >= H:
        ow, oh = round(W * 720 / H / 2) * 2, 720
    else:
        ow, oh = 720, round(H * 720 / W / 2) * 2

    inputs, fl, pads = ["-i", src], [], []
    n_in = 1
    z = float(dec.get("punch_in") or 0)

    def segment(vin, ain, s, e, zoom):
        k = len(pads)
        d = e - s
        crop = (f",crop=iw/{zoom}:ih/{zoom}:(iw-iw/{zoom})/2:(ih-ih/{zoom})*0.4,scale={W}:{H}"
                if zoom > 1 else "")
        fl.append(f"{vin}trim=start={s:.4f}:end={e:.4f},setpts=PTS-STARTPTS{crop},setsar=1[v{k}]")
        fl.append(f"{ain}atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS,"
                  f"afade=t=in:st=0:d={FADE},afade=t=out:st={max(0, d - FADE):.4f}:d={FADE}[a{k}]")
        pads.append(f"[v{k}][a{k}]")

    for hs, he in edl.get("hook_segs") or ([edl["hook"]] if edl.get("hook") else []):  # cold open first
        inputs += ["-ss", f"{hs:.4f}", "-t", f"{he - hs:.4f}", "-i", src]
        segment(f"[{n_in}:v]", f"[{n_in}:a]", 0, he - hs, z if z > 1 else 0)
        n_in += 1
    zoom_on, prev_e = False, None
    for s, e in edl["segments"]:
        if prev_e is not None and s - prev_e > dec.get("punch_flip_gap", 0.6):  # a real cut (content/pause) flips the punch-in;
            zoom_on = not zoom_on                     # closed gate holes keep the same framing (no flicker)
        prev_e = e
        segment("[0:v]", "[0:a]", s, e, z if (z > 1 and zoom_on) else 0)
    fl.append("".join(pads) + f"concat=n={len(pads)}:v=1:a=1[vc][ac]")

    post = [] if (ow, oh) == (W, H) else [f"scale={ow}:{oh}"]
    if dec.get("grade", STYLE["grade"].get("enabled", True)):  # design system: natural footage by default
        g = STYLE["grade"]
        post.append(f"eq=brightness={g['brightness']}:contrast={g['contrast']}:saturation={g['saturation']},"
                    f"unsharp=5:5:{g['sharpen']}")
    hz = dec.get("hook_zoom")
    if hz:  # zoompan on a 2× canvas (no 1-px jitter), z(t): 1.12→1 pop-out, then ease-in push 1→1.13 during the riser
        a0, a1 = hz.get("pop_out", [0, 0.6]); b0, b1 = hz.get("push_in", [0, 0])
        z = (f"if(lt(it,{a1}),1.12-0.12*(1-pow(1-(it-{a0})/{a1 - a0},3)),"
             f"if(between(it,{b0},{b1}),1+0.08*pow((it-{b0})/{max(0.1, b1 - b0)},2),1))")
        post += [f"scale={ow * 2}:{oh * 2}", f"zoompan=z='{z}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={ow * 2}x{oh * 2}:fps={edl['fps_r']}",
                 f"scale={ow}:{oh}"]
    hlg = dec.get("hdr", "auto") is not False and probe(src).get("trc") == "arib-std-b67"
    if hlg:  # iPhone HDR: composite in RGB on the untouched HLG signal (Lloyd: "normal yung kulay", no grading)
        import hdr
        cube = hdr.write_cube(ROOT / "assets" / "sdr_to_hlg.cube")
        dec["_hlg"] = True
        post.append("scale=in_color_matrix=bt2020:in_range=tv,format=gbrp")
    LOOKS = {"bw": "0.30:0.59:0.11:0:0.30:0.59:0.11:0:0.30:0.59:0.11",          # tutorial demo: "baguhin yung filter"
             "warm": "1.12:0.04:0:0:0.02:1.0:0:0:0:0:0.82",                     # "adjustment ng kulay"
             "cool": "0.86:0:0:0:0:1.0:0.04:0:0:0.06:1.14",                     # "tono"
             "vintage": "0.39:0.77:0.19:0:0.35:0.69:0.17:0:0.27:0.53:0.13"}
    if dec.get("looks"):
        if not hlg:
            post.append("format=gbrp")
        for lk in dec["looks"]:  # colorchannelmixer works on RGB; timeline-enabled on the edited clock
            post.append(f"colorchannelmixer={LOOKS.get(lk['look'], lk['look'])}:enable='between(t,{lk['at']:.3f},{lk['at'] + lk['dur']:.3f})'")
    fl.append(f"[vc]{','.join(post) or 'null'}[vp]")
    cur = "[vp]"
    # motion graphics (HyperFrames renders, alpha MOV/WebM) placed on the edited timeline
    ovs = dec.get("overlays", [])
    # v4 glass: consecutive glass scenes share ONE frosted-footage span, so the background never flashes sharp
    spans = []
    for o in sorted((o for o in ovs if o.get("kind") == "glass"), key=lambda o: o["at"]):
        a0, a1 = o["at"], o["at"] + o["dur"]
        if spans and a0 - spans[-1][1] < 0.5:
            spans[-1][1] = max(spans[-1][1], a1)
        else:
            spans.append([a0, a1])
    GF = 0.35  # face ↔ glass dissolve
    # Lloyd 2026-10-20: "make it natural kung ano lang yung nasa camera" — the old warm/desaturated grade read as a filter
    # on his face. Default = neutral: blur + an even dim (hue and saturation untouched). "glass_grade": "warm" = old look.
    GLASS_GRADE = ("eq=brightness=-0.07:saturation=0.78:contrast=0.94,colorbalance=rs=.05:bs=-.07:rm=.05:bm=-.05"
                   if dec.get("glass_grade") == "warm" else "colorchannelmixer=rr=0.8:gg=0.8:bb=0.8")
    for k, (a0, a1) in enumerate(spans):
        q = 4  # blur at quarter size: same look, much faster
        fl.append(f"{cur}split[gs{k}][gb{k}]")
        fl.append(f"[gb{k}]trim=start={a0:.4f}:end={a1:.4f},scale={ow // q // 2 * 2}:{oh // q // 2 * 2},"
                  f"gblur=sigma={max(4, round(oh / 34 / q))},scale={ow}:{oh},"
                  f"{GLASS_GRADE},"
                  f"{"format=gbrap" if hlg else "format=yuva420p"},fade=t=in:st={a0:.4f}:d={GF}:alpha=1,fade=t=out:st={a1 - GF:.4f}:d={GF}:alpha=1[gl{k}]")
        fl.append(f"[gs{k}][gl{k}]overlay=eof_action=pass:format=auto[gd{k}]")
        cur = f"[gd{k}]"
    glass_sorted = sorted((o for o in ovs if o.get("kind") == "glass"), key=lambda o: o["at"])
    # v5 newsroom: consecutive news pages form a span; his face rides along in a round cam bubble
    news_sorted = sorted((o for o in ovs if o.get("kind") == "news"), key=lambda o: o["at"])
    nspans = []
    for o in news_sorted:
        a0, a1 = o["at"], o["at"] + o["dur"]
        if nspans and a0 - nspans[-1][1] < 0.5:
            nspans[-1][1], nspans[-1][2] = max(nspans[-1][1], a1), o.get("wout", True)
        else:
            nspans.append([a0, a1, o.get("wout", True)])
    if nspans:
        fl.append(f"{cur}split={len(nspans) + 1}[vb]" + "".join(f"[cs{k}]" for k in range(len(nspans))))
        cur = "[vb]"
    for k, o in enumerate(ovs):
        if o.get("kind") == "behind":
            continue  # composited after the main render, behind the speaker (behind_pass)
        op = Path(o["file"]) if Path(o["file"]).is_absolute() else ROOT / o["file"]
        if not op.exists():
            die(f"overlay missing: {op}")
        inputs += ["-i", op]
        if o.get("kind") == "news":  # the page wipes itself in/out (alpha); chained pages hold until the next wipe passes
            a1 = o["at"] + o["dur"]
            nxt = next((g["at"] for g in news_sorted if g["at"] >= a1 - 0.01 and g is not o), None)
            pad = (f",tpad=stop_mode=clone:stop_duration={nxt - a1 + 0.6:.4f}"
                   if not o.get("wout", True) and nxt is not None and nxt - a1 < 0.5 else "")
            fl.append(f"[{n_in}:v]scale={ow}:{oh},{"lut3d=file='" + fpath(cube) + "':interp=tetrahedral,format=gbrap" if hlg else "format=yuva420p"}{pad},setpts=PTS-STARTPTS+{o['at']:.4f}/TB[g{k}]")
            fl.append(f"{cur}[g{k}]overlay=eof_action=pass:format=auto[o{k}]")
            cur = f"[o{k}]"
            n_in += 1
            continue
        if o.get("kind") == "shrink":  # the footage itself shrinks into a rounded card (face whole + sharp) and grows back
            c, a0 = o["card"], o["at"]  # card geometry from mograph.shrink_geom (1080×1920 px)
            a1 = a0 + o["dur"]
            fx, fy, s1, to = ow / 1080, oh / 1920, c["s"], c["tout"]
            src_x = (1080 - c["w"] / s1) / 2
            mk = wd / f"shrink_{o['id']}_{oh}.mkv"
            shrink_mask(mk, o, ow, oh, fps, edl["fps_r"])
            inputs += ["-i", mk]
            P = shrink_expr("t", a0, a1, c["tin"], to)
            S = f"(1-{1 - s1:.4f}*{P})"
            fa = "format=gbrap" if hlg else "format=yuva420p"
            fl.append(f"{cur}split=3[ka{k}][kb{k}][kc{k}]")
            # 1 frosted footage behind (glass look), gone again while the card grows back
            fl.append(f"[kb{k}]trim=start={a0:.4f}:end={a1:.4f},scale={ow // 4 // 2 * 2}:{oh // 4 // 2 * 2},"
                      f"gblur=sigma={max(4, round(oh / 34 / 4))},scale={ow}:{oh},"
                      f"eq=brightness=-0.07:saturation=0.78:contrast=0.94,colorbalance=rs=.05:bs=-.07:rm=.05:bm=-.05,{fa},"
                      f"fade=t=in:st={a0:.4f}:d=0.25:alpha=1,fade=t=out:st={a1 - to:.4f}:d={to - 0.05:.2f}:alpha=1[kl{k}]")
            fl.append(f"[ka{k}][kl{k}]overlay=eof_action=pass:format=auto[kd{k}]")
            # 2 the page (dim, ring, kicker, title, chips — never inside the card)
            fl.append(f"[{n_in}:v]scale={ow}:{oh},{"lut3d=file='" + fpath(cube) + "':interp=tetrahedral,format=gbrap" if hlg else "format=yuva420p"},setpts=PTS-STARTPTS+{a0:.4f}/TB[g{k}]")
            fl.append(f"[kd{k}][g{k}]overlay=eof_action=pass:format=auto[ke{k}]")
            # 3 the untouched footage on top: rounded window (mask), scaled + placed per frame
            fl.append(f"[{n_in + 1}:v]format=gray,setpts=PTS-STARTPTS+{a0:.4f}/TB[km{k}]")
            fl.append(f"[kc{k}]trim=start={a0:.4f}:end={a1:.4f},{fa}[kf{k}]")
            fl.append(f"[kf{k}][km{k}]alphamerge,scale=w='2*round({ow}*{S}/2)':h='2*round({oh}*{S}/2)':eval=frame[ks{k}]")
            fl.append(f"[ke{k}][ks{k}]overlay=x='{(c['x'] - s1 * src_x) * fx:.3f}*{P}':y='{(c['y'] - s1 * c['src_y']) * fy:.3f}*{P}'"
                      f":eval=frame:eof_action=pass:format=auto[o{k}]")
            cur = f"[o{k}]"
            n_in += 2
            continue
        if o.get("kind") == "glass":
            a0, a1 = o["at"], o["at"] + o["dur"]
            first = any(abs(a0 - s0) < 0.05 for s0, _ in spans)
            last = any(abs(a1 - s1) < 0.05 for _, s1 in spans)
            nxt = next((g["at"] for g in glass_sorted if g["at"] >= a1 - 0.01 and g is not o), None)
            pad = (f",tpad=stop_mode=clone:stop_duration={nxt - a1 + 1 / fps:.4f}" if not last and nxt is not None else "")
            fade = ((f",fade=t=in:st=0:d={GF - .05}:alpha=1" if first else "") +
                    (f",fade=t=out:st={max(0, o['dur'] - GF + .05):.4f}:d={GF - .05}:alpha=1" if last else ""))
            fl.append(f"[{n_in}:v]scale={ow}:{oh},{"lut3d=file='" + fpath(cube) + "':interp=tetrahedral,format=gbrap" if hlg else "format=yuva420p"}{pad}{fade},setpts=PTS-STARTPTS+{a0:.4f}/TB[g{k}]")
            fl.append(f"{cur}[g{k}]overlay=eof_action=pass:format=auto[o{k}]")
            cur = f"[o{k}]"
            n_in += 1
            continue
        full = o.get("kind", "full" if str(o["file"]).endswith(".mp4") else "") == "full"
        if o.get("caption") == "panel" or full:  # blur the footage behind a centred card / under a scene dissolve
            a0, a1 = o["at"], o["at"] + o["dur"]
            fl.append(f"{cur}split[bs{k}][bb{k}]")
            fl.append(f"[bb{k}]trim=start={a0:.4f}:end={a1:.4f},gblur=sigma={round(oh / 48)},"
                      f"eq=brightness=-0.06,{"format=gbrap" if hlg else "format=yuva420p"},"
                      f"fade=t=in:st={a0:.4f}:d=0.2:alpha=1,fade=t=out:st={a1 - 0.2:.4f}:d=0.2:alpha=1[bl{k}]")
            fl.append(f"[bs{k}][bl{k}]overlay=eof_action=pass:format=auto[bd{k}]")
            cur = f"[bd{k}]"
        fade = (f",fade=t=in:st=0:d=0.22:alpha=1,fade=t=out:st={max(0, o['dur'] - 0.2):.4f}:d=0.2:alpha=1"
                if full else "")  # design system: face → blurred face → scene, and back
        fl.append(f"[{n_in}:v]scale={ow}:{oh},{"lut3d=file='" + fpath(cube) + "':interp=tetrahedral,format=gbrap" if hlg else "format=yuva420p"}{fade},setpts=PTS-STARTPTS+{o['at']:.4f}/TB[g{k}]")
        fl.append(f"{cur}[g{k}]overlay=eof_action=pass:format=auto[o{k}]")
        cur = f"[o{k}]"
        n_in += 1
    if nspans and not dec.get("cam_bubble", False):  # Lloyd: no face bubble on the pages → just release the splits
        for k in range(len(nspans)):
            fl.append(f"[cs{k}]nullsink")
        nspans = []
    if nspans:  # cam bubble inside the page's orange ring (ring drawn by mograph at left 64, top 1100, Ø250, border 7)
        cam = dec.get("cam", {})
        sc_ = ow / 1080
        D = round(236 * sc_) // 2 * 2  # ring Ø250 at left 64, top 1100 (safe zone: clear of the right-hand buttons)
        bx, by = round(71 * sc_), round(1107 * sc_)
        size = cam.get("size", 760) * sc_
        cx, cy = cam.get("cx", 540) * sc_, cam.get("cy", 780) * sc_
        x0, y0 = max(0, min(ow - size, cx - size / 2)), max(0, min(oh - size, cy - size / 2))
        for k, (a0, a1, wout) in enumerate(nspans):
            t0 = round((a0 + 0.42) * fps) / fps
            t1 = a1 - (0.32 if wout else 0.0)
            if t1 - t0 < 0.6:
                fl.append(f"[cs{k}]nullsink")
                continue
            fl.append(f"[cs{k}]trim=start={t0:.4f}:end={t1:.4f},crop={size:.0f}:{size:.0f}:{x0:.0f}:{y0:.0f},scale={D}:{D},{"format=gbrap" if hlg else "format=yuva420p"}[cf{k}]")
            fl.append(f"color=c=black:s={D}x{D}:r={edl['fps_r']}:d={t1 - t0:.4f},format=gray,"
                      f"geq=lum='255*lte(hypot(X-{(D - 1) / 2},Y-{(D - 1) / 2}),{D / 2 - 1.5})',gblur=sigma=1,setpts=PTS+{t0:.4f}/TB[cm{k}]")
            fl.append(f"[cf{k}][cm{k}]alphamerge,fade=t=in:st={t0:.4f}:d=0.2:alpha=1,fade=t=out:st={max(t0, t1 - 0.2):.4f}:d=0.2:alpha=1[cb{k}]")
            fl.append(f"{cur}[cb{k}]overlay={bx}:{by}:eof_action=pass:format=auto[cq{k}]")
            cur = f"[cq{k}]"
    if dec.get("progress_bar"):
        # inspiration: x 64→1016, y 66, 6 px, warm grey track, orange fill
        m, hb = round(ow * 64 / 1080), max(3, round(oh * 6 / 1920))
        y, bw = round(oh * 63 / 1920), ow - 2 * m
        fl.append(f"{cur}drawbox=x={m}:y={y}:w={bw}:h={hb}:color=0x8C6A55@0.55:t=fill,"
                  f"drawbox=x={m}:y={y}:w='max(1,{bw}*t/{edl['new_dur']:.3f})':h={hb}:"
                  f"color=0x{(__import__('brandkit').accent(dec) if dec.get('look') else STYLE['colors']['accent']).lstrip('#')}@1:t=fill[pb]")
        cur = "[pb]"
    logo = dec.get("logo") or (str(ROOT / "assets" / "logo.png") if (ROOT / "assets" / "logo.png").exists() else None)
    if logo:
        lp = Path(logo) if Path(logo).is_absolute() else ROOT / logo
        inputs += ["-i", lp]
        lw = round(ow * STYLE["logo"]["width_pct"] / 100)
        m = round(min(ow, oh) * 0.04)
        fl.append(f"[{n_in}:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa={STYLE['logo']['opacity']}[lg]")
        x = m if STYLE["logo"]["position"].endswith("left") else f"W-w-{m}"
        fl.append(f"{cur}[lg]overlay={x}:{m}[vl]")
        cur = "[vl]"
        n_in += 1
    stem = src.stem
    OUT.mkdir(exist_ok=True)
    if dec.get("captions", True):
        ass = wd / "captions.ass"
        write_captions(ass, OUT / f"{stem}.srt" if final else None, edl, words, dec, W, H)
        fl.append(f"{cur}ass='{fpath(ass)}':fontsdir='{fpath(ROOT / 'assets' / 'fonts')}'[vs]")
        cur = "[vs]"
    fl.append(f"{cur}{'scale=out_color_matrix=bt2020:out_range=tv,' if hlg else ''}format=yuv420p[vout]")
    acur = "[ac]"
    rt = room_tone(wd) if dec.get("room_tone", True) else None
    if rt:  # fill the phone's noise-gate holes (digital silence) with the room's own tone → even background
        t0, t1 = rt
        inputs += ["-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", src]
        fl.append(f"[{n_in}:a]aformat=sample_rates=48000:channel_layouts=mono,asplit[rt1][rt2];[rt2]areverse[rt2r];"
                  f"[rt1][rt2r]concat=n=2:v=0:a=1,aloop=loop=-1:size={int((t1 - t0) * 2 * 48000)},"
                  f"atrim=0:{edl['new_dur'] + 1:.3f},asetpts=N/SR/TB[rtb]")
        fl.append(f"[ac]aformat=sample_rates=48000[acf];[acf][rtb]amix=inputs=2:duration=first:normalize=0[acm]")
        acur = "[acm]"
        n_in += 1
    sfx = dec.get("sfx_track")
    if sfx and (ROOT / sfx).exists() and dec.get("sfx", True):  # tools/sfx.py: sound design on the edited timeline
        inputs += ["-i", str(ROOT / sfx)]
        fl.append(f"[{n_in}:a]aformat=sample_rates=48000:channel_layouts=mono,volume={dec.get('sfx_level', 1.0)}[sfx]")
        fl.append(f"{acur}aformat=sample_rates=48000:channel_layouts=mono[vox];[vox][sfx]amix=inputs=2:duration=first:normalize=0[acx]")
        acur = "[acx]"
        n_in += 1
    fl.append(f"{acur}highpass=f=70,loudnorm=I={STYLE['audio']['lufs']}:TP=-1.5:LRA=11,aresample=48000[aout]")

    script = wd / "filter.txt"
    script.write_text(";\n".join(fl))
    ver = re.search(r"version (\d+)", sh([ffmpeg, "-version"], capture=True))
    fc = ["-/filter_complex", script] if (not ver or int(ver.group(1)) >= 7) else ["-filter_complex_script", script]
    vt = "h264_videotoolbox" in sh([ffmpeg, "-hide_banner", "-encoders"], capture=True)
    if final:
        br = max(6000, min(24000, int(ow * oh * fps * 0.16 / 1000)))
        venc = (["-c:v", "h264_videotoolbox", "-b:v", f"{br}k", "-profile:v", "high"] if vt
                else ["-c:v", "libx264", "-preset", "medium", "-crf", "18"])
        out = OUT / f"{stem}_FINAL.mp4"
    else:
        venc = (["-c:v", "h264_videotoolbox", "-b:v", "3500k"] if vt
                else ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "27"])
        n = 1
        while (OUT / f"{stem}_preview_v{n}.mp4").exists():
            n += 1
        out = OUT / f"{stem}_preview_v{n}.mp4"
    print(f"• rendering {'FINAL' if final else 'preview'} {ow}x{oh}, {len(pads)} segments, "
          f"{tc(edl['new_dur'])} → {out.relative_to(ROOT)}", flush=True)
    sh([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-stats", *inputs, *fc,
        "-map", "[vout]", "-map", "[aout]", *venc, "-r", edl["fps_r"], "-pix_fmt", "yuv420p",
        *(["-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc", "-color_range", "tv"] if hlg
          else ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]),  # SDR: tag it, players must not guess
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    bts = [o for o in dec.get("overlays", []) if o.get("kind") == "behind"]
    if bts:
        behind_pass(out, bts, ow, oh, edl["fps_r"], venc, wd, cube if hlg else None)
    jsave(wd / "last_render.json", dict(path=str(out), final=final))
    print(f"✓ {out.relative_to(ROOT)}" + (f"  +  output/{stem}.srt" if final and dec.get("captions", True) else ""))


# ----------------------------------------------------------------- verify
def cmd_verify(a):
    src, wd, meta = ctx(a.video)
    edl = jload(wd / "edl.json") or die("run plan first")
    tr = jload(wd / "transcript.json")
    words = tr["words"]
    path = Path(a.file) if a.file else Path((jload(wd / "last_render.json") or die("render first"))["path"])
    wav = wd / "verify.wav"
    extract_wav(path, wav)
    print(f"• re-listening to {path.name}…", flush=True)
    got, _ = whisper_words(wav, tr.get("language"))
    exp = [(norm(words[k]["w"]), k, s) for k, s, e in edl["words_out"]]
    exp = [x for x in exp if x[0]]
    B = [x for x in (norm(g[0]) for g in got) if x]
    sm = difflib.SequenceMatcher(None, [x[0] for x in exp], B, autojunk=False)
    ratio = sum(b.size for b in sm.get_matching_blocks()) / max(1, len(exp))
    cut_at = [c["at"] for c in edl["cuts"]]
    splice, noise = [], 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "delete" or (tag == "replace" and i2 - i1 > j2 - j1):
            for w, k, t in exp[i1:i2]:
                j = bisect.bisect_left(cut_at, t)
                near = [c for c in (j - 1, j) if 0 <= c < len(cut_at) and abs(cut_at[c] - t) < 0.8]
                if near:
                    c = edl["cuts"][min(near, key=lambda c: abs(cut_at[c] - t))]
                    splice.append(dict(word=words[k]["w"], i=k, at=t, cut=c,
                                       side="after" if t < c["at"] else "before"))
                else:
                    noise += 1
    ov = jload(wd / "pad_overrides.json", {})
    L = [f"# Verify — {path.name}", "", f"Word match: **{ratio:.1%}** · splice suspects: **{len(splice)}** · "
         f"other transcription differences: {noise}", ""]
    for s in splice:
        key = f"after:{s['cut']['after']}" if s["side"] == "after" else f"before:{s['cut']['before']}"
        L.append(f"- `{tc(s['at'])}` “{s['word']}” (#{s['i']}) missing near cut at {tc(s['cut']['at'])} → widen {key}")
        if a.apply:
            ov[key] = round(min(0.5, ov.get(key, 0) + 0.12), 3)
    (wd / "verify.md").write_text("\n".join(L) + "\n")
    if a.apply and splice:
        jsave(wd / "pad_overrides.json", ov)
    print(f"✓ match {ratio:.1%} · {len(splice)} splice suspects"
          + (" → padding widened, re-run plan + render" if a.apply and splice else "")
          + f" → {wd.relative_to(ROOT)}/verify.md")


# ----------------------------------------------------------------- locate
def cmd_locate(a):
    src, wd, meta = ctx(a.video)
    words = jload(wd / "transcript.json")["words"]
    edl = jload(wd / "edl.json", {})
    out_of = {}
    for k, s, e in edl.get("words_out", []):
        out_of.setdefault(k, s)
    if a.text:
        q = [norm(x) for x in a.text.split() if norm(x)]
        seq = [norm(w["w"]) for w in words]
        for i in range(len(seq) - len(q) + 1):
            if seq[i:i + len(q)] == q:
                o = out_of.get(i)
                print(f"#{i}–#{i + len(q) - 1}  orig {tc(words[i]['s'])}  edited "
                      f"{tc(o) if o is not None else '(removed)'}  …"
                      + " ".join(w["w"] for w in words[max(0, i - 6): i + len(q) + 6]) + "…")
        return
    t = parse_tc(a.at)
    rows = [(k, s) for k, s, e in edl.get("words_out", []) if abs(s - t) <= a.window]
    line = []
    for k, s in rows:
        if not line:
            line_t = s
        line.append(f"#{k}·{words[k]['w']}")
        if len(line) == 10:
            print(f"{tc(line_t)}  " + " ".join(line))
            line = []
    if line:
        print(f"{tc(line_t)}  " + " ".join(line))


def cmd_studio(a):
    """Start the Studio (tools/editor/server.py) and open it in the browser."""
    if not a.no_open:
        import threading
        import webbrowser
        threading.Timer(1.5, webbrowser.open, [f"http://localhost:{os.environ.get('VEDIT_PORT', 8765)}"]).start()
    sys.exit(subprocess.call([sys.executable, "-X", "utf8", str(ROOT / "tools" / "editor" / "server.py")]))


# ----------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser(prog="vedit", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("doctor").set_defaults(fn=cmd_doctor)
    p = sp.add_parser("studio", help="start the Studio → http://localhost:8765")
    p.add_argument("--no-open", action="store_true", help="don't open the browser")
    p.set_defaults(fn=cmd_studio)
    p = sp.add_parser("transcribe")
    p.add_argument("video")
    p.add_argument("--language", default=None, help="e.g. tl or en; default auto-detect")
    p.add_argument("--no-fill", action="store_true", help="skip re-listening to long gaps")
    p.add_argument("--fill-only", action="store_true", help="only re-listen to gaps of the existing transcript")
    p.set_defaults(fn=cmd_transcribe)
    p = sp.add_parser("plan")
    p.add_argument("video")
    p.add_argument("--mode", choices=list(PRESETS))
    p.add_argument("--no-pause-cuts", action="store_true", help="only apply decisions.json removals")
    p.set_defaults(fn=cmd_plan)
    p = sp.add_parser("render")
    p.add_argument("video")
    p.add_argument("--final", action="store_true", help="full resolution + .srt (default: fast 720p preview)")
    p.set_defaults(fn=cmd_render)
    p = sp.add_parser("verify")
    p.add_argument("video")
    p.add_argument("--file", help="rendered file to check (default: last render)")
    p.add_argument("--apply", action="store_true", help="widen padding at suspect cuts")
    p.set_defaults(fn=cmd_verify)
    p = sp.add_parser("locate")
    p.add_argument("video")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--at", help="edited-video timestamp, e.g. 02:13")
    g.add_argument("--text", help="find a phrase in the original transcript")
    p.add_argument("--window", type=float, default=8)
    p.set_defaults(fn=cmd_locate)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
