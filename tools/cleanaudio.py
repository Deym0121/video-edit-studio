"""Remove steady background noise (electric fan, aircon, hum) and polish the voice — writes a new source file.

Lloyd 2026-10-17: "naririnig yung electric fan… boses ko lang yung maririnig". Default engine: DeepFilterNet3 voice
isolation (tools/df_denoise.py in the separate .venv-df — torch 2.2 + torchaudio), which removed ~33 dB of fan where
spectral gating (noisereduce, fallback --engine nr) only managed ~4 dB on the close-to-the-fan intro. Then a gentle voice chain (high-pass, de-mud, presence,
air, de-ess, compression). Video stream is copied untouched; the original goes to work/<name>/source_noisy.<ext>.
usage: tools/cleanaudio.py input/NAME.mov [--strength 0.9] [--test 30-45]"""
import argparse
import shutil
import subprocess as sp
import sys
from pathlib import Path

import numpy as np
import noisereduce as nr

sys.path.insert(0, str(Path(__file__).parent))
import vedit  # noqa: E402

SR = 48000
# no treble/air boost: it lifted DeepFilterNet's residual "static" (Lloyd 2026-10-17)
VOICE = ("highpass=f=95,highpass=f=95,equalizer=f=250:t=q:w=1.0:g=-2,equalizer=f=3200:t=q:w=1.4:g=1.5,lowpass=f=12500,deesser=i=0.3,"
         "acompressor=threshold=-22dB:ratio=2.2:attack=15:release=200:makeup=1.5")
RESIDUAL_DB = -14  # original audio blended back UNDER SPEECH ONLY: keeps soft syllables, masks artifacts; pauses stay fan-free


def load(src, ss=None, t=None):
    cmd = [vedit.binpath("ffmpeg"), "-v", "error", *(["-ss", str(ss)] if ss is not None else []), "-i", str(src),
           *(["-t", str(t)] if t else []), "-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(sp.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32).copy()


def noise_profile(x, max_s=12.0):
    """Fan-only frames: quiet (not speech) but not the phone's digital-silence gate."""
    f = SR // 100
    n = len(x) // f
    db = 20 * np.log10(np.sqrt((x[: n * f].reshape(n, f) ** 2).mean(1)) + 1e-9)
    live = db[db > -90]
    floor = np.percentile(live, 8)
    ok = (db > -90) & (db < floor + 6)
    runs, start = [], None  # keep stretches ≥ 0.25 s so we don't grab word tails
    for i, v in enumerate(np.append(ok, False)):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= 25:
                runs.append((start + 3, i - 3))
            start = None
    chunks, total = [], 0
    for a, b in runs:
        chunks.append(x[a * f:b * f])
        total += (b - a) / 100
        if total >= max_s:
            break
    prof = np.concatenate(chunks) if chunks else x[: SR]
    return prof, floor, total


def clean(x, prof, strength):
    y = nr.reduce_noise(y=x, sr=SR, y_noise=prof, stationary=True, prop_decrease=strength,
                        n_fft=2048, freq_mask_smooth_hz=400, time_mask_smooth_ms=60)
    return y.astype(np.float32)


def deepfilter(x, wd):
    """DeepFilterNet3 in its own venv (torchaudio isn't available for the main venv's torch)."""
    import wave
    a, b = wd / "df_in.wav", wd / "df_out.wav"
    with wave.open(str(a), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    sp.run([str(vedit.ROOT / ".venv-df" / "bin" / "python"), str(vedit.ROOT / "tools" / "df_denoise.py"), str(a), str(b)],
           check=True, capture_output=True)
    with wave.open(str(b)) as w:
        y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    a.unlink(), b.unlink()
    return y


def speech_blend(x, y, res=None):
    """y (DeepFilterNet) + a little of the original x while he is speaking. Full DF removal alone dropped soft
    syllables ("nawawala-wala") and left static; the voice masks the fan under it, so only the pauses need full removal."""
    f = SR // 100
    n = min(len(x), len(y)) // f
    x, y = x[: n * f], y[: n * f]
    res = x if res is None else res[: n * f]
    db = 20 * np.log10(np.sqrt((y.reshape(n, f) ** 2).mean(1)) + 1e-9)
    live = db[db > -90]
    floor = np.percentile(live, 10) if len(live) else -90
    vad = (db > max(floor + 18, -50)).astype(float)
    k = np.ones(25)  # 250 ms hangover/pre-roll so word edges and soft syllables are covered
    vad = np.clip(np.convolve(vad, k, "same"), 0, 1)
    ramp = np.hanning(9) / np.hanning(9).sum()  # 90 ms fades: no pumping
    vad = np.convolve(vad, ramp, "same")
    env = np.repeat(vad, f)
    return (y + res * env * 10 ** (RESIDUAL_DB / 20)).astype(np.float32)


def fanless(x, prof):
    """The residual blended under speech: spectral-gated AND high-passed at 150 Hz, so it brings back the soft
    syllables but not the fan (v5 blended the raw audio and Lloyd still heard the fan while he talked)."""
    from scipy.signal import butter, sosfiltfilt
    return sosfiltfilt(butter(4, 150, "highpass", fs=SR, output="sos"), clean(x, prof, 0.95)).astype(np.float32)


def polish(y):
    p = sp.run([vedit.binpath("ffmpeg"), "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                "-af", VOICE, "-f", "f32le", "-"], input=np.asarray(y, dtype=np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--strength", type=float, default=0.92, help="noisereduce only")
    ap.add_argument("--engine", choices=["df", "nr"], default="df" if (vedit.ROOT / ".venv-df" / "bin" / "python").exists() else "nr")
    ap.add_argument("--test", help="a-b seconds: write work/<name>/clean_test_{before,after}.wav only")
    a = ap.parse_args()
    src, wd, _ = vedit.ctx(a.video)
    backup = wd / f"source_noisy{src.suffix}"
    base = backup if backup.exists() else src  # always clean from the original noisy audio
    x = load(base)
    if a.engine == "df":
        print("• DeepFilterNet3 voice isolation + fan-free speech blend…", flush=True)
        prof, _, _ = noise_profile(x)
        den = lambda seg: speech_blend(seg, deepfilter(seg, wd), fanless(seg, prof))  # noqa: E731
    else:
        prof, floor, secs = noise_profile(x)
        print(f"• noise profile: {secs:.1f}s of fan-only audio (floor {floor:.1f} dB)")
        den = lambda seg: clean(seg, prof, a.strength)  # noqa: E731
    if a.test:
        t0, t1 = (float(v) for v in a.test.split("-"))
        seg = x[int(t0 * SR):int(t1 * SR)]
        out = polish(den(seg))
        for name, s in (("before", seg), ("after", out)):
            p = sp.run([vedit.binpath("ffmpeg"), "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        str(wd / f"clean_test_{name}.wav")], input=s.astype(np.float32).tobytes())
        print(f"✓ {wd / 'clean_test_after.wav'}")
        return
    y = polish(den(x))
    wav = wd / "audio_clean.wav"
    sp.run([vedit.binpath("ffmpeg"), "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", str(wav)],
           input=y.tobytes(), check=True)
    if not backup.exists():
        shutil.move(str(src), backup)
    tmp = src.with_name(src.stem + ".clean" + src.suffix)
    sp.run([vedit.binpath("ffmpeg"), "-v", "error", "-y", "-i", str(backup), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-map_metadata", "0", str(tmp)], check=True)
    tmp.replace(src)
    print(f"✓ {src.name}: fan noise removed + voice polished (original kept at {backup.relative_to(vedit.ROOT)})")


if __name__ == "__main__":
    main()
