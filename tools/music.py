"""Original emotional underscore (no samples, no licences): felt piano + warm strings + soft bass + reverb,
shaped by an intensity curve and ducked under speech. Registers the track as decisions["sfx_track"] (vedit mixes it).

decisions.json → "music": {"bpm": 72, "prog": ["Am","F","C","G"], "keys": [[t_edited, intensity 0–1], …],
                           "level": 0.30, "duck": 0.5}
usage: tools/music.py input/NAME.mov"""
import sys
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

sys.path.insert(0, str(Path(__file__).parent))
import vedit  # noqa: E402

SR = 44100
NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def chord(name):
    """'Am' → root midi (octave 3) + triad intervals; 'F', 'C', 'G', 'Em', 'Dm', 'Fmaj7', 'Gsus4'."""
    root = name[:2] if len(name) > 1 and name[1] in "#b" else name[:1]
    q = name[len(root):]
    r = 48 + NOTE[root]
    iv = [0, 3, 7] if q.startswith("m") and not q.startswith("maj") else [0, 4, 7]
    if "maj7" in q:
        iv = [0, 4, 7, 11]
    elif "sus4" in q:
        iv = [0, 5, 7]
    elif "add9" in q:
        iv = [0, 4, 7, 14]
    return r, iv


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def piano(m, vel, dur=4.0):
    f0, n = hz(m), int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    bright = 0.6 + 0.6 * vel
    for k in range(1, 10):
        fk = k * f0 * np.sqrt(1 + 0.0004 * k * k)
        if fk > 9000:
            break
        decay = (1.6 + 2.4 * (60 / m)) / (1 + 0.35 * k)  # low notes and low partials ring longer
        out += (1 / k ** (1.9 - bright)) * np.exp(-t / decay) * np.sin(2 * np.pi * fk * t + k)
    att = np.minimum(1, t / 0.006)
    ham = np.random.default_rng(m).standard_normal(n) * np.exp(-t / 0.012) * 0.04 * vel
    return (out * att + ham) * vel * 0.18


def strings(m, dur, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for d in (-9, -4, 0, 4, 9):  # cents: ensemble
        f = hz(m) * 2 ** (d / 1200)
        vib = 1 + 0.0022 * np.sin(2 * np.pi * (4.6 + 0.3 * d / 9) * t + rng.uniform(0, 6))
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        for k in range(1, 12):
            if f * k > 6000:
                break
            out += np.sin(k * ph + rng.uniform(0, 6)) / k
    env = np.minimum(1, t / 1.4) * np.minimum(1, (dur - t) / 1.6).clip(0, 1)
    return out * env * 0.012


def reverb_ir(secs=2.8):
    n = int(secs * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(7)
    ir = rng.standard_normal(n) * np.exp(-t * 6.9 / secs)
    ir = sosfilt(butter(2, 5000, "lowpass", fs=SR, output="sos"), ir)
    ir[: int(0.012 * SR)] = 0
    return ir / np.abs(ir).sum() * 30


def main():
    src, wd, _ = vedit.ctx(sys.argv[1])
    dec = vedit.jload(wd / "decisions.json", {})
    edl = vedit.jload(wd / "edl.json") or vedit.die("run plan first")
    cfg = dec.get("music", {})
    bpm, prog = cfg.get("bpm", 72), cfg.get("prog", ["Am", "F", "C", "G"])
    keys = sorted(cfg.get("keys", [[0, 0.3], [edl["new_dur"], 0.3]]))
    D = edl["new_dur"] + 2.0
    N = int(D * SR)
    beat = 60 / bpm
    bar = 4 * beat
    kt, kv = np.array([k[0] for k in keys]), np.array([k[1] for k in keys])
    inten = lambda x: float(np.interp(x, kt, kv))  # noqa: E731
    rng = np.random.default_rng(3)
    pno, pad, bass = np.zeros(N + SR * 6), np.zeros(N + SR * 6), np.zeros(N + SR * 6)
    nb = int(D / bar) + 1
    for b in range(nb):
        t0 = b * bar
        I = inten(t0 + bar / 2)
        r, iv = chord(prog[b % len(prog)])
        tones = [r + i for i in iv]
        # strings: whole-bar chord, more voices + higher octave as intensity rises
        if I > 0.25:
            sv = [tones[0] + 12, tones[1] + 12, tones[2] + 12] + ([tones[1] + 24] if I > 0.7 else [])
            for m in sv:
                s = strings(m, bar + 1.6, rng) * (I - 0.2) * 1.3
                i0 = int(t0 * SR)
                pad[i0:i0 + len(s)] += s
        # bass: root, soft sine + octave, enters with the build
        if I > 0.4:
            n = int((bar + 0.5) * SR)
            t = np.arange(n) / SR
            bf = hz(r - 12)
            s = (np.sin(2 * np.pi * bf * t) + 0.3 * np.sin(4 * np.pi * bf * t)) * np.minimum(1, t / 0.08) * np.exp(-t / 2.8)
            i0 = int(t0 * SR)
            bass[i0:i0 + n] += s * 0.10 * (I - 0.3)
        # piano: low root on beat 1, arpeggio pattern denser with intensity, melody top note on high intensity
        hits = [(0, r, 0.55)]
        arp = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 12]
        step = beat if I < 0.45 else beat / 2
        k = 0
        x = 0.0
        while x < bar - 1e-6:
            if not (I < 0.2 and k % 2):
                hits.append((x, arp[k % len(arp)] + (12 if I > 0.8 and k % 4 == 3 else 0), 0.32 + 0.25 * I))
            k += 1
            x += step
        if I > 0.6:
            hits.append((beat * 2, tones[2] + 24, 0.30))
        for off, m, v in hits:
            s = piano(m, v * (0.85 + 0.3 * rng.random()))
            i0 = int((t0 + off + rng.normal(0, 0.006)) * SR)
            pno[max(0, i0):max(0, i0) + len(s)] += s[: len(pno) - max(0, i0)]
    dry = pno + pad + bass
    ir = reverb_ir()
    wet = fftconvolve(dry, ir)[: len(dry)]
    mix = (0.72 * dry + 0.55 * wet)[:N]
    # ducking under speech (edited-time word spans), gentle so the bed stays emotional
    env = np.ones(int(D * 100))
    for _, s, e in edl["words_out"]:
        env[int(s * 100):int(e * 100) + 1] = cfg.get("duck", 0.5)
    env = np.convolve(env, np.ones(45) / 45, "same")  # ~0.45 s smoothing
    env = np.minimum(env, np.convolve(env, np.ones(25) / 25, "same"))
    g = np.repeat(env, SR // 100)[:N]
    mix = mix[: len(g)] * g
    # fade in/out
    fi, fo = int(0.8 * SR), int(2.2 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix = mix / (np.abs(mix).max() + 1e-9) * cfg.get("level", 0.30)
    out = wd / "music.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    dec["sfx_track"] = out.relative_to(vedit.ROOT).as_posix()
    dec["sfx_level"] = 1.0
    vedit.jsave(wd / "decisions.json", dec)
    print(f"✓ music {D:.1f}s · {bpm} bpm · {' '.join(prog)} → {out.relative_to(vedit.ROOT)}")


if __name__ == "__main__":
    main()
