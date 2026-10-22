"""Lay licensed music tracks (e.g. Pixabay) under the edit: per-cue offset/fades, loudness-matched, ducked under speech,
optional dips. Registers work/<name>/music.wav as decisions["sfx_track"].

decisions.json → "music_mix": {"level": 0.22, "duck": 0.4,
   "cues": [{"file": "assets/music/a.mp3", "at": 0, "src": 0, "end": 110.5, "fade_in": 0.8, "fade_out": 1.2}, …],
   "dips": [{"start": 186, "end": 200, "gain": 0.55}]}
usage: tools/musicmix.py input/NAME.mov"""
import subprocess as sp
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import vedit  # noqa: E402

SR = 44100


def load(f, ss, dur):
    cmd = [vedit.binpath("ffmpeg"), "-v", "error", "-ss", f"{ss:.3f}", "-t", f"{dur:.3f}", "-i", str(vedit.ROOT / f),
           "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(sp.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32).astype(np.float64)


def main():
    src, wd, _ = vedit.ctx(sys.argv[1])
    dec = vedit.jload(wd / "decisions.json", {})
    edl = vedit.jload(wd / "edl.json") or vedit.die("run plan first")
    cfg = dec["music_mix"]
    D = edl["new_dur"] + 1.0
    N = int(D * SR)
    mix = np.zeros(N)
    for c in cfg["cues"]:
        dur = min(c["end"], D) - c["at"]
        x = load(c["file"], c.get("src", 0.0), dur)
        x = x / (np.sqrt((x ** 2).mean()) + 1e-9) * 0.1  # loudness-match every track to the same RMS
        n = len(x)
        fi, fo = int(c.get("fade_in", 0.5) * SR), int(c.get("fade_out", 1.0) * SR)
        if fi:
            x[:fi] *= np.linspace(0, 1, fi)
        if fo:
            x[-fo:] *= np.linspace(1, 0, fo)
        i0 = int(c["at"] * SR)
        mix[i0:i0 + n] += x[: N - i0]
    env = np.ones(int(D * 100) + 1)
    for _, s, e in edl["words_out"]:
        env[int(s * 100):int(e * 100) + 1] = cfg.get("duck", 0.4)
    env = np.convolve(env, np.ones(45) / 45, "same")
    for d in cfg.get("dips", []):
        a, b = int(d["start"] * 100), int(d["end"] * 100)
        ramp = np.ones(len(env))
        ramp[a:b] = d["gain"]
        env *= np.convolve(ramp, np.ones(80) / 80, "same")
    g = np.repeat(env, SR // 100)[:N]
    mix = mix[: len(g)] * g
    mix = mix / (np.abs(mix).max() + 1e-9) * cfg.get("level", 0.22)
    out = wd / "music.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    dec["sfx_track"], dec["sfx_level"], dec["sfx"] = out.relative_to(vedit.ROOT).as_posix(), 1.0, True
    vedit.jsave(wd / "decisions.json", dec)
    print(f"✓ music mix ({len(cfg['cues'])} tracks) → {out.relative_to(vedit.ROOT)}")


if __name__ == "__main__":
    main()
