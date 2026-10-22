#!/usr/bin/env python3
"""soundcheck — find doubles and bad audio from the SOUND itself (no transcript).

Whisper "cleans up" speech, so repeated words vanish from transcripts. This looks at
the edited audio (rebuilt from edl.json) directly:

  REPEAT  two back-to-back stretches that sound the same (MFCC self-similarity at a
          short lag) → a word or phrase said twice
  CUT     a splice where speech energy is high right at the cut → clipped word
  CHOPPY  speech with lots of noise-gate dropouts (sounds broken)

Usage: soundcheck.py VIDEO   → work/<name>/soundcheck.json + printed list
"""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vedit  # noqa: E402

SR, HOP, WIN = 16000, 160, 400  # 10 ms hop, 25 ms window


def mfcc(x):
    n = 1 + (len(x) - WIN) // HOP
    frames = np.lib.stride_tricks.as_strided(x, (n, WIN), (x.strides[0] * HOP, x.strides[0])) * np.hanning(WIN)
    spec = np.abs(np.fft.rfft(frames, 512)) ** 2
    mel = lambda f: 2595 * np.log10(1 + f / 700)
    imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = imel(np.linspace(mel(80), mel(7600), 42))
    bins = np.floor((512 + 1) * pts / SR).astype(int)
    fb = np.zeros((40, 257))
    for i in range(40):
        a, b, c = bins[i], bins[i + 1], bins[i + 2]
        fb[i, a:b] = (np.arange(a, b) - a) / max(1, b - a)
        fb[i, b:c] = (c - np.arange(b, c)) / max(1, c - b)
    logmel = np.log(spec @ fb.T + 1e-9)
    k = np.arange(40)
    dct = np.cos(np.pi / 40 * (k[:, None] + 0.5) * np.arange(1, 14)[None, :])
    m = logmel @ dct
    m = (m - m.mean(0)) / (m.std(0) + 1e-9)
    e = 10 * np.log10((frames ** 2).mean(1) + 1e-10)
    return m, e


def main():
    src, wd, meta = vedit.ctx(sys.argv[1])
    edl = vedit.jload(wd / "edl.json")
    segs = (edl.get("hook_segs") or []) + edl["segments"]  # cold open first, as rendered
    offs, o = [], 0.0
    for a, b in segs:
        offs.append(o)
        o += b - a
    to_src = lambda t: next((a + (t - of) for (a, b), of in zip(segs, offs) if of <= t < of + (b - a)), segs[-1][1])

    with wave.open(str(wd / "audio.wav")) as f:
        full = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    x = np.concatenate([full[int(a * SR):int(b * SR)] for a, b in segs])
    M, E = mfcc(x)
    n = len(M)
    voiced = E > np.percentile(E, 90) - 22
    issues = []

    # ---- REPEAT: same-sounding stretch again 0.15–2.0 s later
    Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    best = {}
    for lag in range(15, 200):
        sim = (Mn[:-lag] * Mn[lag:]).sum(1)
        ok = (sim > 0.72) & voiced[:-lag] & voiced[lag:]
        # smooth: allow tiny gaps (tempo differences)
        run, start = 0, None
        for t in range(len(ok)):
            if ok[t]:
                if start is None:
                    start = t
                run = t - start + 1
            elif start is not None and (t - start) - run < 3 and t + 1 < len(ok) and ok[t + 1]:
                continue
            else:
                if start is not None and run >= 28 and lag >= run * 0.7:  # ≥0.28 s, repeat follows right after
                    key = start // 50
                    score = run * float(sim[start:start + run].mean())
                    if key not in best or score > best[key][3]:
                        best[key] = (start, run, lag, score)
                start, run = None, 0
    for start, run, lag, score in sorted(best.values()):
        t0 = start / 100
        issues.append(dict(kind="REPEAT", out=round(t0, 2), dur=round(run / 100, 2), lag=round(lag / 100, 2),
                           src=round(to_src(t0), 2), src2=round(to_src(t0 + lag / 100), 2), score=round(score, 1)))

    # ---- CUT: speech right at a splice
    db = np.load(wd / "energy.npy")
    for k in range(1, len(segs)):
        a_end, b_start = segs[k - 1][1], segs[k][0]
        tail = db[max(0, int(a_end * 100) - 4):int(a_end * 100)]
        head = db[int(b_start * 100):int(b_start * 100) + 4]
        if (len(tail) and tail.max() > -20) or (len(head) and head.max() > -20):
            issues.append(dict(kind="CUT", out=round(offs[k], 2), src=round(a_end, 2), src2=round(b_start, 2),
                               tail=round(float(tail.max()) if len(tail) else -99, 1),
                               head=round(float(head.max()) if len(head) else -99, 1)))

    # ---- CHOPPY: speech with noise-gate dropouts inside a 1 s window
    for s in np.arange(0, n / 100 - 1, 0.5):
        f0 = int(s * 100)
        w = E[f0:f0 + 100]
        if (w > np.percentile(E, 90) - 15).mean() > 0.35 and (w < -70).mean() > 0.25:
            if not issues or issues[-1]["kind"] != "CHOPPY" or s - issues[-1]["out"] > 1.5:
                issues.append(dict(kind="CHOPPY", out=round(float(s), 2), src=round(to_src(float(s)), 2)))

    issues.sort(key=lambda i: i["out"])
    vedit.jsave(wd / "soundcheck.json", issues)
    for i in issues:
        extra = f"said again {i['lag']}s later (src {i['src']}→{i['src2']})" if i["kind"] == "REPEAT" else \
            f"tail {i['tail']} dB / head {i['head']} dB at splice src {i['src']}→{i['src2']}" if i["kind"] == "CUT" else f"src {i['src']}"
        print(f"{i['kind']:<7} {vedit.tc(i['out'])}  {extra}")
    print(f"✓ {sum(i['kind'] == 'REPEAT' for i in issues)} repeats · {sum(i['kind'] == 'CUT' for i in issues)} hard cuts · "
          f"{sum(i['kind'] == 'CHOPPY' for i in issues)} choppy spots")


if __name__ == "__main__":
    main()
