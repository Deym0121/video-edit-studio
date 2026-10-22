#!/usr/bin/env python3
"""audit — verbatim re-listen of the EDITED audio to catch what the source transcript hides.

Whisper collapses repeats ("tapos tapos" → "tapos") and drops fragments ("ta-", "nag-")
in long audio, so the planning transcript looks clean while the viewer hears doubles.
audit rebuilds the edited audio straight from edl.json (seconds, no video render),
re-transcribes it in short overlapping windows with a verbatim prompt, stitches the
words, maps every word back to source time and flags:
  DBL  adjacent repeated word / 2–4-word phrase
  FRG  fragment (cut-off word: trailing "-", "...", or a 1–2 letter non-word)
  LOW  low-confidence word (often a mumble or noise)

Usage: audit.py VIDEO            → work/<name>/audit.txt + audit.json
"""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vedit  # noqa: E402

PROMPT = "Verbatim na transcript, isulat ang bawat ulit, utal at putol na salita: tapos tapos, ta- tapos, automation automation, so so, um, uh."
PARTICLES = {"na", "ng", "sa", "ay", "po", "ka", "mo", "ko", "si", "ni", "at", "o", "a", "i"}
WIN, HOP = 10.0, 4.0


def main():
    src, wd, meta = vedit.ctx(sys.argv[1])
    edl = vedit.jload(wd / "edl.json") or vedit.die("run plan first")
    segs = (edl.get("hook_segs") or ([edl["hook"]] if edl.get("hook") else [])) + edl["segments"]
    offs, o = [], 0.0
    for a, b in segs:
        offs.append(o)
        o += b - a
    total = o

    def to_src(t):
        for (a, b), of in zip(segs, offs):
            if of <= t < of + (b - a):
                return a + (t - of)
        return segs[-1][1]

    # 1) edited audio straight from the EDL (no video render)
    ff = vedit.binpath("ffmpeg")
    wav = wd / "audit.wav"
    fl = "".join(f"[0:a]atrim=start={a:.4f}:end={b:.4f},asetpts=PTS-STARTPTS[a{k}];" for k, (a, b) in enumerate(segs))
    fl += "".join(f"[a{k}]" for k in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[out]"
    script = wd / "audit_filter.txt"
    script.write_text(fl)
    vedit.sh([ff, "-y", "-v", "error", "-i", wd / "audio.wav", "-/filter_complex", script, "-map", "[out]",
              "-ac", "1", "-ar", "16000", wav])

    # 2) overlapping short windows, keep each window's middle part
    words, t, clip = [], 0.0, wd / "audit_win.wav"
    while t < total:
        print(f"\r• listening {vedit.tc(t)} / {vedit.tc(total)}", end="", flush=True)
        vedit.sh([ff, "-y", "-v", "error", "-ss", f"{t:.3f}", "-t", f"{WIN}", "-i", wav, clip])
        ws, _ = vedit.whisper_words(clip, "tl", prompt=PROMPT)
        lo = 0.0 if t == 0 else (WIN - HOP) / 2
        hi = WIN if t + WIN >= total else (WIN + HOP) / 2
        for w, s, e, p in ws:
            if w.strip() and lo <= s < hi:
                words.append(dict(w=w.strip(), t=round(t + s, 2), e=round(t + e, 2), p=round(p, 2)))
        t += HOP
    print()
    words.sort(key=lambda x: x["t"])
    # the same word heard by two overlapping windows → keep one
    dedup = []
    for w in words:
        if dedup and vedit.norm(w["w"]) == vedit.norm(dedup[-1]["w"]) and abs(w["t"] - dedup[-1]["t"]) < 0.35:
            continue
        dedup.append(w)
    words = dedup
    for w in words:
        w["src"] = round(to_src(w["t"]), 2)
        w["flags"] = []

    # 3) flags
    n = [vedit.norm(w["w"]) for w in words]
    for j in range(1, len(words)):
        for g in (4, 3, 2, 1):
            a = j - 2 * g + 1
            if a < 0:
                continue
            if all(n[a + q] and n[a + q] == n[a + g + q] for q in range(g)):
                if g == 1 and n[j] in PARTICLES:
                    break
                for q in range(a, j + 1):
                    words[q]["flags"].append("DBL")
                break
    for w, k in zip(words, n):
        raw = w["w"]
        if raw.endswith(("-", "…", "...")) or (len(k) <= 2 and k not in PARTICLES and not k.isdigit() and k not in {"ai", "ba", "eh", "oh", "ha"}):
            w["flags"].append("FRG")
        if w["p"] < 0.4:
            w["flags"].append("LOW")
    # confirm every repeat with ONE window centred on it (seams can fake a double)
    groups, cur_g = [], []
    for k, w in enumerate(words):
        if "DBL" in w["flags"]:
            if cur_g and k != cur_g[-1] + 1:
                groups.append(cur_g)
                cur_g = []
            cur_g.append(k)
        elif cur_g:
            groups.append(cur_g)
            cur_g = []
    if cur_g:
        groups.append(cur_g)
    for g in groups:
        mid = (words[g[0]]["t"] + words[g[-1]]["e"]) / 2
        a0 = max(0.0, mid - 3.5)
        vedit.sh([ff, "-y", "-v", "error", "-ss", f"{a0:.3f}", "-t", "7", "-i", wav, clip])
        ws, _ = vedit.whisper_words(clip, "tl", prompt=PROMPT)
        nn = [vedit.norm(x[0]) for x in ws if vedit.norm(x[0])]
        target = [vedit.norm(words[k]["w"]) for k in g]
        half = target[: len(target) // 2]
        real = any(nn[i:i + 2 * len(half)] == half + half for i in range(len(nn))) if half else False
        for k in g:
            words[k]["flags"] = [f for f in words[k]["flags"] if f != "DBL"] + (["DBL"] if real else ["dbl?"])
    vedit.jsave(wd / "audit.json", words)

    # 4) readable report: one line per ~sentence, flagged words in [brackets]
    lines, cur = [f"# Audit of edited audio — {src.name} ({vedit.tc(total)}, {len(words)} words)",
                  "# out-time (src-time)  text   ·  [[DBL]] repeat  [[FRG]] fragment  [[LOW]] low confidence", ""], []
    for w in words:
        if not cur:
            start = w
        tag = "/".join(dict.fromkeys(w["flags"]))
        cur.append(f"[[{w['w']}·{tag}]]" if tag else w["w"])
        if w["w"].endswith((".", "?", "!")) or len(cur) >= 14:
            lines.append(f"{vedit.tc(start['t']):>8} ({vedit.tc(start['src'])})  " + " ".join(cur))
            cur = []
    if cur:
        lines.append(f"{vedit.tc(start['t']):>8} ({vedit.tc(start['src'])})  " + " ".join(cur))
    (wd / "audit.txt").write_text("\n".join(lines) + "\n")
    nd = sum("DBL" in w["flags"] for w in words)
    print("confirmed repeats:")
    k = 0
    while k < len(words):
        if "DBL" in words[k]["flags"]:
            j = k
            while j + 1 < len(words) and "DBL" in words[j + 1]["flags"]:
                j += 1
            ctx = " ".join(x["w"] for x in words[max(0, k - 4):j + 4])
            print(f"   out {vedit.tc(words[k]['t'])} src {vedit.tc(words[k]['src'])}: …{ctx}…")
            k = j + 1
        else:
            k += 1
    nf = sum("FRG" in w["flags"] for w in words)
    nl = sum("LOW" in w["flags"] for w in words)
    print(f"✓ {len(words)} words · DBL {nd} · FRG {nf} · LOW {nl} → {(wd / 'audit.txt').relative_to(vedit.ROOT)}")


if __name__ == "__main__":
    main()
