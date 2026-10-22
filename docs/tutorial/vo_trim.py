#!/usr/bin/env python3
"""Measure the recorded voiceover lines (vo/NNN.mp3, one per VOICEOVER.md line, in order) → vo/lines.json.

For each clip: where the speech starts and ends (Whisper's last word, then the loudness around it), so the trailing
breath, click or silence is never heard, and the video gives each line exactly the time it needs.

usage:  ../../.venv/bin/python vo_trim.py      (after replacing clips in vo/; then build.py --render)
"""
import collections
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.argv = [sys.argv[0]]
import build  # noqa: E402

os.environ["PATH"] = str(build.FFMPEG.parent) + os.pathsep + os.environ["PATH"]


def pcm(f):
    r = subprocess.run([str(build.FFMPEG), "-v", "error", "-i", str(f), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32)


def main():
    import mlx_whisper  # noqa: PLC0415 — Mac; faster-whisper elsewhere
    T = build.walkthrough(collections.defaultdict(lambda: [0, 0, 10, 10]))
    out = []
    for n, (_, _, en, _) in enumerate(T.vo):
        f = HERE / "vo" / f"{n:03d}.mp3"
        r = mlx_whisper.transcribe(str(f), path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en", word_timestamps=True)
        words = [w for s in r["segments"] for w in s.get("words", [])]
        asr_end = words[-1]["end"] if words else 0.0
        x = pcm(f)
        w = 320  # 20 ms
        db = np.array([20 * np.log10(np.sqrt(np.mean(x[i:i + w] ** 2)) + 1e-9) for i in range(0, len(x) - w, w)])
        t = np.arange(len(db)) * .02
        loud = np.where(db > -45)[0]
        inside = loud[t[loud] <= asr_end + .6]
        dur = len(x) / 16000
        out.append(dict(n=n, en=en, file=f.name, dur=round(dur, 3), asr=r["text"].strip(), asr_end=round(asr_end, 2),
                        start=round(max(0.0, t[inside[0]] - .05), 2) if len(inside) else 0.0,
                        end=round(min(dur, t[inside[-1]] + .12), 2) if len(inside) else dur))
        print(f"{n:3d} {out[-1]['start']:5.2f}–{out[-1]['end']:5.2f}  {out[-1]['asr'][:70]}")
    (HERE / "vo" / "lines.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"✓ {len(out)} lines · {sum(o['end'] - o['start'] for o in out):.1f} s of voice → vo/lines.json")


if __name__ == "__main__":
    main()
