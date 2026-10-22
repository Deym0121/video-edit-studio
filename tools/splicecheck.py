#!/usr/bin/env python3
"""splicecheck — listen to EVERY join of the edit (content cuts, pause trims, closed gate holes).

For each join it rebuilds ±window of the edited audio, runs the literal model (MMS, keeps repeats and
broken syllables) and prints what the viewer hears next to what the script says, plus the energy around
the join on both sides of the cut in the SOURCE (so a clipped onset or a leftover syllable is visible).

Usage: splicecheck.py VIDEO [--from SEC] [--to SEC]
"""
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vedit  # noqa: E402
from listen import mms_words  # noqa: E402

SR = 16000


def strip(db, a, b):
    return "".join(" " if v < -70 else "." if v < -50 else ":" if v < -40 else "#"
                   for v in [db[max(0, int(t * 100)):int(t * 100) + 2].max() if int(t * 100) < len(db) else -100
                             for t in np.arange(a, b, 0.02)])


def main():
    args = sys.argv[1:]
    lo = float(args[args.index("--from") + 1]) if "--from" in args else 0
    hi = float(args[args.index("--to") + 1]) if "--to" in args else 1e9
    src, wd, meta = vedit.ctx(args[0])
    edl = vedit.jload(wd / "edl.json")
    segs = (edl.get("hook_segs") or []) + edl["segments"]  # cold open first, as rendered
    words = vedit.jload(wd / "transcript.json")["words"]
    fixes = vedit.jload(wd / "decisions.json", {}).get("fixes", {})
    db = np.load(wd / "energy.npy")
    with wave.open(str(wd / "audio.wav")) as f:
        x = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    y = np.concatenate([x[int(a * SR):int(b * SR)] for a, b in segs])
    offs, o = [], 0.0
    for a, b in segs:
        offs.append(o)
        o += b - a
    wo = [(vedit.fixed_text(words, fixes, k), s, e) for k, s, e in edl["words_out"]]
    for j in range(1, len(segs)):
        T = offs[j]
        if not lo <= T <= hi:
            continue
        a0, a1 = max(0, T - 1.3), min(len(y) / SR, T + 1.5)
        heard = mms_words(y[int(a0 * SR):int(a1 * SR)])
        exp = " ".join(w for w, s, e in wo if a0 <= (s + e) / 2 <= a1)
        pe, ns = segs[j - 1][1], segs[j][0]
        kind = "hole" if ns - pe < 0.5 else "CUT "
        print(f"{vedit.tc(T)} {kind} src {pe:.2f}→{ns:.2f}  |{strip(db, pe - 0.4, pe)}‖{strip(db, pe, pe + 0.3)} … "
              f"{strip(db, ns - 0.3, ns)}‖{strip(db, ns, ns + 0.4)}|")
        print(f"      script: {exp}")
        print(f"      heard : " + " ".join(f"{w}" + ("·" if abs(a0 + s - T) < 0.12 else "") for w, s in heard))


if __name__ == "__main__":
    main()
